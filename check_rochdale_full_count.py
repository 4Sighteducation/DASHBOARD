#!/usr/bin/env python3
"""
Check the ACTUAL full count of Rochdale students, handling pagination properly
"""

import os
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

def get_all_rochdale_students():
    """Get ALL Rochdale students, handling pagination"""
    logging.info("=" * 60)
    logging.info("ROCHDALE FULL STUDENT COUNT CHECK")
    logging.info("=" * 60)
    
    # Get Rochdale's establishment ID
    rochdale = supabase.table('establishments')\
        .select('id, name')\
        .ilike('name', '%Rochdale Sixth Form%')\
        .execute()
    
    if not rochdale.data:
        logging.error("Rochdale Sixth Form College not found!")
        return
    
    establishment_id = rochdale.data[0]['id']
    logging.info(f"Found: {rochdale.data[0]['name']}")
    logging.info(f"Establishment ID: {establishment_id}")
    
    # Method 1: Use count parameter to get exact count
    logging.info("\n📊 METHOD 1: Using count parameter")
    count_result = supabase.table('students')\
        .select('*', count='exact')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    logging.info(f"Total student count (using count): {count_result.count}")
    logging.info(f"Records returned in response: {len(count_result.data)}")
    
    # Method 2: Paginate through all records
    logging.info("\n📊 METHOD 2: Manual pagination")
    all_students = []
    page_size = 1000
    offset = 0
    
    while True:
        batch = supabase.table('students')\
            .select('id, email, year_group, knack_id, created_at')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not batch.data:
            break
            
        all_students.extend(batch.data)
        logging.info(f"  Page {(offset // page_size) + 1}: Retrieved {len(batch.data)} records (total so far: {len(all_students)})")
        
        if len(batch.data) < page_size:
            break
            
        offset += page_size
    
    logging.info(f"Total students found via pagination: {len(all_students)}")
    
    # Check year groups
    year_groups = {}
    for student in all_students:
        yg = student.get('year_group', 'Unknown')
        year_groups[yg] = year_groups.get(yg, 0) + 1
    
    logging.info("\n📚 Students by Year Group:")
    for yg, count in sorted(year_groups.items()):
        logging.info(f"  {yg}: {count} students")
    
    # Now check VESPA scores to understand the dashboard count
    logging.info("\n🎯 VESPA SCORES ANALYSIS:")
    logging.info("-" * 40)
    
    # Get count of VESPA records for 2025/2026
    vespa_count = supabase.table('vespa_scores')\
        .select('*', count='exact')\
        .eq('academic_year', '2025/2026')\
        .in_('student_id', [s['id'] for s in all_students[:500]])\
        .execute()
    
    logging.info(f"VESPA records for first 500 students in 2025/2026: {vespa_count.count}")
    
    # Check how the dashboard might be counting
    logging.info("\n💡 DASHBOARD COUNT INVESTIGATION:")
    
    # The dashboard might be counting VESPA records, not students
    # Let's check total VESPA records for this establishment for 2025/2026
    all_student_ids = [s['id'] for s in all_students]
    
    # Process in batches to avoid URL limits
    batch_size = 100
    total_vespa_2025 = 0
    unique_students_2025 = set()
    
    for i in range(0, len(all_student_ids), batch_size):
        batch_ids = all_student_ids[i:i+batch_size]
        vespa_batch = supabase.table('vespa_scores')\
            .select('student_id, cycle')\
            .eq('academic_year', '2025/2026')\
            .in_('student_id', batch_ids)\
            .execute()
        
        total_vespa_2025 += len(vespa_batch.data)
        for record in vespa_batch.data:
            unique_students_2025.add(record['student_id'])
        
        if i % 500 == 0:
            logging.info(f"  Processed {i + len(batch_ids)} students...")
    
    logging.info(f"\n📈 FINAL COUNTS FOR 2025/2026:")
    logging.info(f"  Total VESPA records: {total_vespa_2025}")
    logging.info(f"  Unique students with VESPA data: {len(unique_students_2025)}")
    logging.info(f"  Average cycles per student: {total_vespa_2025 / len(unique_students_2025) if unique_students_2025 else 0:.1f}")
    
    # Check for orphaned VESPA records (records without matching students)
    logging.info("\n🔍 CHECKING FOR ORPHANED VESPA RECORDS:")
    
    # Get a sample of VESPA records for 2025/2026
    sample_vespa = supabase.table('vespa_scores')\
        .select('student_id')\
        .eq('academic_year', '2025/2026')\
        .limit(100)\
        .execute()
    
    orphaned_count = 0
    for vespa in sample_vespa.data:
        if vespa['student_id'] not in all_student_ids:
            # Check if this student exists at all
            student_check = supabase.table('students')\
                .select('id, establishment_id')\
                .eq('id', vespa['student_id'])\
                .execute()
            
            if not student_check.data:
                orphaned_count += 1
                logging.info(f"  Orphaned VESPA record: student_id {vespa['student_id'][:8]}... doesn't exist")
            elif student_check.data[0]['establishment_id'] != establishment_id:
                logging.info(f"  VESPA record for student from different school: {vespa['student_id'][:8]}...")
    
    if orphaned_count > 0:
        logging.info(f"  Found {orphaned_count} orphaned VESPA records in sample of 100")
    
    return len(all_students)

def main():
    """Main execution"""
    try:
        total_students = get_all_rochdale_students()
        
        logging.info("\n" + "=" * 60)
        logging.info("CONCLUSION")
        logging.info("=" * 60)
        logging.info(f"Actual Rochdale student count: {total_students}")
        logging.info("\nThe dashboard count of 2303 is likely:")
        logging.info("1. Counting VESPA records instead of unique students")
        logging.info("2. Including multiple cycles per student")
        logging.info("3. Possibly including orphaned records from deleted students")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
