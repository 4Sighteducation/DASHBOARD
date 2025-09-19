#!/usr/bin/env python3
"""
Fix Rochdale enrollment count to show exactly 1026 students for 2025/26
We need to identify which students should NOT have 2025/26 data
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

# Target number of students for 2025/26
TARGET_CURRENT_STUDENTS = 1026

def analyze_and_fix():
    """Identify and fix student counts for Rochdale"""
    logging.info("=" * 60)
    logging.info("FIXING ROCHDALE STUDENT COUNT FOR 2025/26")
    logging.info(f"Target: {TARGET_CURRENT_STUDENTS} students")
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
    logging.info(f"Found: {rochdale.data[0]['name']}")
    
    # Get all Rochdale students
    all_students = []
    offset = 0
    limit = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id, email, name, created_at')\
            .eq('establishment_id', establishment_id)\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not batch.data:
            break
        all_students.extend(batch.data)
        if len(batch.data) < limit:
            break
        offset += limit
    
    logging.info(f"\nTotal Rochdale students in database: {len(all_students)}")
    
    # Get students with 2025/26 VESPA data
    students_with_current_data = set()
    batch_size = 50
    
    for i in range(0, len(all_students), batch_size):
        batch = all_students[i:i+batch_size]
        student_ids = [s['id'] for s in batch]
        
        vespa = supabase.table('vespa_scores')\
            .select('student_id')\
            .in_('student_id', student_ids)\
            .eq('academic_year', '2025/2026')\
            .execute()
        
        for v in vespa.data:
            students_with_current_data.add(v['student_id'])
    
    logging.info(f"Students with 2025/26 data: {len(students_with_current_data)}")
    logging.info(f"Need to remove: {len(students_with_current_data) - TARGET_CURRENT_STUDENTS}")
    
    # Strategy: Keep the most recently created students (they were uploaded for this year)
    # Remove 2025/26 data from older students
    
    # Sort students by creation date (newest first)
    all_students.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Identify the current students (most recent TARGET_CURRENT_STUDENTS)
    current_student_ids = set()
    for i, student in enumerate(all_students):
        if i < TARGET_CURRENT_STUDENTS:
            current_student_ids.add(student['id'])
    
    logging.info(f"\nIdentified {len(current_student_ids)} students as current (most recently created)")
    
    # Find students who have 2025/26 data but shouldn't
    students_to_fix = []
    for student_id in students_with_current_data:
        if student_id not in current_student_ids:
            # Find the student details
            student_detail = next((s for s in all_students if s['id'] == student_id), None)
            if student_detail:
                students_to_fix.append({
                    'id': student_id,
                    'email': student_detail['email'],
                    'name': student_detail['name'],
                    'created_at': student_detail['created_at']
                })
    
    logging.info(f"\n📊 Students to remove from 2025/26: {len(students_to_fix)}")
    
    if students_to_fix:
        # Show sample
        logging.info("\nSample of students to remove from 2025/26 (first 5):")
        for s in students_to_fix[:5]:
            logging.info(f"  - {s['name']} ({s['email'][:30]}...)")
            logging.info(f"    Created: {s['created_at']}")
        
        if len(students_to_fix) > 5:
            logging.info(f"  ... and {len(students_to_fix) - 5} more")
        
        # Count VESPA records to be moved
        total_vespa_records = 0
        for student_id in [s['id'] for s in students_to_fix]:
            count = supabase.table('vespa_scores')\
                .select('id', count='exact')\
                .eq('student_id', student_id)\
                .eq('academic_year', '2025/2026')\
                .execute()
            total_vespa_records += count.count
        
        logging.info(f"\nTotal VESPA records to move to 2024/25: {total_vespa_records}")
        
        # Ask for confirmation
        logging.info("\n" + "=" * 60)
        logging.info("This will move these students' 2025/26 data to 2024/25")
        logging.info("ensuring only current students show in 2025/26")
        response = input(f"Proceed with fix? (yes/no): ")
        
        if response.lower() == 'yes':
            logging.info("\nMoving VESPA records...")
            
            # Update VESPA records in batches
            student_ids_to_fix = [s['id'] for s in students_to_fix]
            updated_count = 0
            
            for i in range(0, len(student_ids_to_fix), 10):
                batch_ids = student_ids_to_fix[i:i+10]
                
                try:
                    # Move their 2025/26 VESPA data to 2024/25
                    result = supabase.table('vespa_scores')\
                        .update({'academic_year': '2024/2025'})\
                        .in_('student_id', batch_ids)\
                        .eq('academic_year', '2025/2026')\
                        .execute()
                    
                    updated_count += len(result.data)
                    logging.info(f"  Batch {i//10 + 1}: Moved {len(result.data)} records")
                except Exception as e:
                    logging.error(f"Error updating batch: {e}")
            
            # Also update question_responses
            logging.info("\nUpdating question_responses...")
            qr_updated = 0
            
            for i in range(0, len(student_ids_to_fix), 10):
                batch_ids = student_ids_to_fix[i:i+10]
                
                try:
                    result = supabase.table('question_responses')\
                        .update({'academic_year': '2024/2025'})\
                        .in_('student_id', batch_ids)\
                        .eq('academic_year', '2025/2026')\
                        .execute()
                    
                    qr_updated += len(result.data)
                    logging.info(f"  Batch {i//10 + 1}: Updated {len(result.data)} question responses")
                except Exception as e:
                    logging.error(f"Error updating question responses: {e}")
            
            logging.info(f"\n✅ Successfully moved {updated_count} VESPA records")
            logging.info(f"✅ Successfully updated {qr_updated} question responses")
            
            # Verify the fix
            verify_fix(establishment_id)
        else:
            logging.info("Fix cancelled")
    else:
        logging.info("No students need to be removed from 2025/26")
        verify_fix(establishment_id)

def verify_fix(establishment_id):
    """Verify the student counts after the fix"""
    logging.info("\n" + "=" * 60)
    logging.info("VERIFYING FINAL COUNTS")
    logging.info("=" * 60)
    
    # Get all students
    all_students = []
    offset = 0
    limit = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not batch.data:
            break
        all_students.extend([s['id'] for s in batch.data])
        if len(batch.data) < limit:
            break
        offset += limit
    
    # Count unique students by academic year
    for year in ['2024/2025', '2025/2026']:
        unique_students = set()
        
        for i in range(0, len(all_students), 50):
            batch_ids = all_students[i:i+50]
            
            vespa = supabase.table('vespa_scores')\
                .select('student_id')\
                .in_('student_id', batch_ids)\
                .eq('academic_year', year)\
                .execute()
            
            for v in vespa.data:
                unique_students.add(v['student_id'])
        
        logging.info(f"{year}: {len(unique_students)} students with VESPA data")
    
    logging.info(f"\n✅ Target was {TARGET_CURRENT_STUDENTS} students for 2025/26")
    logging.info("The dashboard should now show the correct student counts!")

if __name__ == "__main__":
    try:
        analyze_and_fix()
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
