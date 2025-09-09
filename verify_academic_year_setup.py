#!/usr/bin/env python3
"""
Verify if academic_year column has been added to students table
and check current state of data
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

def check_academic_year_column():
    """Check if academic_year column exists and analyze data"""
    logging.info("=" * 60)
    logging.info("CHECKING ACADEMIC YEAR SETUP")
    logging.info("=" * 60)
    
    try:
        # Try to query the academic_year column
        test_result = supabase.table('students')\
            .select('id, academic_year')\
            .limit(1)\
            .execute()
        
        if test_result.data:
            logging.info("✅ academic_year column EXISTS!")
            
            # Check if any values are populated
            sample = test_result.data[0]
            if sample.get('academic_year'):
                logging.info(f"✅ Column has data: {sample['academic_year']}")
            else:
                logging.info("⚠️ Column exists but is NULL for this record")
        else:
            logging.info("⚠️ No student records found")
            
    except Exception as e:
        if 'column students.academic_year does not exist' in str(e):
            logging.error("❌ academic_year column DOES NOT EXIST")
            logging.info("\nPlease run the SQL migrations first:")
            logging.info("1. add_academic_year_STEP1.sql")
            logging.info("2. add_academic_year_STEP2.sql")
            logging.info("3. add_academic_year_STEP3_rochdale.sql")
            logging.info("4. add_academic_year_STEP4_finalize.sql")
            return False
        else:
            logging.error(f"Error checking column: {e}")
            return False
    
    # If column exists, analyze the data
    logging.info("\n" + "=" * 60)
    logging.info("ANALYZING ACADEMIC YEAR DATA")
    logging.info("=" * 60)
    
    # Count students by academic year
    try:
        # Get all unique academic years
        all_students = []
        offset = 0
        while True:
            batch = supabase.table('students')\
                .select('academic_year')\
                .range(offset, offset + 999)\
                .execute()
            
            if not batch.data:
                break
            all_students.extend(batch.data)
            if len(batch.data) < 1000:
                break
            offset += 1000
        
        # Count by year
        year_counts = {}
        null_count = 0
        for student in all_students:
            year = student.get('academic_year')
            if year:
                year_counts[year] = year_counts.get(year, 0) + 1
            else:
                null_count += 1
        
        logging.info(f"\nTotal students: {len(all_students)}")
        logging.info(f"Students with NULL academic_year: {null_count}")
        
        logging.info("\nStudents by academic year:")
        for year in sorted(year_counts.keys(), reverse=True):
            logging.info(f"  {year}: {year_counts[year]} students")
        
        # Check Rochdale specifically
        logging.info("\n" + "=" * 60)
        logging.info("ROCHDALE SIXTH FORM COLLEGE CHECK")
        logging.info("=" * 60)
        
        rochdale = supabase.table('establishments')\
            .select('id, name')\
            .ilike('name', '%Rochdale Sixth%')\
            .execute()
        
        if rochdale.data:
            establishment_id = rochdale.data[0]['id']
            logging.info(f"Found: {rochdale.data[0]['name']}")
            
            # Count by year for Rochdale
            rochdale_students = []
            offset = 0
            while True:
                batch = supabase.table('students')\
                    .select('academic_year')\
                    .eq('establishment_id', establishment_id)\
                    .range(offset, offset + 999)\
                    .execute()
                
                if not batch.data:
                    break
                rochdale_students.extend(batch.data)
                if len(batch.data) < 1000:
                    break
                offset += 1000
            
            rochdale_years = {}
            for s in rochdale_students:
                year = s.get('academic_year', 'NULL')
                rochdale_years[year] = rochdale_years.get(year, 0) + 1
            
            logging.info(f"\nRochdale student counts by year:")
            for year in sorted(rochdale_years.keys(), reverse=True):
                logging.info(f"  {year}: {rochdale_years[year]} students")
            
            if rochdale_years.get('2025/2026') == 1026:
                logging.info("✅ Rochdale has exactly 1026 students for 2025/2026!")
            else:
                current_count = rochdale_years.get('2025/2026', 0)
                logging.warning(f"⚠️ Rochdale has {current_count} students for 2025/2026 (expected 1026)")
        
        return True
        
    except Exception as e:
        logging.error(f"Error analyzing data: {e}")
        return False

if __name__ == "__main__":
    success = check_academic_year_column()
    
    if not success:
        logging.info("\n" + "=" * 60)
        logging.info("NEXT STEPS")
        logging.info("=" * 60)
        logging.info("1. Run the SQL migrations in Supabase")
        logging.info("2. Update sync_knack_to_supabase.py to include academic_year")
        logging.info("3. Update app.py to filter by academic_year")
        logging.info("4. Test the dashboard with the new field")
