#!/usr/bin/env python3
"""
Fix Rochdale Sixth Form College archive data
This script will:
1. Identify duplicate student records (same email, different IDs)
2. Assign correct academic years based on data patterns
3. Preserve historical data for all students
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

def analyze_rochdale_data():
    """Analyze the current state of Rochdale data"""
    logging.info("=" * 60)
    logging.info("ANALYZING ROCHDALE DATA")
    logging.info("=" * 60)
    
    # Get Rochdale's establishment ID
    rochdale = supabase.table('establishments')\
        .select('id, name')\
        .ilike('name', '%Rochdale Sixth Form%')\
        .execute()
    
    if not rochdale.data:
        logging.error("Rochdale Sixth Form College not found!")
        return None
    
    establishment_id = rochdale.data[0]['id']
    logging.info(f"Found: {rochdale.data[0]['name']}")
    
    # Get ALL students for Rochdale with pagination
    all_students = []
    offset = 0
    page_size = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('*')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not batch.data:
            break
            
        all_students.extend(batch.data)
        if len(batch.data) < page_size:
            break
        offset += page_size
    
    logging.info(f"Total student records: {len(all_students)}")
    
    # Group students by email to find duplicates
    students_by_email = {}
    for student in all_students:
        email = student.get('email', '').lower() if student.get('email') else None
        if email:
            if email not in students_by_email:
                students_by_email[email] = []
            students_by_email[email].append(student)
    
    # Analyze patterns
    single_record_students = []
    duplicate_record_students = []
    
    for email, students in students_by_email.items():
        if len(students) == 1:
            single_record_students.append(students[0])
        else:
            duplicate_record_students.append(students)
    
    logging.info(f"\n📊 STUDENT RECORD ANALYSIS:")
    logging.info(f"Unique email addresses: {len(students_by_email)}")
    logging.info(f"Students with single record: {len(single_record_students)}")
    logging.info(f"Students with duplicate records: {len(duplicate_record_students)}")
    
    # For duplicate students, analyze their data
    logging.info("\n🔍 ANALYZING DUPLICATE PATTERNS:")
    
    older_records = []
    newer_records = []
    
    for student_group in duplicate_record_students:
        # Sort by creation date
        sorted_students = sorted(student_group, key=lambda x: x.get('created_at', ''))
        older_records.append(sorted_students[0])  # Oldest record
        newer_records.append(sorted_students[-1])  # Newest record
    
    # Check which records have VESPA data
    logging.info("\n📈 CHECKING VESPA DATA:")
    
    # Process in batches
    batch_size = 50
    
    def check_vespa_for_students(student_list, label):
        has_data_count = 0
        total_vespa_records = 0
        
        for i in range(0, len(student_list), batch_size):
            batch = student_list[i:i+batch_size]
            student_ids = [s['id'] for s in batch]
            
            vespa_data = supabase.table('vespa_scores')\
                .select('student_id, cycle, academic_year')\
                .in_('student_id', student_ids)\
                .execute()
            
            if vespa_data.data:
                student_ids_with_data = set(v['student_id'] for v in vespa_data.data)
                has_data_count += len(student_ids_with_data)
                total_vespa_records += len(vespa_data.data)
        
        logging.info(f"{label}: {has_data_count}/{len(student_list)} have VESPA data ({total_vespa_records} total records)")
        return has_data_count, total_vespa_records
    
    # Check older records
    older_with_data, older_vespa_total = check_vespa_for_students(older_records, "Older duplicate records")
    
    # Check newer records  
    newer_with_data, newer_vespa_total = check_vespa_for_students(newer_records, "Newer duplicate records")
    
    # Check single records
    single_with_data, single_vespa_total = check_vespa_for_students(single_record_students, "Single records")
    
    # Determine which records likely belong to which year
    logging.info("\n💡 LIKELY SCENARIO:")
    logging.info(f"- Older duplicate records: Likely 2024/25 data (Year 12s last year)")
    logging.info(f"- Newer duplicate records: Likely 2025/26 data (Year 13s this year)")
    logging.info(f"- Single records: Mix of departed Year 13s (2024/25) and new students")
    
    return {
        'establishment_id': establishment_id,
        'all_students': all_students,
        'older_records': older_records,
        'newer_records': newer_records,
        'single_records': single_record_students,
        'total_students': len(all_students)
    }

def fix_academic_years(data):
    """Fix academic year assignments for Rochdale data"""
    logging.info("\n" + "=" * 60)
    logging.info("FIXING ACADEMIC YEARS")
    logging.info("=" * 60)
    
    establishment_id = data['establishment_id']
    updates_made = 0
    errors = 0
    
    # Strategy:
    # 1. For duplicate records: older = 2024/25, newer = 2025/26
    # 2. For single records: check creation date or VESPA data patterns
    
    logging.info("\n📝 UPDATING OLDER DUPLICATE RECORDS TO 2024/25:")
    
    # Process older records in batches
    batch_size = 50
    older_student_ids = [s['id'] for s in data['older_records']]
    
    for i in range(0, len(older_student_ids), batch_size):
        batch_ids = older_student_ids[i:i+batch_size]
        
        try:
            # Update VESPA scores for these students to 2024/25
            result = supabase.table('vespa_scores')\
                .update({'academic_year': '2024/2025'})\
                .in_('student_id', batch_ids)\
                .execute()
            
            if result.data:
                updates_made += len(result.data)
                logging.info(f"  Batch {i//batch_size + 1}: Updated {len(result.data)} VESPA records")
        except Exception as e:
            logging.error(f"  Error updating batch: {e}")
            errors += 1
    
    logging.info(f"\n📝 CHECKING SINGLE RECORDS:")
    
    # For single records, we need to be more careful
    # Check their creation dates and existing VESPA data
    single_to_2024 = []
    single_to_2025 = []
    
    for student in data['single_records']:
        created_date = student.get('created_at', '')
        
        # Parse the creation date
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                # If created before August 2025, likely belongs to 2024/25
                if dt < datetime(2025, 8, 1, tzinfo=dt.tzinfo):
                    single_to_2024.append(student['id'])
                else:
                    single_to_2025.append(student['id'])
            except:
                # If we can't parse, check if they have VESPA data
                vespa_check = supabase.table('vespa_scores')\
                    .select('academic_year')\
                    .eq('student_id', student['id'])\
                    .limit(1)\
                    .execute()
                
                if vespa_check.data:
                    # Keep their existing academic year
                    pass
                else:
                    # No data, skip
                    pass
    
    logging.info(f"  Single records to assign to 2024/25: {len(single_to_2024)}")
    logging.info(f"  Single records to assign to 2025/26: {len(single_to_2025)}")
    
    # Update single records to 2024/25
    if single_to_2024:
        for i in range(0, len(single_to_2024), batch_size):
            batch_ids = single_to_2024[i:i+batch_size]
            
            try:
                result = supabase.table('vespa_scores')\
                    .update({'academic_year': '2024/2025'})\
                    .in_('student_id', batch_ids)\
                    .execute()
                
                if result.data:
                    updates_made += len(result.data)
            except Exception as e:
                logging.error(f"  Error updating single records: {e}")
                errors += 1
    
    logging.info(f"\n✅ SUMMARY:")
    logging.info(f"  Total VESPA records updated: {updates_made}")
    logging.info(f"  Errors encountered: {errors}")
    
    return updates_made, errors

def verify_fix(establishment_id):
    """Verify the fix by checking academic year distribution"""
    logging.info("\n" + "=" * 60)
    logging.info("VERIFYING FIX")
    logging.info("=" * 60)
    
    # Get all students for Rochdale
    all_students = []
    offset = 0
    page_size = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not batch.data:
            break
        all_students.extend(batch.data)
        if len(batch.data) < page_size:
            break
        offset += page_size
    
    student_ids = [s['id'] for s in all_students]
    
    # Check VESPA distribution by academic year
    years_data = {}
    batch_size = 100
    
    for year in ['2024/2025', '2025/2026']:
        unique_students = set()
        total_records = 0
        
        for i in range(0, len(student_ids), batch_size):
            batch_ids = student_ids[i:i+batch_size]
            
            vespa_data = supabase.table('vespa_scores')\
                .select('student_id, cycle')\
                .eq('academic_year', year)\
                .in_('student_id', batch_ids)\
                .execute()
            
            if vespa_data.data:
                for record in vespa_data.data:
                    unique_students.add(record['student_id'])
                total_records += len(vespa_data.data)
        
        years_data[year] = {
            'unique_students': len(unique_students),
            'total_records': total_records
        }
    
    logging.info("\n📊 FINAL DATA DISTRIBUTION:")
    logging.info(f"2024/2025:")
    logging.info(f"  Unique students: {years_data['2024/2025']['unique_students']}")
    logging.info(f"  Total VESPA records: {years_data['2024/2025']['total_records']}")
    logging.info(f"\n2025/2026:")
    logging.info(f"  Unique students: {years_data['2025/2026']['unique_students']}")
    logging.info(f"  Total VESPA records: {years_data['2025/2026']['total_records']}")
    
    logging.info("\n✨ The dashboard should now show:")
    logging.info(f"  2024/25: ~{years_data['2024/2025']['unique_students']} students (historical archive)")
    logging.info(f"  2025/26: ~{years_data['2025/2026']['unique_students']} students (current year)")
    
    return years_data

def main():
    """Main execution"""
    try:
        # Step 1: Analyze current state
        data = analyze_rochdale_data()
        if not data:
            return
        
        # Step 2: Ask for confirmation
        logging.info("\n" + "=" * 60)
        logging.info("PROPOSED FIX")
        logging.info("=" * 60)
        logging.info("\nThis script will:")
        logging.info("1. Assign older duplicate records to 2024/2025")
        logging.info("2. Keep newer duplicate records in 2025/2026")
        logging.info("3. Assign single records based on creation date")
        logging.info("\nThis preserves the historical archive while maintaining current data.")
        
        response = input("\n⚠️  Proceed with fix? (yes/no): ")
        if response.lower() != 'yes':
            logging.info("Fix cancelled.")
            return
        
        # Step 3: Apply fixes
        updates_made, errors = fix_academic_years(data)
        
        # Step 4: Verify
        verify_fix(data['establishment_id'])
        
        logging.info("\n" + "=" * 60)
        logging.info("FIX COMPLETE")
        logging.info("=" * 60)
        logging.info("\n📌 NEXT STEPS:")
        logging.info("1. Check the dashboard to verify both years show data")
        logging.info("2. Verify the historical data matches expectations")
        logging.info("3. Consider running the statistics calculation to update aggregates")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
