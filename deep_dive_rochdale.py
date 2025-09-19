#!/usr/bin/env python3
"""
Deep dive into Rochdale data to understand the actual structure
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging
from collections import defaultdict

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

def deep_dive():
    """Deep dive into Rochdale data"""
    logging.info("=" * 60)
    logging.info("ROCHDALE DATA DEEP DIVE")
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
    logging.info(f"Found Rochdale: {rochdale.data[0]['name']}")
    logging.info(f"Establishment ID: {establishment_id}")
    
    # Get ALL students for Rochdale with pagination
    all_students = []
    offset = 0
    batch_size = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('*')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + batch_size - 1)\
            .execute()
        
        if not batch.data:
            break
            
        all_students.extend(batch.data)
        logging.info(f"Fetched {len(batch.data)} students (total so far: {len(all_students)})")
        
        if len(batch.data) < batch_size:
            break
        offset += batch_size
    
    logging.info(f"\nTotal Rochdale students: {len(all_students)}")
    
    # Analyze students by various attributes
    logging.info("\n" + "=" * 40)
    logging.info("STUDENT ANALYSIS")
    logging.info("=" * 40)
    
    # Group by email to find duplicates
    email_groups = defaultdict(list)
    for student in all_students:
        if student.get('email'):
            email_groups[student['email']].append(student)
    
    duplicates = {email: students for email, students in email_groups.items() if len(students) > 1}
    logging.info(f"\nEmails with multiple student records: {len(duplicates)}")
    
    if duplicates:
        # Show first 5 examples
        for i, (email, students) in enumerate(list(duplicates.items())[:5]):
            logging.info(f"\nExample {i+1}: {email}")
            for s in students:
                logging.info(f"  - ID: {s['id'][:8]}... Created: {s.get('created_at', 'N/A')}")
    
    # Check for students by year group patterns
    year_groups = defaultdict(int)
    for student in all_students:
        year_group = student.get('year_group', 'Unknown')
        year_groups[year_group] += 1
    
    logging.info("\n" + "=" * 40)
    logging.info("YEAR GROUP DISTRIBUTION")
    logging.info("=" * 40)
    for year, count in sorted(year_groups.items()):
        logging.info(f"{year}: {count} students")
    
    # Check creation dates
    logging.info("\n" + "=" * 40)
    logging.info("CREATION DATE ANALYSIS")
    logging.info("=" * 40)
    
    created_2024 = 0
    created_2025 = 0
    for student in all_students:
        created = student.get('created_at', '')
        if '2024' in created:
            created_2024 += 1
        elif '2025' in created:
            created_2025 += 1
    
    logging.info(f"Created in 2024: {created_2024} students")
    logging.info(f"Created in 2025: {created_2025} students")
    
    # Check VESPA scores and their academic years
    logging.info("\n" + "=" * 40)
    logging.info("VESPA SCORES ANALYSIS")
    logging.info("=" * 40)
    
    # Get sample of student IDs for VESPA check
    sample_ids = [s['id'] for s in all_students[:100]]  # Check first 100
    
    vespa_scores = supabase.table('vespa_scores')\
        .select('student_id, cycle, academic_year, completion_date')\
        .in_('student_id', sample_ids)\
        .execute()
    
    vespa_by_year = defaultdict(set)
    vespa_by_date = defaultdict(int)
    
    for score in vespa_scores.data:
        year = score.get('academic_year', 'Unknown')
        vespa_by_year[year].add(score['student_id'])
        
        completion = score.get('completion_date', '')
        if completion:
            date_prefix = completion[:7]  # YYYY-MM
            vespa_by_date[date_prefix] += 1
    
    logging.info("\nVESPA records by academic year (sample of 100 students):")
    for year, students in sorted(vespa_by_year.items()):
        logging.info(f"  {year}: {len(students)} unique students")
    
    logging.info("\nVESPA completion dates distribution (sample):")
    for date, count in sorted(vespa_by_date.items())[-10:]:  # Show last 10 months
        logging.info(f"  {date}: {count} records")
    
    # Check for patterns in student names/IDs that might indicate year groups
    logging.info("\n" + "=" * 40)
    logging.info("CHECKING FOR DATA PATTERNS")
    logging.info("=" * 40)
    
    # Sample some students to show their full data
    logging.info("\nSample student records (first 3):")
    for i, student in enumerate(all_students[:3]):
        logging.info(f"\nStudent {i+1}:")
        logging.info(f"  ID: {student['id']}")
        logging.info(f"  Email: {student.get('email', 'N/A')}")
        logging.info(f"  Name: {student.get('first_name', '')} {student.get('last_name', '')}")
        logging.info(f"  Year Group: {student.get('year_group', 'N/A')}")
        logging.info(f"  Created: {student.get('created_at', 'N/A')}")
        logging.info(f"  Updated: {student.get('updated_at', 'N/A')}")
        
        # Get this student's VESPA scores
        vespa = supabase.table('vespa_scores')\
            .select('cycle, academic_year, completion_date, overall')\
            .eq('student_id', student['id'])\
            .execute()
        
        if vespa.data:
            logging.info("  VESPA Scores:")
            for v in vespa.data:
                logging.info(f"    Cycle {v['cycle']}: {v['academic_year']} (completed: {v.get('completion_date', 'N/A')[:10]})")

if __name__ == "__main__":
    deep_dive()
