#!/usr/bin/env python3
"""
Deep investigation of Rochdale Sixth Form College data discrepancy
Dashboard shows 2303 students but we only found 1000
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

def investigate_rochdale():
    """Deep dive into Rochdale data"""
    logging.info("=" * 60)
    logging.info("ROCHDALE SIXTH FORM COLLEGE - DEEP INVESTIGATION")
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
    
    # 1. Check ALL students for this establishment
    logging.info("\n📊 CHECKING STUDENT RECORDS:")
    logging.info("-" * 40)
    
    all_students = supabase.table('students')\
        .select('id, email, knack_id, year_group, created_at')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    logging.info(f"Total student records in database: {len(all_students.data)}")
    
    # Check for duplicates by email
    email_counts = {}
    knack_id_counts = {}
    for student in all_students.data:
        email = student.get('email', '').lower() if student.get('email') else 'no_email'
        knack_id = student.get('knack_id', 'no_knack_id')
        
        email_counts[email] = email_counts.get(email, 0) + 1
        knack_id_counts[knack_id] = knack_id_counts.get(knack_id, 0) + 1
    
    duplicate_emails = {k: v for k, v in email_counts.items() if v > 1 and k != 'no_email'}
    duplicate_knack_ids = {k: v for k, v in knack_id_counts.items() if v > 1 and k != 'no_knack_id'}
    
    if duplicate_emails:
        logging.warning(f"Found {len(duplicate_emails)} duplicate emails!")
        for email, count in list(duplicate_emails.items())[:5]:
            logging.warning(f"  - {email}: {count} records")
    
    if duplicate_knack_ids:
        logging.warning(f"Found {len(duplicate_knack_ids)} duplicate knack_ids!")
        for knack_id, count in list(duplicate_knack_ids.items())[:5]:
            logging.warning(f"  - {knack_id}: {count} records")
    
    # 2. Check VESPA scores - might have multiple cycles per student
    logging.info("\n📈 CHECKING VESPA SCORES:")
    logging.info("-" * 40)
    
    student_ids = [s['id'] for s in all_students.data]
    
    # Process in batches to avoid URL limits
    batch_size = 50
    all_vespa_records = []
    
    for i in range(0, len(student_ids), batch_size):
        batch_ids = student_ids[i:i+batch_size]
        vespa_batch = supabase.table('vespa_scores')\
            .select('*')\
            .in_('student_id', batch_ids)\
            .execute()
        if vespa_batch.data:
            all_vespa_records.extend(vespa_batch.data)
    
    logging.info(f"Total VESPA score records: {len(all_vespa_records)}")
    
    # Analyze by academic year and cycle
    by_year_cycle = {}
    unique_students_by_year = {}
    
    for record in all_vespa_records:
        year = record.get('academic_year', 'Unknown')
        cycle = record.get('cycle', 'Unknown')
        student_id = record.get('student_id')
        
        key = f"{year} - Cycle {cycle}"
        by_year_cycle[key] = by_year_cycle.get(key, 0) + 1
        
        if year not in unique_students_by_year:
            unique_students_by_year[year] = set()
        unique_students_by_year[year].add(student_id)
    
    logging.info("\nVESPA scores by year and cycle:")
    for key, count in sorted(by_year_cycle.items()):
        logging.info(f"  - {key}: {count} records")
    
    logging.info("\nUnique students by academic year:")
    for year, students in sorted(unique_students_by_year.items()):
        logging.info(f"  - {year}: {len(students)} unique students")
    
    # Check for students with multiple records in same cycle
    student_cycle_combos = {}
    for record in all_vespa_records:
        student_id = record.get('student_id')
        cycle = record.get('cycle')
        year = record.get('academic_year')
        key = (student_id, cycle, year)
        student_cycle_combos[key] = student_cycle_combos.get(key, 0) + 1
    
    duplicates = {k: v for k, v in student_cycle_combos.items() if v > 1}
    if duplicates:
        logging.warning(f"\n⚠️ Found {len(duplicates)} duplicate (student, cycle, year) combinations!")
        logging.warning("This could explain inflated counts in the dashboard")
    
    # 3. Check what the dashboard might be counting
    logging.info("\n🔍 SIMULATING DASHBOARD COUNT:")
    logging.info("-" * 40)
    
    # Dashboard might be counting VESPA records, not unique students
    vespa_2025_26 = [r for r in all_vespa_records if r.get('academic_year') == '2025/2026']
    vespa_2024_25 = [r for r in all_vespa_records if r.get('academic_year') == '2024/2025']
    
    logging.info(f"2025/2026: {len(vespa_2025_26)} VESPA records")
    logging.info(f"2024/2025: {len(vespa_2024_25)} VESPA records")
    
    # Check dates on records
    logging.info("\n📅 CHECKING COMPLETION DATES:")
    logging.info("-" * 40)
    
    dates_by_year = {}
    no_date_count = 0
    
    for record in all_vespa_records:
        year = record.get('academic_year', 'Unknown')
        completion_date = record.get('completion_date')
        
        if completion_date:
            if year not in dates_by_year:
                dates_by_year[year] = []
            dates_by_year[year].append(completion_date)
        else:
            no_date_count += 1
    
    logging.info(f"Records without completion dates: {no_date_count}")
    
    for year, dates in sorted(dates_by_year.items()):
        if dates:
            # Parse dates and find min/max
            parsed_dates = []
            for d in dates:
                try:
                    parsed = datetime.fromisoformat(d.replace('Z', '+00:00'))
                    parsed_dates.append(parsed)
                except:
                    pass
            
            if parsed_dates:
                min_date = min(parsed_dates)
                max_date = max(parsed_dates)
                logging.info(f"\n{year}:")
                logging.info(f"  - Earliest: {min_date.strftime('%Y-%m-%d')}")
                logging.info(f"  - Latest: {max_date.strftime('%Y-%m-%d')}")
                logging.info(f"  - Total records with dates: {len(parsed_dates)}")
    
    # 4. Check if there are orphaned VESPA records
    logging.info("\n⚠️ CHECKING FOR ORPHANED RECORDS:")
    logging.info("-" * 40)
    
    # Get all VESPA records for ANY Rochdale student (including deleted ones)
    all_vespa_any = supabase.table('vespa_scores')\
        .select('student_id, cycle, academic_year')\
        .execute()
    
    # Filter for those whose student_id is not in our current student list
    current_student_ids = set(s['id'] for s in all_students.data)
    orphaned_vespa = []
    
    for record in all_vespa_any.data:
        if record['student_id'] not in current_student_ids:
            # Check if this orphaned record might belong to Rochdale
            # by checking if the student ever belonged to Rochdale
            student_check = supabase.table('students')\
                .select('id, establishment_id')\
                .eq('id', record['student_id'])\
                .execute()
            
            if student_check.data and student_check.data[0].get('establishment_id') == establishment_id:
                orphaned_vespa.append(record)
    
    if orphaned_vespa:
        logging.warning(f"Found {len(orphaned_vespa)} VESPA records for deleted/missing Rochdale students!")
    
    return len(all_students.data), len(all_vespa_records), len(vespa_2025_26)

def main():
    """Main execution"""
    try:
        students, vespa_total, vespa_2025 = investigate_rochdale()
        
        logging.info("\n" + "=" * 60)
        logging.info("SUMMARY")
        logging.info("=" * 60)
        logging.info(f"Student records in database: {students}")
        logging.info(f"Total VESPA records: {vespa_total}")
        logging.info(f"VESPA records in 2025/2026: {vespa_2025}")
        logging.info(f"Dashboard shows: 2303 students for 2025/2026")
        logging.info(f"DISCREPANCY: {2303 - vespa_2025} records")
        
        if vespa_2025 > students:
            logging.warning("\n⚠️ More VESPA records than students!")
            logging.warning("This suggests students have multiple VESPA records")
            logging.warning("Dashboard might be counting records, not unique students")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
