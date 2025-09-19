#!/usr/bin/env python3
"""
Fix Rochdale Sixth Form College academic year data
- Restore 2024-25 archive data
- Correct academic year assignments for manually imported data
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

def investigate_rochdale_data():
    """Investigate current state of Rochdale data"""
    logging.info("=" * 60)
    logging.info("ROCHDALE SIXTH FORM COLLEGE DATA INVESTIGATION")
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
    logging.info(f"Found: {rochdale.data[0]['name']} (ID: {establishment_id})")
    
    # Check students by academic year
    logging.info("\n📊 STUDENT COUNTS BY ACADEMIC YEAR:")
    logging.info("-" * 40)
    
    # Get all students for Rochdale
    all_students = supabase.table('students')\
        .select('id, email, knack_id, year_group')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    logging.info(f"Total students in database: {len(all_students.data)}")
    
    # Check VESPA scores by academic year
    for year in ['2024/2025', '2025/2026']:
        # Process in smaller batches to avoid URL length limits
        student_ids = [s['id'] for s in all_students.data]
        batch_size = 50  # Process 50 students at a time
        unique_students = set()
        total_vespa_count = 0
        
        for i in range(0, len(student_ids), batch_size):
            batch_ids = student_ids[i:i+batch_size]
            
            vespa_batch = supabase.table('vespa_scores')\
                .select('student_id')\
                .eq('academic_year', year)\
                .in_('student_id', batch_ids)\
                .execute()
            
            if vespa_batch.data:
                for v in vespa_batch.data:
                    unique_students.add(v['student_id'])
                total_vespa_count += len(vespa_batch.data)
        
        logging.info(f"\n{year}:")
        logging.info(f"  - Unique students with VESPA scores: {len(unique_students)}")
        logging.info(f"  - Total VESPA records: {total_vespa_count}")
        
        # Check question responses in batches
        if unique_students:
            total_responses = 0
            unique_list = list(unique_students)
            
            for i in range(0, len(unique_list), batch_size):
                batch_ids = unique_list[i:i+batch_size]
                responses = supabase.table('question_responses')\
                    .select('id', count='exact')\
                    .eq('academic_year', year)\
                    .in_('student_id', batch_ids)\
                    .execute()
                total_responses += responses.count
            
            logging.info(f"  - Question responses: {total_responses}")
    
    # Check for orphaned VESPA scores (no completion date)
    logging.info("\n🔍 CHECKING FOR DATA WITHOUT DATES:")
    logging.info("-" * 40)
    
    # Process in batches to avoid URL length limits
    student_ids = [s['id'] for s in all_students.data]
    batch_size = 50
    all_no_date_vespa = []
    
    for i in range(0, len(student_ids), batch_size):
        batch_ids = student_ids[i:i+batch_size]
        
        batch_vespa = supabase.table('vespa_scores')\
            .select('student_id, cycle, academic_year, completion_date')\
            .in_('student_id', batch_ids)\
            .is_('completion_date', 'null')\
            .execute()
        
        if batch_vespa.data:
            all_no_date_vespa.extend(batch_vespa.data)
    
    if all_no_date_vespa:
        logging.info(f"Found {len(all_no_date_vespa)} VESPA records without completion dates")
        # Group by academic year
        by_year = {}
        for record in all_no_date_vespa:
            year = record.get('academic_year', 'Unknown')
            by_year[year] = by_year.get(year, 0) + 1
        for year, count in by_year.items():
            logging.info(f"  - {year}: {count} records")
    
    # Check for students with data in both years
    logging.info("\n🔄 CHECKING FOR STUDENTS WITH DATA IN MULTIPLE YEARS:")
    logging.info("-" * 40)
    
    students_2024 = set()
    students_2025 = set()
    
    for year, student_set in [('2024/2025', students_2024), ('2025/2026', students_2025)]:
        # Process in batches
        for i in range(0, len(student_ids), batch_size):
            batch_ids = student_ids[i:i+batch_size]
            
            vespa = supabase.table('vespa_scores')\
                .select('student_id')\
                .eq('academic_year', year)\
                .in_('student_id', batch_ids)\
                .execute()
            if vespa.data:
                for v in vespa.data:
                    student_set.add(v['student_id'])
    
    overlap = students_2024.intersection(students_2025)
    if overlap:
        logging.info(f"Found {len(overlap)} students with data in BOTH academic years")
        logging.info("This suggests data migration issues")
    else:
        logging.info("No students found with data in both years")
    
    logging.info(f"\nStudents only in 2024/2025: {len(students_2024 - students_2025)}")
    logging.info(f"Students only in 2025/2026: {len(students_2025 - students_2024)}")
    
    return establishment_id, all_students.data

def fix_academic_years(establishment_id, students):
    """Fix academic year assignments based on completion dates"""
    logging.info("\n" + "=" * 60)
    logging.info("FIXING ACADEMIC YEAR ASSIGNMENTS")
    logging.info("=" * 60)
    
    student_ids = [s['id'] for s in students]
    
    # Step 1: Fix VESPA scores with wrong academic year
    logging.info("\n📝 Step 1: Checking VESPA scores...")
    
    # Get all VESPA scores for these students in batches
    batch_size = 50
    all_vespa_data = []
    
    for i in range(0, len(student_ids), batch_size):
        batch_ids = student_ids[i:i+batch_size]
        
        batch_vespa = supabase.table('vespa_scores')\
            .select('*')\
            .in_('student_id', batch_ids)\
            .execute()
        
        if batch_vespa.data:
            all_vespa_data.extend(batch_vespa.data)
    
    # Create a wrapper object to mimic the original response
    all_vespa = type('obj', (object,), {'data': all_vespa_data})
    
    updates_2024 = []
    updates_2025 = []
    
    for record in all_vespa.data:
        completion_date = record.get('completion_date')
        current_year = record.get('academic_year')
        
        if completion_date:
            # Parse date and determine correct academic year
            date_obj = datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
            if date_obj.month >= 8:
                correct_year = f"{date_obj.year}/{date_obj.year + 1}"
            else:
                correct_year = f"{date_obj.year - 1}/{date_obj.year}"
            
            if current_year != correct_year:
                if correct_year == '2024/2025':
                    updates_2024.append(record['id'])
                elif correct_year == '2025/2026':
                    updates_2025.append(record['id'])
    
    # Apply updates
    if updates_2024:
        logging.info(f"Moving {len(updates_2024)} VESPA records to 2024/2025...")
        for record_id in updates_2024:
            supabase.table('vespa_scores')\
                .update({'academic_year': '2024/2025'})\
                .eq('id', record_id)\
                .execute()
    
    if updates_2025:
        logging.info(f"Moving {len(updates_2025)} VESPA records to 2025/2026...")
        for record_id in updates_2025:
            supabase.table('vespa_scores')\
                .update({'academic_year': '2025/2026'})\
                .eq('id', record_id)\
                .execute()
    
    # Step 2: Fix question responses
    logging.info("\n📝 Step 2: Fixing question responses...")
    
    # Get all cycles to determine dates
    cycles_2024 = []
    cycles_2025 = []
    
    # Check VESPA scores to determine which cycles belong to which year
    vespa_by_cycle = {}
    for record in all_vespa.data:
        cycle = record.get('cycle')
        year = record.get('academic_year')
        if cycle not in vespa_by_cycle:
            vespa_by_cycle[cycle] = year
    
    # Update question responses to match VESPA academic years
    for cycle, academic_year in vespa_by_cycle.items():
        if cycle and academic_year:
            logging.info(f"Setting cycle {cycle} question responses to {academic_year}...")
            
            # Update in batches to avoid URL length limits
            total_updated = 0
            for i in range(0, len(student_ids), batch_size):
                batch_ids = student_ids[i:i+batch_size]
                
                result = supabase.table('question_responses')\
                    .update({'academic_year': academic_year})\
                    .in_('student_id', batch_ids)\
                    .eq('cycle', cycle)\
                    .execute()
                
                if result.data:
                    total_updated += len(result.data)
            
            if total_updated > 0:
                logging.info(f"  Updated {total_updated} question responses")
    
    logging.info("\n✅ Academic year fix completed!")

def generate_summary(establishment_id):
    """Generate summary after fixes"""
    logging.info("\n" + "=" * 60)
    logging.info("FINAL DATA SUMMARY")
    logging.info("=" * 60)
    
    # Get all students for Rochdale
    all_students = supabase.table('students')\
        .select('id')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    student_ids = [s['id'] for s in all_students.data]
    
    batch_size = 50
    for year in ['2024/2025', '2025/2026']:
        logging.info(f"\n📊 Academic Year {year}:")
        
        # VESPA scores - process in batches
        all_vespa_data = []
        for i in range(0, len(student_ids), batch_size):
            batch_ids = student_ids[i:i+batch_size]
            
            vespa_batch = supabase.table('vespa_scores')\
                .select('student_id, cycle')\
                .eq('academic_year', year)\
                .in_('student_id', batch_ids)\
                .execute()
            
            if vespa_batch.data:
                all_vespa_data.extend(vespa_batch.data)
        
        unique_students = set(v['student_id'] for v in all_vespa_data)
        cycles = set(v['cycle'] for v in all_vespa_data if v['cycle'])
        
        logging.info(f"  - Students with VESPA scores: {len(unique_students)}")
        logging.info(f"  - Total VESPA records: {len(all_vespa_data)}")
        logging.info(f"  - Cycles present: {sorted(cycles)}")
        
        # Question responses - process in batches
        if unique_students:
            total_responses = 0
            unique_list = list(unique_students)
            
            for i in range(0, len(unique_list), batch_size):
                batch_ids = unique_list[i:i+batch_size]
                responses = supabase.table('question_responses')\
                    .select('id', count='exact')\
                    .eq('academic_year', year)\
                    .in_('student_id', batch_ids)\
                    .execute()
                total_responses += responses.count
            
            logging.info(f"  - Question responses: {total_responses}")

def main():
    """Main execution"""
    try:
        # Investigate current state
        result = investigate_rochdale_data()
        if not result:
            return
        
        establishment_id, students = result
        
        # Ask for confirmation
        print("\n" + "=" * 60)
        print("⚠️  READY TO FIX ROCHDALE SIXTH FORM COLLEGE DATA")
        print("=" * 60)
        print("\nThis will:")
        print("1. Reassign VESPA scores to correct academic years based on dates")
        print("2. Match question responses to their VESPA score years")
        print("3. Restore the 2024/2025 archive data")
        print("\nPress Enter to continue or Ctrl+C to cancel...")
        input()
        
        # Apply fixes
        fix_academic_years(establishment_id, students)
        
        # Generate final summary
        generate_summary(establishment_id)
        
        logging.info("\n✅ All fixes completed successfully!")
        logging.info("\n⚠️  IMPORTANT: You may need to:")
        logging.info("1. Refresh the statistics calculations")
        logging.info("2. Clear any cached data in Redis") 
        logging.info("3. Refresh the dashboard to see changes")
        
    except KeyboardInterrupt:
        logging.info("\n❌ Operation cancelled by user")
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
