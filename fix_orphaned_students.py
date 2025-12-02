#!/usr/bin/env python3
"""
Fix Orphaned Students - Backfill school_id and school_name
============================================================

Purpose: Fix 4,822 students (19%) with NULL school_id by extracting 
         establishment reference from knack_user_attributes JSONB

Strategy:
1. Find all students with school_id IS NULL
2. Extract Knack establishment ID from knack_user_attributes->field_133_raw
3. Look up establishment UUID from establishments table
4. Update vespa_students with correct school_id and school_name
5. Also backfill to vespa_accounts table

Date: December 1, 2025
Author: Tony (with AI assistance)
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_orphaned_students.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Stats tracking
stats = {
    'total_orphaned': 0,
    'fixed': 0,
    'no_knack_data': 0,
    'establishment_not_found': 0,
    'update_failed': 0,
    'errors': []
}

def get_establishment_mapping():
    """
    Pre-fetch all establishments to build knack_id -> UUID mapping
    Returns: Dict[knack_id, {id, name}]
    """
    logging.info("Loading establishment mappings...")
    
    try:
        establishments = supabase.table('establishments').select('id', 'knack_id', 'name').execute()
        
        mapping = {}
        for est in establishments.data:
            if est.get('knack_id'):
                mapping[est['knack_id']] = {
                    'id': est['id'],
                    'name': est['name']
                }
        
        logging.info(f"Loaded {len(mapping)} establishment mappings")
        return mapping
        
    except Exception as e:
        logging.error(f"Failed to load establishments: {e}")
        return {}

def extract_establishment_id_from_knack_data(knack_attributes):
    """
    Extract establishment Knack ID from knack_user_attributes JSONB
    
    Knack field_133_raw format:
    [
      {
        "id": "5abc123...",  <- This is the Knack establishment ID
        "identifier": "School Name"
      }
    ]
    """
    if not knack_attributes:
        return None
    
    try:
        # Check field_133_raw (establishment connection field)
        field_133_raw = knack_attributes.get('field_133_raw')
        
        if field_133_raw and isinstance(field_133_raw, list) and len(field_133_raw) > 0:
            first_item = field_133_raw[0]
            
            if isinstance(first_item, dict):
                # Get the establishment Knack ID
                est_knack_id = first_item.get('id')
                
                if est_knack_id:
                    logging.debug(f"  Extracted establishment Knack ID: {est_knack_id}")
                    return est_knack_id
        
        # Fallback: Try field_133 (formatted value)
        field_133 = knack_attributes.get('field_133')
        if field_133 and isinstance(field_133, list) and len(field_133) > 0:
            first_item = field_133[0]
            if isinstance(first_item, dict) and first_item.get('id'):
                return first_item['id']
        
        # No establishment reference found
        return None
        
    except Exception as e:
        logging.error(f"Error extracting establishment ID: {e}")
        return None

def fix_single_student(student, establishment_mapping, dry_run=False):
    """
    Fix a single orphaned student by backfilling school_id and school_name
    
    Returns: (success: bool, reason: str)
    """
    email = student.get('email')
    student_id = student.get('id')
    knack_attributes = student.get('knack_user_attributes')
    
    logging.info(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {email}")
    
    # Extract establishment Knack ID from JSON
    est_knack_id = extract_establishment_id_from_knack_data(knack_attributes)
    
    if not est_knack_id:
        logging.warning(f"  ⚠️  No establishment reference in knack_user_attributes")
        stats['no_knack_data'] += 1
        return (False, 'no_knack_data')
    
    logging.info(f"  Found establishment Knack ID: {est_knack_id}")
    
    # Look up establishment UUID
    establishment = establishment_mapping.get(est_knack_id)
    
    if not establishment:
        logging.warning(f"  ⚠️  Establishment Knack ID '{est_knack_id}' not found in establishments table")
        stats['establishment_not_found'] += 1
        stats['errors'].append({
            'email': email,
            'issue': 'establishment_not_found',
            'knack_id': est_knack_id
        })
        return (False, 'establishment_not_found')
    
    school_id = establishment['id']
    school_name = establishment['name']
    
    logging.info(f"  ✅ Matched to: {school_name} (UUID: {school_id})")
    
    if dry_run:
        logging.info(f"  [DRY RUN] Would update: school_id={school_id}, school_name={school_name}")
        stats['fixed'] += 1
        return (True, 'would_fix')
    
    # Update vespa_students
    try:
        update_data = {
            'school_id': school_id,
            'school_name': school_name,
            'updated_at': datetime.now().isoformat()
        }
        
        supabase.table('vespa_students').update(update_data).eq('id', student_id).execute()
        logging.info(f"  ✅ Updated vespa_students")
        
        # Also update vespa_accounts (if linked)
        account_id = student.get('account_id')
        if account_id:
            supabase.table('vespa_accounts').update(update_data).eq('id', account_id).execute()
            logging.info(f"  ✅ Updated vespa_accounts")
        
        stats['fixed'] += 1
        return (True, 'fixed')
        
    except Exception as e:
        logging.error(f"  ❌ Update failed: {e}")
        stats['update_failed'] += 1
        stats['errors'].append({
            'email': email,
            'issue': 'update_failed',
            'error': str(e)
        })
        return (False, 'update_failed')

def fix_orphaned_students(dry_run=True, limit=None):
    """
    Main function to fix all orphaned students
    
    Args:
        dry_run: If True, only log what would be done (don't actually update)
        limit: Max number of students to process (None = all)
    """
    logging.info("=" * 80)
    logging.info(f"{'DRY RUN - ' if dry_run else ''}FIXING ORPHANED STUDENTS")
    logging.info("=" * 80)
    
    # Load establishment mapping
    establishment_mapping = get_establishment_mapping()
    
    if not establishment_mapping:
        logging.error("❌ No establishments found! Cannot proceed.")
        return
    
    # Fetch orphaned students
    logging.info("\nFetching orphaned students (school_id IS NULL)...")
    
    query = supabase.table('vespa_students')\
        .select('id', 'email', 'full_name', 'school_id', 'school_name', 
                'knack_user_attributes', 'account_id', 'created_at')\
        .is_('school_id', 'null')
    
    if limit:
        query = query.limit(limit)
    
    try:
        orphaned_students = query.execute()
        stats['total_orphaned'] = len(orphaned_students.data)
        
        logging.info(f"Found {stats['total_orphaned']} orphaned students")
        
        if stats['total_orphaned'] == 0:
            logging.info("✅ No orphaned students found! Nothing to fix.")
            return
        
        # Process each student
        for i, student in enumerate(orphaned_students.data, 1):
            logging.info(f"\n[{i}/{stats['total_orphaned']}]")
            fix_single_student(student, establishment_mapping, dry_run)
            
            # Progress update every 100 students
            if i % 100 == 0:
                logging.info(f"\n{'=' * 80}")
                logging.info(f"PROGRESS: {i}/{stats['total_orphaned']} processed")
                logging.info(f"Fixed: {stats['fixed']}, No data: {stats['no_knack_data']}, "
                           f"Not found: {stats['establishment_not_found']}, Failed: {stats['update_failed']}")
                logging.info(f"{'=' * 80}\n")
        
        # Final summary
        print_summary(dry_run)
        
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        raise

def print_summary(dry_run):
    """Print final statistics"""
    logging.info("\n" + "=" * 80)
    logging.info(f"{'DRY RUN ' if dry_run else ''}SUMMARY")
    logging.info("=" * 80)
    logging.info(f"Total orphaned students:        {stats['total_orphaned']}")
    logging.info(f"{'Would be ' if dry_run else ''}Fixed:                     {stats['fixed']}")
    logging.info(f"No Knack data:                  {stats['no_knack_data']}")
    logging.info(f"Establishment not found:        {stats['establishment_not_found']}")
    logging.info(f"Update failed:                  {stats['update_failed']}")
    logging.info(f"\nSuccess rate:                   {stats['fixed']}/{stats['total_orphaned']} "
               f"({100 * stats['fixed'] / stats['total_orphaned'] if stats['total_orphaned'] > 0 else 0:.1f}%)")
    
    if stats['errors']:
        logging.info(f"\n⚠️  {len(stats['errors'])} errors logged")
        logging.info("\nFirst 10 errors:")
        for error in stats['errors'][:10]:
            logging.info(f"  - {error['email']}: {error['issue']}")
    
    logging.info("=" * 80)
    
    if dry_run:
        logging.info("\n✅ DRY RUN COMPLETE - No changes made")
        logging.info("Run with --live flag to apply changes")
    else:
        logging.info("\n✅ LIVE RUN COMPLETE - Changes applied to database")

def main():
    """Main entry point with command-line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix orphaned students with NULL school_id')
    parser.add_argument('--live', action='store_true', 
                       help='Apply changes (default is dry-run)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of students to process (for testing)')
    
    args = parser.parse_args()
    
    dry_run = not args.live
    
    if dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be made")
        logging.info("Use --live flag to apply changes\n")
    else:
        logging.warning("⚠️  LIVE MODE - Changes will be applied!")
        logging.warning("Press Ctrl+C within 5 seconds to cancel...\n")
        import time
        time.sleep(5)
    
    try:
        fix_orphaned_students(dry_run=dry_run, limit=args.limit)
    except KeyboardInterrupt:
        logging.info("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()



