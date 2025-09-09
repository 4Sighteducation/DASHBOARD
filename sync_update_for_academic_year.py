#!/usr/bin/env python3
"""
Update sync_knack_to_supabase.py to include academic_year in student records

Add this modification to the sync_students_and_vespa_scores function
"""

# CHANGES NEEDED IN sync_knack_to_supabase.py:

# Around line 430-440, update the student_data dictionary:
"""
# OLD CODE (line 430-439):
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

# NEW CODE - ADD academic_year:
# Get the completion date to determine academic year
completion_date_raw = record.get('field_855')  # Or use current date if no completion
if completion_date_raw and completion_date_raw.strip():
    try:
        date_obj = datetime.strptime(completion_date_raw, '%d/%m/%Y')
        academic_year = calculate_academic_year(
            completion_date_raw,
            establishment_id,
            is_uk_school=True  # You may need to determine this
        )
    except ValueError:
        # If date parsing fails, use current academic year
        academic_year = calculate_academic_year(
            datetime.now().strftime('%d/%m/%Y'),
            establishment_id,
            is_uk_school=True
        )
else:
    # No completion date, use current academic year
    academic_year = calculate_academic_year(
        datetime.now().strftime('%d/%m/%Y'),
        establishment_id,
        is_uk_school=True
    )

student_data = {
    'knack_id': record['id'],
    'email': student_email,
    'name': student_name,
    'establishment_id': establishment_id,
    'academic_year': academic_year,  # NEW FIELD
    'group': record.get('field_223', ''),
    'year_group': record.get('field_144', ''),
    'course': record.get('field_2299', ''),
    'faculty': record.get('field_782', '')
}
"""

# ALSO, when upserting students (around line 453), consider updating academic_year:
"""
# The upsert should update academic_year if it's newer
result = supabase.table('students').upsert(
    student_batch,
    on_conflict='email'
).execute()

# Note: Supabase will update all fields on conflict by default
# If you want to preserve the existing academic_year and only update if newer,
# you'll need to handle that logic separately
"""

# IMPORTANT: The calculate_academic_year function already exists in the file
# It's used for VESPA scores, so we can reuse it for students too
