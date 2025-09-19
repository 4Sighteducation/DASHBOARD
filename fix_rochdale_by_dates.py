#!/usr/bin/env python3
"""
Fix Rochdale academic years based on completion dates
This will properly split historical data from current data
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fix_rochdale_years():
    """Fix academic years based on completion dates"""
    logging.info("=" * 60)
    logging.info("FIXING ROCHDALE ACADEMIC YEARS BY COMPLETION DATE")
    logging.info("=" * 60)
    
    # Get Rochdale's establishment ID
    rochdale = supabase.table('establishments')\
        .select('id, name')\
        .ilike('name', '%Rochdale Sixth%')\
        .execute()
    
    if not rochdale.data:
        logging.error("Rochdale Sixth Form College not found!")
        return
    
    establishment_id = rochdale.data[0]['id']
    logging.info(f"Found: {rochdale.data[0]['name']}")
    
    # Get ALL Rochdale student IDs
    logging.info("\nFetching all Rochdale students...")
    all_students = []
    offset = 0
    batch_size = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + batch_size - 1)\
            .execute()
        
        if not batch.data:
            break
            
        all_students.extend(batch.data)
        
        if len(batch.data) < batch_size:
            break
        offset += batch_size
    
    student_ids = [s['id'] for s in all_students]
    logging.info(f"Found {len(student_ids)} students")
    
    # Process VESPA scores in batches
    logging.info("\nAnalyzing VESPA scores by completion date...")
    
    to_fix_2024_25 = []
    keep_2025_26 = []
    
    # Process in smaller batches to avoid URL limits
    batch_size = 50
    for i in range(0, len(student_ids), batch_size):
        batch_ids = student_ids[i:i+batch_size]
        
        vespa_records = supabase.table('vespa_scores')\
            .select('id, student_id, cycle, completion_date, academic_year')\
            .in_('student_id', batch_ids)\
            .execute()
        
        for record in vespa_records.data:
            completion_date = record.get('completion_date', '')
            
            # Parse the completion date
            if completion_date:
                # Date format: "2024-09-13T00:00:00+00:00"
                date_str = completion_date.split('T')[0]  # Get just the date part
                year, month, day = date_str.split('-')
                year = int(year)
                month = int(month)
                
                # Determine correct academic year
                # Before August 1, 2025 -> 2024/2025
                # After August 1, 2025 -> 2025/2026
                if year < 2025 or (year == 2025 and month < 8):
                    # This should be 2024/2025
                    if record['academic_year'] != '2024/2025':
                        to_fix_2024_25.append(record)
                else:
                    # This should be 2025/2026
                    if record['academic_year'] == '2025/2026':
                        keep_2025_26.append(record)
        
        logging.info(f"Processed {i + len(batch_ids)}/{len(student_ids)} students...")
    
    logging.info(f"\n📊 Analysis complete:")
    logging.info(f"  - Records to move to 2024/2025: {len(to_fix_2024_25)}")
    logging.info(f"  - Records correctly in 2025/2026: {len(keep_2025_26)}")
    
    if not to_fix_2024_25:
        logging.info("\n✅ No records need fixing!")
        return
    
    # Show examples
    logging.info("\n📋 Sample records that will be moved to 2024/2025:")
    for record in to_fix_2024_25[:5]:
        logging.info(f"  - Student {record['student_id'][:8]}..., Cycle {record['cycle']}, "
                    f"Completed: {record['completion_date'][:10]}")
    
    # Ask for confirmation
    logging.info("\n" + "=" * 60)
    logging.info(f"READY TO FIX {len(to_fix_2024_25)} RECORDS")
    logging.info("=" * 60)
    response = input("\n⚠️  Proceed with the fix? (yes/no): ")
    
    if response.lower() != 'yes':
        logging.info("Fix cancelled by user")
        return
    
    # Apply the fix in batches
    logging.info("\n🔧 Applying fixes...")
    
    fixed_count = 0
    error_count = 0
    batch_size = 100
    
    for i in range(0, len(to_fix_2024_25), batch_size):
        batch = to_fix_2024_25[i:i+batch_size]
        
        for record in batch:
            try:
                # Update the academic year
                result = supabase.table('vespa_scores')\
                    .update({'academic_year': '2024/2025'})\
                    .eq('id', record['id'])\
                    .execute()
                
                fixed_count += 1
                
            except Exception as e:
                logging.error(f"Error updating record {record['id']}: {e}")
                error_count += 1
        
        logging.info(f"Progress: {fixed_count}/{len(to_fix_2024_25)} fixed...")
    
    # Also update question_responses for consistency
    logging.info("\n📝 Updating question_responses...")
    
    # Get all affected student-cycle combinations
    student_cycles_to_fix = set()
    for record in to_fix_2024_25:
        student_cycles_to_fix.add((record['student_id'], record['cycle']))
    
    logging.info(f"Updating responses for {len(student_cycles_to_fix)} student-cycle combinations...")
    
    response_fixed = 0
    for student_id, cycle in student_cycles_to_fix:
        try:
            result = supabase.table('question_responses')\
                .update({'academic_year': '2024/2025'})\
                .eq('student_id', student_id)\
                .eq('cycle', cycle)\
                .execute()
            
            response_fixed += len(result.data) if result.data else 0
            
        except Exception as e:
            logging.error(f"Error updating responses for {student_id[:8]}... cycle {cycle}: {e}")
    
    logging.info(f"Updated {response_fixed} question responses")
    
    # Verify the fix
    logging.info("\n✅ VERIFYING FIX...")
    
    # Count records by academic year
    vespa_2024_25 = []
    vespa_2025_26 = []
    
    for i in range(0, len(student_ids), 50):
        batch_ids = student_ids[i:i+50]
        
        records = supabase.table('vespa_scores')\
            .select('academic_year')\
            .in_('student_id', batch_ids)\
            .execute()
        
        for r in records.data:
            if r['academic_year'] == '2024/2025':
                vespa_2024_25.append(r)
            elif r['academic_year'] == '2025/2026':
                vespa_2025_26.append(r)
    
    logging.info("\n" + "=" * 60)
    logging.info("FIX COMPLETE!")
    logging.info("=" * 60)
    logging.info(f"\n📊 Final distribution:")
    logging.info(f"  2024/2025: {len(vespa_2024_25)} VESPA records")
    logging.info(f"  2025/2026: {len(vespa_2025_26)} VESPA records")
    logging.info(f"\n✨ The dashboard should now show:")
    logging.info(f"  - 2024/25: Historical data from last year")
    logging.info(f"  - 2025/26: Current year data")
    
    # Trigger statistics recalculation
    logging.info("\n📈 Triggering statistics recalculation...")
    try:
        supabase.rpc('calculate_statistics').execute()
        logging.info("Statistics recalculation triggered successfully")
    except Exception as e:
        logging.warning(f"Could not trigger statistics recalculation: {e}")
        logging.info("You may need to run this manually or wait for the next sync")

if __name__ == "__main__":
    fix_rochdale_years()
