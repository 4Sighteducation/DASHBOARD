#!/usr/bin/env python3
"""
Backfill Orphaned Students by Querying Knack API
=================================================

Purpose: Fix 4,822 students with NULL school_id by querying Knack Object_10
         directly using their email address

Critical Finding: knack_user_attributes is NULL for orphaned students,
                  so we can't extract from JSON - we need to query Knack API!

Strategy:
1. Get all orphaned students (school_id IS NULL)
2. Clean HTML from emails
3. For each email, query Knack Object_10 (field_197 = email)
4. Extract establishment (field_133), name (field_187), year group (field_144)
5. Look up establishment UUID from establishments table
6. Update vespa_students AND vespa_accounts with full data

Date: December 1, 2025
"""

import os
import sys
import json
import logging
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backfill_from_knack.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Stats tracking
stats = {
    'total_orphaned': 0,
    'cleaned_emails': 0,
    'found_in_knack': 0,
    'not_in_knack': 0,
    'school_cancelled': 0,
    'establishment_found': 0,
    'establishment_not_found': 0,
    'updated': 0,
    'update_failed': 0,
    'errors': []
}

def clean_email_html(email):
    """
    Clean HTML anchor tags from email
    
    Input: <a href="mailto:student@school.com">student@school.com</a>
    Output: student@school.com
    """
    if not email or not isinstance(email, str):
        return None
    
    # Already clean
    if '<' not in email and '@' in email:
        return email.strip().lower()
    
    # Extract from mailto: link
    if 'mailto:' in email:
        match = re.search(r'mailto:([^"\'>\s]+)', email)
        if match:
            return match.group(1).strip().lower()
    
    # Strip all HTML tags
    clean = re.sub(r'<[^>]+>', '', email).strip().lower()
    
    # Validate it's an email
    if '@' in clean and '.' in clean:
        return clean
    
    return None

def query_knack_by_email(email):
    """
    Query Knack Object_10 (VESPA Results) by email
    
    Returns: Knack record or None
    """
    try:
        url = f"https://api.knack.com/v1/objects/object_10/records"
        
        headers = {
            'X-Knack-Application-Id': KNACK_APP_ID,
            'X-Knack-REST-API-Key': KNACK_API_KEY
        }
        
        # Build filters for email field (field_197)
        params = {
            'filters': json.dumps([{
                'field': 'field_197',
                'operator': 'is',
                'value': email
            }])
            # DON'T use format=raw here - we need both formatted and raw fields
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        records = data.get('records', [])
        
        if records:
            # DEBUG: Log available fields for first test
            record = records[0]
            logging.debug(f"  Available fields: {list(record.keys())[:10]}")
            
            # Return first record (should only be one per email per year)
            return record
        
        return None
        
    except Exception as e:
        logging.error(f"Knack API error for {email}: {e}")
        return None

def get_establishment_mapping():
    """
    Pre-fetch all establishments for knack_id -> UUID lookup
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

def is_establishment_cancelled(est_knack_id):
    """
    Check if establishment is cancelled by querying Knack Object_2 (Establishments)
    
    Returns: True if cancelled, False if active, None if error
    """
    try:
        url = f"https://api.knack.com/v1/objects/object_2/records/{est_knack_id}"
        
        headers = {
            'X-Knack-Application-Id': KNACK_APP_ID,
            'X-Knack-REST-API-Key': KNACK_API_KEY
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            logging.warning(f"  Establishment {est_knack_id} not found in Knack")
            return None
        
        response.raise_for_status()
        est_record = response.json()
        
        # Check field_2209 (Account Status)
        account_status = est_record.get('field_2209', '')
        
        is_cancelled = account_status == 'Cancelled'
        
        if is_cancelled:
            logging.info(f"  ⚠️  School is CANCELLED in Knack - skipping")
        
        return is_cancelled
        
    except Exception as e:
        logging.error(f"  Error checking if establishment cancelled: {e}")
        return None

def extract_establishment_from_knack_record(knack_record):
    """
    Extract establishment Knack ID from Object_10 record
    """
    try:
        # Try field_133_raw first (raw connection field)
        field_133_raw = knack_record.get('field_133_raw', [])
        
        if field_133_raw and isinstance(field_133_raw, list) and len(field_133_raw) > 0:
            first_item = field_133_raw[0]
            
            if isinstance(first_item, dict):
                est_knack_id = first_item.get('id')
                est_name = first_item.get('identifier', '')
                
                return {
                    'knack_id': est_knack_id,
                    'name': est_name
                }
        
        # Try field_133 (formatted version)
        field_133 = knack_record.get('field_133')
        if field_133:
            if isinstance(field_133, list) and len(field_133) > 0:
                return {
                    'knack_id': field_133[0].get('id') if isinstance(field_133[0], dict) else field_133[0],
                    'name': field_133[0].get('identifier', '') if isinstance(field_133[0], dict) else ''
                }
        
        return None
        
    except Exception as e:
        logging.error(f"Error extracting establishment: {e}")
        return None

def extract_name_from_knack_record(knack_record):
    """
    Extract student name from Object_10 record
    
    Field: field_187_raw (Student name)
    Format: {"first": "John", "last": "Smith", "full": "John Smith"}
    """
    try:
        field_187_raw = knack_record.get('field_187_raw', {})
        
        if isinstance(field_187_raw, dict):
            return {
                'first_name': field_187_raw.get('first', ''),
                'last_name': field_187_raw.get('last', ''),
                'full_name': field_187_raw.get('full', '')
            }
        elif isinstance(field_187_raw, str):
            # Fallback: split name string
            parts = field_187_raw.split(' ', 1)
            return {
                'first_name': parts[0] if len(parts) > 0 else '',
                'last_name': parts[1] if len(parts) > 1 else '',
                'full_name': field_187_raw
            }
        
        return None
        
    except Exception as e:
        logging.error(f"Error extracting name: {e}")
        return None

def backfill_single_student(student, establishment_mapping, dry_run=False):
    """
    Backfill a single orphaned student from Knack
    
    Returns: (success: bool, reason: str)
    """
    email_raw = student.get('email', '')
    student_id = student.get('id')
    
    logging.info(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {email_raw}")
    
    # Step 1: Clean HTML from email
    email_clean = clean_email_html(email_raw)
    
    if not email_clean:
        logging.warning(f"  ⚠️  Could not clean email: {email_raw}")
        return (False, 'email_clean_failed')
    
    if email_clean != email_raw:
        logging.info(f"  Cleaned email: {email_raw} → {email_clean}")
        stats['cleaned_emails'] += 1
    
    # Step 2: Query Knack for this student
    logging.info(f"  Querying Knack Object_10 for: {email_clean}")
    knack_record = query_knack_by_email(email_clean)
    
    if not knack_record:
        logging.warning(f"  ⚠️  Student not found in Knack Object_10")
        stats['not_in_knack'] += 1
        return (False, 'not_in_knack')
    
    stats['found_in_knack'] += 1
    logging.info(f"  ✅ Found in Knack (record ID: {knack_record.get('id')})")
    
    # Step 3: Extract establishment
    establishment_ref = extract_establishment_from_knack_record(knack_record)
    
    if not establishment_ref:
        logging.warning(f"  ⚠️  No establishment reference in Knack record")
        stats['establishment_not_found'] += 1
        return (False, 'no_establishment_in_knack')
    
    est_knack_id = establishment_ref['knack_id']
    logging.info(f"  Found establishment Knack ID: {est_knack_id} ({establishment_ref['name']})")
    
    # Step 3.5: Check if establishment is cancelled
    is_cancelled = is_establishment_cancelled(est_knack_id)
    
    if is_cancelled:
        stats['not_in_knack'] += 1  # Count as not processable
        return (False, 'school_cancelled')
    
    # Step 4: Look up establishment UUID
    establishment = establishment_mapping.get(est_knack_id)
    
    if not establishment:
        logging.warning(f"  ⚠️  Establishment '{est_knack_id}' not in establishments table")
        stats['establishment_not_found'] += 1
        stats['errors'].append({
            'email': email_clean,
            'issue': 'establishment_not_in_supabase',
            'knack_id': est_knack_id,
            'name': establishment_ref['name']
        })
        return (False, 'establishment_not_in_supabase')
    
    school_id = establishment['id']
    school_name = establishment['name']
    stats['establishment_found'] += 1
    
    logging.info(f"  ✅ Matched to: {school_name} (UUID: {school_id[:8]}...)")
    
    # Step 5: Extract name
    name_data = extract_name_from_knack_record(knack_record)
    
    # Step 6: Extract other fields
    year_group = knack_record.get('field_144', '')  # Current Year Group
    student_group = knack_record.get('field_145', '')  # Group (may have HTML)
    
    # Clean student_group if it has HTML
    if student_group and '<' in str(student_group):
        student_group = re.sub(r'<[^>]+>', '', str(student_group)).strip()
    
    if dry_run:
        logging.info(f"  [DRY RUN] Would update:")
        logging.info(f"    email: {email_clean}")
        logging.info(f"    school: {school_name}")
        logging.info(f"    name: {name_data.get('full_name') if name_data else 'N/A'}")
        logging.info(f"    year: {year_group}")
        stats['updated'] += 1
        return (True, 'would_update')
    
    # Step 7: Update vespa_students
    try:
        update_data = {
            'email': email_clean,  # Update email if it had HTML
            'school_id': school_id,
            'school_name': school_name,
            'current_knack_id': knack_record.get('id'),
            'updated_at': datetime.now().isoformat()
        }
        
        # Add name data if available
        if name_data:
            update_data['first_name'] = name_data['first_name']
            update_data['last_name'] = name_data['last_name']
            update_data['full_name'] = name_data['full_name']
        
        # Add academic data (truncate to avoid varchar(100) constraint)
        if year_group:
            update_data['current_year_group'] = str(year_group)[:100]
        if student_group:
            update_data['student_group'] = str(student_group)[:100]
        
        # Store full Knack record for reference
        update_data['knack_user_attributes'] = knack_record
        update_data['last_synced_from_knack'] = datetime.now().isoformat()
        
        # Update vespa_students
        supabase.table('vespa_students').update(update_data).eq('id', student_id).execute()
        logging.info(f"  ✅ Updated vespa_students")
        
        # Also update vespa_accounts if linked
        account_id = student.get('account_id')
        if account_id:
            try:
                account_update = {
                    'school_id': school_id,
                    'school_name': school_name,
                    'current_knack_id': knack_record.get('id'),
                    'updated_at': datetime.now().isoformat()
                }
                
                if name_data:
                    account_update['first_name'] = name_data['first_name']
                    account_update['last_name'] = name_data['last_name']
                    account_update['full_name'] = name_data['full_name']
                
                # DON'T update email in vespa_accounts to avoid duplicate key errors
                # Email already exists in another account - this is a data integrity issue
                # Student record is fixed, that's what matters for now
                
                supabase.table('vespa_accounts').update(account_update).eq('id', account_id).execute()
                logging.info(f"  ✅ Updated vespa_accounts")
            except Exception as e:
                # Log but don't fail - student record is already fixed
                logging.warning(f"  ⚠️  vespa_accounts update failed (non-critical): {e}")
        
        stats['updated'] += 1
        return (True, 'updated')
        
    except Exception as e:
        logging.error(f"  ❌ Update failed: {e}")
        stats['update_failed'] += 1
        stats['errors'].append({
            'email': email_clean,
            'issue': 'update_failed',
            'error': str(e)
        })
        return (False, 'update_failed')

def backfill_orphaned_students(dry_run=True, limit=None, rate_limit_ms=200):
    """
    Main function to backfill orphaned students from Knack
    
    Args:
        dry_run: If True, only log what would be done
        limit: Max number of students to process
        rate_limit_ms: Milliseconds to wait between Knack API calls
    """
    logging.info("=" * 80)
    logging.info(f"{'DRY RUN - ' if dry_run else ''}BACKFILLING ORPHANED STUDENTS FROM KNACK")
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
                'account_id', 'created_at')\
        .is_('school_id', 'null')\
        .order('created_at', desc=True)  # Process newest first
    
    if limit:
        query = query.limit(limit)
    
    try:
        orphaned_students = query.execute()
        stats['total_orphaned'] = len(orphaned_students.data)
        
        logging.info(f"Found {stats['total_orphaned']} orphaned students")
        
        if stats['total_orphaned'] == 0:
            logging.info("✅ No orphaned students found!")
            return
        
        # Process each student
        for i, student in enumerate(orphaned_students.data, 1):
            logging.info(f"\n{'=' * 80}")
            logging.info(f"[{i}/{stats['total_orphaned']}]")
            
            backfill_single_student(student, establishment_mapping, dry_run)
            
            # Rate limiting for Knack API
            time.sleep(rate_limit_ms / 1000.0)
            
            # Progress update every 50 students
            if i % 50 == 0:
                print_progress()
        
        # Final summary
        print_summary(dry_run)
        
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        raise

def print_progress():
    """Print progress stats"""
    logging.info(f"\n{'=' * 80}")
    logging.info(f"PROGRESS UPDATE")
    logging.info(f"{'=' * 80}")
    logging.info(f"Processed:                 {stats['found_in_knack'] + stats['not_in_knack']}")
    logging.info(f"  Found in Knack:          {stats['found_in_knack']}")
    logging.info(f"  Not in Knack:            {stats['not_in_knack']}")
    logging.info(f"  Establishment matched:   {stats['establishment_found']}")
    logging.info(f"  Updated:                 {stats['updated']}")
    logging.info(f"  Failed:                  {stats['update_failed']}")
    logging.info(f"{'=' * 80}\n")

def print_summary(dry_run):
    """Print final statistics"""
    logging.info("\n" + "=" * 80)
    logging.info(f"{'DRY RUN ' if dry_run else ''}SUMMARY")
    logging.info("=" * 80)
    logging.info(f"Total orphaned students:        {stats['total_orphaned']}")
    logging.info(f"Emails cleaned (had HTML):      {stats['cleaned_emails']}")
    logging.info(f"Found in Knack Object_10:       {stats['found_in_knack']}")
    logging.info(f"NOT found in Knack:             {stats['not_in_knack']}")
    logging.info(f"School is CANCELLED:            {stats['school_cancelled']}")
    logging.info(f"Establishment matched:          {stats['establishment_found']}")
    logging.info(f"Establishment not found:        {stats['establishment_not_found']}")
    logging.info(f"{'Would update' if dry_run else 'Updated'}:                     {stats['updated']}")
    logging.info(f"Update failed:                  {stats['update_failed']}")
    
    if stats['found_in_knack'] > 0:
        success_rate = 100 * stats['updated'] / stats['found_in_knack']
        logging.info(f"\nSuccess rate (of those in Knack): {success_rate:.1f}%")
    
    if stats['errors']:
        logging.info(f"\n⚠️  {len(stats['errors'])} errors logged")
        logging.info("\nFirst 10 errors:")
        for error in stats['errors'][:10]:
            logging.info(f"  - {error['email']}: {error['issue']}")
            if error.get('knack_id'):
                logging.info(f"    Knack ID: {error['knack_id']}, Name: {error.get('name')}")
        
        # Group by issue type
        issue_counts = {}
        for error in stats['errors']:
            issue = error['issue']
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        logging.info("\nErrors by type:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            logging.info(f"  {issue}: {count}")
    
    logging.info("=" * 80)
    
    if dry_run:
        logging.info("\n✅ DRY RUN COMPLETE - No changes made")
        logging.info("Run with --live flag to apply changes")
    else:
        logging.info("\n✅ LIVE RUN COMPLETE - Changes applied")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Backfill orphaned students by querying Knack API'
    )
    parser.add_argument('--live', action='store_true',
                       help='Apply changes (default is dry-run)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of students to process')
    parser.add_argument('--rate-limit', type=int, default=200,
                       help='Milliseconds between Knack API calls (default: 200)')
    
    args = parser.parse_args()
    
    dry_run = not args.live
    
    if dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be made")
        logging.info("Use --live flag to apply changes\n")
    else:
        logging.warning("⚠️  LIVE MODE - Changes will be applied!")
        logging.warning(f"Processing up to {args.limit or 'ALL'} students")
        logging.warning("Press Ctrl+C within 5 seconds to cancel...\n")
        import time
        time.sleep(5)
    
    try:
        backfill_orphaned_students(
            dry_run=dry_run, 
            limit=args.limit,
            rate_limit_ms=args.rate_limit
        )
    except KeyboardInterrupt:
        logging.info("\n\n❌ Cancelled by user")
        print_progress()
        sys.exit(1)
    except Exception as e:
        logging.error(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

