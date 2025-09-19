#!/usr/bin/env python3
"""
Updated sync process to work with student enrollment history
Supports both workflows:
1. Small schools: Keep accounts, update Year Group
2. Large schools: Delete and re-upload
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

def get_updated_sync_function():
    """
    Returns the updated sync_students_and_vespa_scores function that:
    1. Uses email as the primary identifier (one master student record)
    2. Creates enrollment history entries for each academic year
    3. Detects Year Group changes as progression indicators
    """
    
    return '''
def sync_students_and_vespa_scores():
    """Enhanced sync with enrollment history tracking"""
    logging.info("Syncing students with enrollment history...")
    
    # Track what we're doing
    workflow_stats = {
        'new_students': 0,
        'updated_students': 0,
        'year_progressions': 0,
        'enrollment_records': 0
    }
    
    # Pre-fetch existing students and their current Year Groups
    logging.info("Loading existing student data...")
    student_email_map = {}  # email -> {id, year_group, knack_id}
    
    offset = 0
    limit = 1000
    while True:
        existing = supabase.table('students').select(
            'id', 'email', 'year_group', 'knack_id', 'establishment_id'
        ).limit(limit).offset(offset).execute()
        
        if not existing.data:
            break
            
        for student in existing.data:
            if student.get('email'):
                student_email_map[student['email'].lower()] = {
                    'id': student['id'],
                    'year_group': student.get('year_group'),
                    'knack_id': student.get('knack_id'),
                    'establishment_id': student.get('establishment_id')
                }
        
        if len(existing.data) < limit:
            break
        offset += limit
    
    logging.info(f"Loaded {len(student_email_map)} existing students")
    
    # Process Knack data
    page = 1
    while True:
        # Fetch Object_10 records (VESPA assessments with student info)
        data = make_knack_request('object_10', page=page)
        records = data.get('records', [])
        
        if not records:
            break
        
        for record in records:
            # Extract student info
            student_email = (record.get('field_186', '') or record.get('field_186_raw', {}).get('email', '')).strip().lower()
            if not student_email:
                continue
            
            # Get student details
            knack_id = record['id']
            year_group = record.get('field_144', '')
            course = record.get('field_2299', '')
            faculty = record.get('field_782', '')
            establishment_id = get_establishment_uuid(record.get('field_126', [''])[0])
            
            # Determine workflow based on existing data
            existing_student = student_email_map.get(student_email)
            
            if existing_student:
                # Student exists - check for changes
                workflow = detect_workflow(existing_student, {
                    'knack_id': knack_id,
                    'year_group': year_group
                })
                
                if workflow == 'YEAR_PROGRESSION':
                    # Small school workflow: Year Group changed
                    logging.info(f"Year progression detected for {student_email}: "
                               f"{existing_student['year_group']} -> {year_group}")
                    workflow_stats['year_progressions'] += 1
                    
                elif workflow == 'RE_UPLOAD':
                    # Large school workflow: Different Knack ID (deleted and re-uploaded)
                    logging.info(f"Re-upload detected for {student_email}: "
                               f"Knack ID changed from {existing_student['knack_id']} to {knack_id}")
                
                # Update student record (preserving master ID)
                update_data = {
                    'knack_id': knack_id,  # May have changed
                    'year_group': year_group,
                    'course': course,
                    'faculty': faculty,
                    'updated_at': datetime.now().isoformat()
                }
                
                supabase.table('students').update(update_data).eq('id', existing_student['id']).execute()
                workflow_stats['updated_students'] += 1
                
                # Create enrollment history
                create_enrollment_history(
                    student_id=existing_student['id'],
                    academic_year=calculate_current_academic_year(),
                    knack_id=knack_id,
                    year_group=year_group,
                    previous_year_group=existing_student.get('year_group') if workflow == 'YEAR_PROGRESSION' else None,
                    course=course,
                    faculty=faculty
                )
                workflow_stats['enrollment_records'] += 1
                
            else:
                # New student
                student_data = {
                    'email': student_email,
                    'knack_id': knack_id,
                    'name': extract_student_name(record),
                    'establishment_id': establishment_id,
                    'year_group': year_group,
                    'course': course,
                    'faculty': faculty,
                    'academic_year': calculate_current_academic_year()
                }
                
                result = supabase.table('students').insert(student_data).execute()
                if result.data:
                    new_student_id = result.data[0]['id']
                    workflow_stats['new_students'] += 1
                    
                    # Create initial enrollment
                    create_enrollment_history(
                        student_id=new_student_id,
                        academic_year=calculate_current_academic_year(),
                        knack_id=knack_id,
                        year_group=year_group,
                        course=course,
                        faculty=faculty
                    )
                    workflow_stats['enrollment_records'] += 1
                    
                    # Update our map
                    student_email_map[student_email] = {
                        'id': new_student_id,
                        'year_group': year_group,
                        'knack_id': knack_id
                    }
            
            # Process VESPA scores (unchanged)
            process_vespa_scores(record, student_id=existing_student['id'] if existing_student else new_student_id)
        
        page += 1
        
    # Log summary
    logging.info("Sync complete!")
    logging.info(f"  New students: {workflow_stats['new_students']}")
    logging.info(f"  Updated students: {workflow_stats['updated_students']}")
    logging.info(f"  Year progressions detected: {workflow_stats['year_progressions']}")
    logging.info(f"  Enrollment records created: {workflow_stats['enrollment_records']}")
    
def detect_workflow(existing_student: Dict, new_data: Dict) -> str:
    """
    Detect which workflow is being used:
    - YEAR_PROGRESSION: Same Knack ID, different Year Group (small schools)
    - RE_UPLOAD: Different Knack ID (large schools, delete & re-upload)
    - NO_CHANGE: Same data
    """
    if existing_student['knack_id'] == new_data['knack_id']:
        # Same Knack ID
        if existing_student['year_group'] != new_data['year_group']:
            return 'YEAR_PROGRESSION'
        else:
            return 'NO_CHANGE'
    else:
        # Different Knack ID - student was deleted and re-uploaded
        return 'RE_UPLOAD'

def create_enrollment_history(
    student_id: str,
    academic_year: str,
    knack_id: str,
    year_group: str,
    previous_year_group: Optional[str] = None,
    course: Optional[str] = None,
    faculty: Optional[str] = None
):
    """Create or update enrollment history record"""
    enrollment_data = {
        'student_id': student_id,
        'academic_year': academic_year,
        'knack_id': knack_id,
        'year_group': year_group,
        'course': course,
        'faculty': faculty
    }
    
    if previous_year_group:
        enrollment_data['previous_year_group'] = previous_year_group
    
    # Upsert - will update if exists for this student/year combo
    supabase.table('student_enrollments').upsert(
        enrollment_data,
        on_conflict='student_id,academic_year'
    ).execute()

def calculate_current_academic_year() -> str:
    """Calculate current academic year based on date"""
    today = datetime.now()
    if today.month >= 8:  # August onwards
        return f"{today.year}/{today.year + 1}"
    else:
        return f"{today.year - 1}/{today.year}"
'''

def create_migration_script():
    """
    Create a migration script to update existing deployments
    """
    migration = '''#!/usr/bin/env python3
"""
Migration script to add enrollment history to existing deployment
Run this after creating the student_enrollments table
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
logging.basicConfig(level=logging.INFO)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def migrate_existing_data():
    """
    Create enrollment history from existing student and VESPA data
    """
    logging.info("Starting enrollment history migration...")
    
    # Get all students
    students = []
    offset = 0
    limit = 1000
    
    while True:
        batch = supabase.table('students').select('*').range(offset, offset + limit - 1).execute()
        if not batch.data:
            break
        students.extend(batch.data)
        if len(batch.data) < limit:
            break
        offset += limit
    
    logging.info(f"Processing {len(students)} students...")
    
    enrollment_count = 0
    for student in students:
        # Get all VESPA scores for this student to determine which years they were active
        vespa_scores = supabase.table('vespa_scores').select('academic_year').eq('student_id', student['id']).execute()
        
        academic_years = set()
        for score in vespa_scores.data:
            if score.get('academic_year'):
                academic_years.add(score['academic_year'])
        
        # Create enrollment records for each academic year
        for academic_year in academic_years:
            enrollment_data = {
                'student_id': student['id'],
                'academic_year': academic_year,
                'knack_id': student.get('knack_id'),
                'year_group': student.get('year_group'),
                'course': student.get('course'),
                'faculty': student.get('faculty'),
                'enrollment_status': 'active' if academic_year == student.get('academic_year') else 'completed'
            }
            
            try:
                supabase.table('student_enrollments').upsert(
                    enrollment_data,
                    on_conflict='student_id,academic_year'
                ).execute()
                enrollment_count += 1
            except Exception as e:
                logging.error(f"Failed to create enrollment for student {student['id']}: {e}")
    
    logging.info(f"Migration complete! Created {enrollment_count} enrollment records")

if __name__ == "__main__":
    migrate_existing_data()
'''
    
    with open('migrate_to_enrollment_history.py', 'w') as f:
        f.write(migration)
    
    print("Created migrate_to_enrollment_history.py")

if __name__ == "__main__":
    print("Student Enrollment History - Sync Update")
    print("=" * 60)
    print("\nThis update supports both workflows:")
    print("1. Small schools: Keep accounts, change Year Group")
    print("2. Large schools: Delete and re-upload")
    print("\nKey features:")
    print("- Single master student record per email")
    print("- Enrollment history tracks each academic year")
    print("- Detects Year Group changes as progression indicator")
    print("- Handles Knack ID changes from re-uploads")
    print("\nCreating migration script...")
    create_migration_script()
    print("\nDone! Run migrate_to_enrollment_history.py after creating the tables")
