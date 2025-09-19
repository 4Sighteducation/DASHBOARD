#!/usr/bin/env python3
"""
Fix Rochdale student academic years based on their VESPA data
Students with ONLY 2024/25 data should be marked as archived
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

def fix_student_years():
    """Fix student academic years based on their VESPA data"""
    logging.info("=" * 60)
    logging.info("FIXING ROCHDALE STUDENT ACADEMIC YEARS")
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
    
    # Get all Rochdale students
    all_students = []
    offset = 0
    limit = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id, email, name, academic_year')\
            .eq('establishment_id', establishment_id)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not batch.data:
            break
            
        all_students.extend(batch.data)
        
        if len(batch.data) < limit:
            break
        offset += limit
    
    logging.info(f"\nFound {len(all_students)} total Rochdale students")
    
    # Analyze each student's VESPA data to determine their correct academic year
    students_to_update = []
    batch_size = 50
    
    for i in range(0, len(all_students), batch_size):
        batch = all_students[i:i+batch_size]
        student_ids = [s['id'] for s in batch]
        
        # Get VESPA data for this batch
        vespa_data = supabase.table('vespa_scores')\
            .select('student_id, academic_year')\
            .in_('student_id', student_ids)\
            .execute()
        
        # Group by student
        student_years = {}
        for v in vespa_data.data:
            sid = v['student_id']
            if sid not in student_years:
                student_years[sid] = set()
            student_years[sid].add(v['academic_year'])
        
        # Check each student
        for student in batch:
            sid = student['id']
            if sid in student_years:
                years = student_years[sid]
                
                # If student ONLY has 2024/2025 data, they should be archived
                if years == {'2024/2025'}:
                    if student['academic_year'] != '2024/2025':
                        students_to_update.append({
                            'id': sid,
                            'email': student['email'],
                            'name': student['name'],
                            'current_year': student['academic_year'],
                            'should_be': '2024/2025'
                        })
    
    logging.info(f"\n📊 Students to update: {len(students_to_update)}")
    
    if students_to_update:
        # Show sample
        logging.info("\nSample of students to update (first 5):")
        for s in students_to_update[:5]:
            logging.info(f"  - {s['name']} ({s['email'][:20]}...)")
            logging.info(f"    Current: {s['current_year']} → Should be: {s['should_be']}")
        
        if len(students_to_update) > 5:
            logging.info(f"  ... and {len(students_to_update) - 5} more")
        
        # Ask for confirmation
        logging.info("\n" + "=" * 60)
        response = input(f"Update {len(students_to_update)} students to 2024/2025? (yes/no): ")
        
        if response.lower() == 'yes':
            logging.info("\nUpdating students...")
            
            # Update in batches
            update_batch_size = 100
            total_updated = 0
            
            for i in range(0, len(students_to_update), update_batch_size):
                batch = students_to_update[i:i+update_batch_size]
                student_ids = [s['id'] for s in batch]
                
                try:
                    result = supabase.table('students')\
                        .update({'academic_year': '2024/2025'})\
                        .in_('id', student_ids)\
                        .execute()
                    
                    total_updated += len(result.data)
                    logging.info(f"  Updated batch {i//update_batch_size + 1}: {len(result.data)} students")
                except Exception as e:
                    logging.error(f"Error updating batch: {e}")
            
            logging.info(f"\n✅ Successfully updated {total_updated} students to 2024/2025")
            
            # Verify the fix
            verify_fix(establishment_id)
        else:
            logging.info("Update cancelled")
    else:
        logging.info("No students need updating - academic years appear correct!")
        verify_fix(establishment_id)

def verify_fix(establishment_id):
    """Verify the distribution after the fix"""
    logging.info("\n" + "=" * 60)
    logging.info("VERIFYING FINAL DISTRIBUTION")
    logging.info("=" * 60)
    
    # Count students by academic year
    for year in ['2024/2025', '2025/2026']:
        count = supabase.table('students')\
            .select('id', count='exact')\
            .eq('establishment_id', establishment_id)\
            .eq('academic_year', year)\
            .execute()
        
        logging.info(f"{year}: {count.count} students")
    
    # Count VESPA records by year
    logging.info("\nVESPA records by academic year:")
    
    # Get all student IDs for Rochdale
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
    
    # Count VESPA records in batches
    for year in ['2024/2025', '2025/2026']:
        total_count = 0
        for i in range(0, len(all_students), 50):
            batch_ids = all_students[i:i+50]
            count = supabase.table('vespa_scores')\
                .select('id', count='exact')\
                .in_('student_id', batch_ids)\
                .eq('academic_year', year)\
                .execute()
            total_count += count.count
        
        logging.info(f"  {year}: {total_count} VESPA records")
    
    logging.info("\n✅ Fix complete! The dashboard should now show correct student counts.")
    logging.info("Expected dashboard display:")
    logging.info("  - 2024/25: ~898 students (archived)")
    logging.info("  - 2025/26: ~1405 students (1029 current-only + 376 continuing)")

if __name__ == "__main__":
    try:
        fix_student_years()
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
