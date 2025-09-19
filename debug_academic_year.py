#!/usr/bin/env python3
"""
Debug why academic_year is not being populated
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

def debug_academic_year():
    """Debug why academic_year is not populated"""
    logging.info("=" * 60)
    logging.info("DEBUGGING ACADEMIC YEAR POPULATION")
    logging.info("=" * 60)
    
    # 1. Check if students have created_at dates
    logging.info("\n1. Checking if students have created_at dates...")
    sample_students = supabase.table('students')\
        .select('id, created_at, academic_year')\
        .limit(5)\
        .execute()
    
    for s in sample_students.data:
        logging.info(f"  Student {s['id'][:8]}...")
        logging.info(f"    created_at: {s.get('created_at')}")
        logging.info(f"    academic_year: {s.get('academic_year')}")
    
    # 2. Check if VESPA scores have academic_year
    logging.info("\n2. Checking if vespa_scores have academic_year...")
    sample_vespa = supabase.table('vespa_scores')\
        .select('student_id, academic_year, cycle')\
        .limit(5)\
        .execute()
    
    for v in sample_vespa.data:
        logging.info(f"  VESPA for student {v['student_id'][:8]}...")
        logging.info(f"    academic_year: {v.get('academic_year')}")
        logging.info(f"    cycle: {v.get('cycle')}")
    
    # 3. Count how many students have VESPA data
    logging.info("\n3. Counting students with VESPA data...")
    
    # Get a sample of students
    students_sample = supabase.table('students')\
        .select('id')\
        .limit(100)\
        .execute()
    
    students_with_vespa = 0
    for student in students_sample.data:
        vespa_check = supabase.table('vespa_scores')\
            .select('academic_year')\
            .eq('student_id', student['id'])\
            .limit(1)\
            .execute()
        
        if vespa_check.data:
            students_with_vespa += 1
    
    logging.info(f"  Out of 100 students, {students_with_vespa} have VESPA data")
    
    # 4. Check created_at distribution
    logging.info("\n4. Checking created_at date distribution...")
    
    # Get all students' created_at dates (sample)
    date_sample = supabase.table('students')\
        .select('created_at')\
        .limit(1000)\
        .execute()
    
    date_counts = {
        '2025/2026': 0,
        '2024/2025': 0,
        '2023/2024': 0,
        'older': 0,
        'null': 0
    }
    
    for record in date_sample.data:
        created = record.get('created_at')
        if not created:
            date_counts['null'] += 1
        else:
            try:
                date_obj = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if date_obj >= datetime(2025, 8, 1):
                    date_counts['2025/2026'] += 1
                elif date_obj >= datetime(2024, 8, 1):
                    date_counts['2024/2025'] += 1
                elif date_obj >= datetime(2023, 8, 1):
                    date_counts['2023/2024'] += 1
                else:
                    date_counts['older'] += 1
            except:
                date_counts['null'] += 1
    
    logging.info("  Based on created_at dates (sample of 1000):")
    for year, count in date_counts.items():
        logging.info(f"    {year}: {count} students")
    
    # 5. Try a manual update on one student
    logging.info("\n5. Testing manual update on one student...")
    test_student = students_sample.data[0] if students_sample.data else None
    
    if test_student:
        try:
            result = supabase.table('students')\
                .update({'academic_year': '2025/2026'})\
                .eq('id', test_student['id'])\
                .execute()
            
            if result.data:
                logging.info(f"  ✅ Successfully updated student {test_student['id'][:8]}...")
                
                # Check if it stuck
                check = supabase.table('students')\
                    .select('academic_year')\
                    .eq('id', test_student['id'])\
                    .execute()
                
                if check.data and check.data[0].get('academic_year'):
                    logging.info(f"  ✅ Update confirmed: {check.data[0]['academic_year']}")
                else:
                    logging.info(f"  ❌ Update didn't stick!")
            else:
                logging.info(f"  ❌ Update failed")
        except Exception as e:
            logging.error(f"  ❌ Error updating: {e}")

if __name__ == "__main__":
    debug_academic_year()
