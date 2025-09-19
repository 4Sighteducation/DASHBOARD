#!/usr/bin/env python3
"""
Fix the sync process to preserve academic year data
This prevents overwriting historical student records
"""

import os
from datetime import datetime

def get_fixed_sync_students_function():
    """
    This is the CORRECTED version of the sync_students_and_vespa_scores function
    that preserves academic year data for existing students
    """
    
    return '''
def sync_students_and_vespa_scores():
    """Sync students and VESPA scores from Object_10 with batch processing"""
    logging.info("Syncing students and VESPA scores...")
    
    # ... [previous initialization code remains the same] ...
    
    # Pre-fetch existing students to track what we already have
    logging.info("Loading existing student mappings...")
    student_id_map = {}  # knack_id -> student_id
    student_email_map = {}  # email -> student_id
    student_academic_years = {}  # student_id -> academic_year
    
    offset = 0
    limit = 1000
    while True:
        existing_students = supabase.table('students').select('id', 'knack_id', 'email', 'academic_year').limit(limit).offset(offset).execute()
        if not existing_students.data:
            break
        for student in existing_students.data:
            student_id_map[student['knack_id']] = student['id']
            if student.get('email'):
                student_email_map[student['email'].lower()] = student['id']
                # Track the existing academic year
                student_academic_years[student['id']] = student.get('academic_year')
        if len(existing_students.data) < limit:
            break
        offset += limit
    
    logging.info(f"Loaded {len(student_id_map)} existing student mappings")
    
    # ... [processing loop continues] ...
    
    # When creating student_data (around line 450):
    student_data = {
        'knack_id': record['id'],
        'email': student_email,
        'name': student_name,
        'establishment_id': establishment_id,
        'group': record.get('field_223', ''),
        'year_group': record.get('field_144', ''),
        'course': record.get('field_2299', ''),
        'faculty': record.get('field_782', '')
    }
    
    # CRITICAL FIX: Check if student already exists
    existing_student_id = student_email_map.get(student_email.lower())
    
    if existing_student_id:
        # Student exists - check their academic year
        existing_year = student_academic_years.get(existing_student_id)
        current_year = calculate_academic_year(
            datetime.now().strftime('%d/%m/%Y'),
            establishment_id,
            is_australian=is_australian
        )
        
        # IMPORTANT: Only update non-academic fields
        # Don't overwrite academic_year for existing students
        logging.debug(f"Student {student_email} exists with year {existing_year}")
        
        # Option 1: Skip academic_year update entirely
        # (This preserves historical records)
        
        # Option 2: Update only if student has new VESPA data
        # Check if student has VESPA data for current year
        has_current_vespa = False
        for cycle in [1, 2, 3]:
            # Check VESPA fields for this cycle
            if has_vespa_data_for_cycle(record, cycle):
                has_current_vespa = True
                break
        
        if has_current_vespa and existing_year != current_year:
            # Student has new assessments - they're active this year
            student_data['academic_year'] = current_year
            logging.info(f"Updating {student_email} from {existing_year} to {current_year} due to new VESPA data")
        else:
            # Keep their existing academic year
            pass
    else:
        # New student - set current academic year
        student_data['academic_year'] = calculate_academic_year(
            datetime.now().strftime('%d/%m/%Y'),
            establishment_id,
            is_australian=is_australian
        )
    
    # Continue with batch processing...
'''

def create_patch_file():
    """
    Create a patch file that can be applied to sync_knack_to_supabase.py
    """
    patch_content = '''
--- a/sync_knack_to_supabase.py
+++ b/sync_knack_to_supabase.py
@@ -344,11 +344,15 @@ def sync_students_and_vespa_scores():
     # Pre-fetch existing students to build both email -> student_id and knack_id -> student_id mappings
     logging.info("Loading existing student mappings...")
     student_id_map = {}  # knack_id -> student_id
     student_email_map = {}  # email -> student_id
+    student_academic_years = {}  # student_id -> academic_year
     offset = 0
     limit = 1000
     while True:
-        existing_students = supabase.table('students').select('id', 'knack_id', 'email').limit(limit).offset(offset).execute()
+        existing_students = supabase.table('students').select('id', 'knack_id', 'email', 'academic_year').limit(limit).offset(offset).execute()
         if not existing_students.data:
             break
         for student in existing_students.data:
             student_id_map[student['knack_id']] = student['id']
             # Also map by email for better matching when students are re-uploaded
             if student.get('email'):
                 student_email_map[student['email'].lower()] = student['id']
+                student_academic_years[student['id']] = student.get('academic_year')
         if len(existing_students.data) < limit:
             break
         offset += limit
@@ -440,6 +444,30 @@ def sync_students_and_vespa_scores():
                     'faculty': record.get('field_782', '')
                 }
                 
+                # Check if student already exists
+                existing_student_id = student_email_map.get(student_email.lower())
+                
+                if existing_student_id:
+                    # Student exists - preserve their academic year unless they have new VESPA data
+                    existing_year = student_academic_years.get(existing_student_id)
+                    
+                    # Check if student has VESPA data for any cycle
+                    has_vespa = False
+                    for cycle_num in [1, 2, 3]:
+                        cycle_fields = get_cycle_fields(cycle_num)
+                        for field in cycle_fields:
+                            if record.get(field):
+                                has_vespa = True
+                                break
+                        if has_vespa:
+                            break
+                    
+                    if not has_vespa:
+                        # No new VESPA data - keep existing academic year
+                        student_data.pop('academic_year', None)
+                else:
+                    # New student - add current academic year
+                    student_data['academic_year'] = calculate_academic_year(datetime.now().strftime('%d/%m/%Y'), establishment_id, is_australian)
+                
                 student_batch.append(student_data)
                 students_processed.add(student_email)
'''
    
    with open('sync_academic_year_fix.patch', 'w') as f:
        f.write(patch_content)
    
    print("Created sync_academic_year_fix.patch")
    print("\nTo apply this patch:")
    print("  git apply sync_academic_year_fix.patch")
    print("\nOr manually update sync_knack_to_supabase.py with the changes shown above")

if __name__ == "__main__":
    print("Academic Year Sync Fix")
    print("=" * 60)
    print("\nThis script shows how to fix the sync process to preserve academic year data")
    print("\nThe main issues to fix:")
    print("1. Don't overwrite academic_year for existing students")
    print("2. Only update academic_year if student has new VESPA data")
    print("3. Preserve historical records")
    print("\nGenerating patch file...")
    create_patch_file()

