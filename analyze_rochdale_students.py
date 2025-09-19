#!/usr/bin/env python3
"""
Analyze Rochdale student distribution to understand the count discrepancy
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

def analyze_students():
    """Analyze student distribution by their VESPA data"""
    logging.info("=" * 60)
    logging.info("ROCHDALE STUDENT ANALYSIS")
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
    logging.info(f"Establishment ID: {establishment_id}")
    
    # Get ALL Rochdale students
    logging.info("\nFetching all students...")
    all_students = []
    offset = 0
    batch_size = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id, email, created_at, updated_at')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + batch_size - 1)\
            .execute()
        
        if not batch.data:
            break
            
        all_students.extend(batch.data)
        
        if len(batch.data) < batch_size:
            break
        offset += batch_size
    
    logging.info(f"Total students in database: {len(all_students)}")
    
    # Now analyze which students have data in which academic year
    students_2024_25_only = []
    students_2025_26_only = []
    students_both_years = []
    students_no_vespa = []
    
    # Process in batches to check VESPA scores
    batch_size = 50
    for i in range(0, len(all_students), batch_size):
        batch = all_students[i:i+batch_size]
        batch_ids = [s['id'] for s in batch]
        
        # Get VESPA scores for this batch
        vespa_scores = supabase.table('vespa_scores')\
            .select('student_id, academic_year, cycle, completion_date')\
            .in_('student_id', batch_ids)\
            .execute()
        
        # Group by student
        student_vespa = {}
        for score in vespa_scores.data:
            sid = score['student_id']
            if sid not in student_vespa:
                student_vespa[sid] = {'2024/2025': [], '2025/2026': []}
            year = score.get('academic_year', 'Unknown')
            if year in student_vespa[sid]:
                student_vespa[sid][year].append(score)
        
        # Categorize students
        for student in batch:
            sid = student['id']
            if sid not in student_vespa:
                students_no_vespa.append(student)
            else:
                has_2024 = len(student_vespa[sid]['2024/2025']) > 0
                has_2025 = len(student_vespa[sid]['2025/2026']) > 0
                
                if has_2024 and has_2025:
                    students_both_years.append(student)
                elif has_2024:
                    students_2024_25_only.append(student)
                elif has_2025:
                    students_2025_26_only.append(student)
                else:
                    students_no_vespa.append(student)
        
        logging.info(f"Processed {min(i + batch_size, len(all_students))}/{len(all_students)} students...")
    
    # Report findings
    logging.info("\n" + "=" * 60)
    logging.info("STUDENT DISTRIBUTION BY ACADEMIC YEAR DATA")
    logging.info("=" * 60)
    
    logging.info(f"\n📊 Student Categories:")
    logging.info(f"  Students with ONLY 2024/2025 data: {len(students_2024_25_only)}")
    logging.info(f"  Students with ONLY 2025/2026 data: {len(students_2025_26_only)}")
    logging.info(f"  Students with BOTH years data: {len(students_both_years)}")
    logging.info(f"  Students with NO VESPA data: {len(students_no_vespa)}")
    logging.info(f"  TOTAL: {len(all_students)}")
    
    # The dashboard likely shows:
    # - Current year: students_2025_26_only + students_both_years
    # - Last year: students_2024_25_only (if they have a separate view)
    
    current_year_count = len(students_2025_26_only) + len(students_both_years)
    logging.info(f"\n📈 Dashboard perspective:")
    logging.info(f"  Students showing in 2025/26: {current_year_count} (matches dashboard: ~1405)")
    logging.info(f"  Students ONLY in 2024/25: {len(students_2024_25_only)} (should be in archive)")
    
    # Analyze the "both years" students more closely
    if students_both_years:
        logging.info(f"\n🔍 Analyzing {len(students_both_years)} students with data in BOTH years:")
        
        # Check first 10 as examples
        for student in students_both_years[:10]:
            sid = student['id']
            email = student.get('email', 'No email')
            
            # Get their VESPA data
            vespa = supabase.table('vespa_scores')\
                .select('cycle, academic_year, completion_date')\
                .eq('student_id', sid)\
                .order('cycle')\
                .execute()
            
            logging.info(f"\n  Student: {email}")
            for v in vespa.data:
                logging.info(f"    Cycle {v['cycle']}: {v['academic_year']} (completed: {v.get('completion_date', 'N/A')[:10]})")
    
    # Recommendation
    logging.info("\n" + "=" * 60)
    logging.info("RECOMMENDATION")
    logging.info("=" * 60)
    logging.info(f"\n🎯 The issue:")
    logging.info(f"  - You have {len(students_both_years)} students with data in BOTH academic years")
    logging.info(f"  - These are your continuing students (Year 12 → Year 13)")
    logging.info(f"  - They're being counted in the current year (correct)")
    logging.info(f"  - But there are also {len(students_2024_25_only)} students with ONLY 2024/25 data")
    logging.info(f"  - These appear to be departed Year 13s from last year")
    
    if students_2024_25_only:
        logging.info(f"\n📋 Students that should probably be archived (first 10):")
        for student in students_2024_25_only[:10]:
            logging.info(f"  - {student.get('email', 'No email')}")
    
    return {
        'total': len(all_students),
        '2024_only': len(students_2024_25_only),
        '2025_only': len(students_2025_26_only),
        'both_years': len(students_both_years),
        'no_vespa': len(students_no_vespa),
        'students_2024_only': students_2024_25_only
    }

if __name__ == "__main__":
    result = analyze_students()
