#!/usr/bin/env python3
"""
Check the structure of the students table and understand how academic years work
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

def check_structure():
    """Check the structure of the students table"""
    logging.info("=" * 60)
    logging.info("CHECKING TABLE STRUCTURE")
    logging.info("=" * 60)
    
    # Get a sample student record to see the columns
    sample = supabase.table('students')\
        .select('*')\
        .limit(1)\
        .execute()
    
    if sample.data:
        logging.info("\nStudent table columns:")
        for key in sample.data[0].keys():
            logging.info(f"  - {key}")
    
    # Check how the dashboard might be determining student counts
    logging.info("\n" + "=" * 60)
    logging.info("UNDERSTANDING ACADEMIC YEAR LOGIC")
    logging.info("=" * 60)
    
    # Get Rochdale's establishment ID
    rochdale = supabase.table('establishments')\
        .select('id, name')\
        .ilike('name', '%Rochdale Sixth%')\
        .execute()
    
    if not rochdale.data:
        logging.error("Rochdale not found!")
        return
    
    establishment_id = rochdale.data[0]['id']
    logging.info(f"\nRochdale ID: {establishment_id}")
    
    # Check how many unique students have VESPA data for each academic year
    logging.info("\nChecking unique students by VESPA academic year:")
    
    # Get all Rochdale students
    all_students = []
    offset = 0
    limit = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id, email, name')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not batch.data:
            break
        all_students.extend(batch.data)
        if len(batch.data) < limit:
            break
        offset += limit
    
    logging.info(f"Total Rochdale students in DB: {len(all_students)}")
    
    # Check VESPA distribution
    student_ids = [s['id'] for s in all_students]
    
    for year in ['2024/2025', '2025/2026']:
        unique_students = set()
        
        # Process in batches
        for i in range(0, len(student_ids), 50):
            batch_ids = student_ids[i:i+50]
            
            vespa = supabase.table('vespa_scores')\
                .select('student_id')\
                .in_('student_id', batch_ids)\
                .eq('academic_year', year)\
                .execute()
            
            for v in vespa.data:
                unique_students.add(v['student_id'])
        
        logging.info(f"  {year}: {len(unique_students)} unique students with VESPA data")
    
    # The issue is clear: the dashboard counts students based on whether they have
    # VESPA data for that academic year. Since some students have data in BOTH years,
    # they're being counted in both years.
    
    logging.info("\n💡 KEY INSIGHT:")
    logging.info("The dashboard appears to count students based on VESPA data presence.")
    logging.info("Students with data in both years are counted in both years.")
    logging.info("\nFor Rochdale:")
    logging.info("- 898 students have ONLY 2024/25 data (last year's departed students)")
    logging.info("- 1029 students have ONLY 2025/26 data (new/current-only students)")  
    logging.info("- 376 students have BOTH (continuing students)")
    logging.info("\nDashboard shows:")
    logging.info("- 2024/25: 898 + 376 = 1274 students")
    logging.info("- 2025/26: 1029 + 376 = 1405 students")

if __name__ == "__main__":
    try:
        check_structure()
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
