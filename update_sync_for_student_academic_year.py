#!/usr/bin/env python3
"""
Updates to sync_knack_to_supabase.py to handle academic_year in students table

This shows the changes needed in the sync_students_and_vespa_scores function
"""

# Add this to sync_knack_to_supabase.py in the sync_students_and_vespa_scores function

def sync_students_with_academic_year(record, completion_date):
    """
    Enhanced student sync that includes academic year assignment
    """
    # Calculate academic year for this student based on completion date
    # or current date if no completion
    if completion_date:
        reference_date = datetime.strptime(completion_date, '%Y-%m-%d')
    else:
        reference_date = datetime.now()
    
    # Determine academic year
    academic_year = calculate_academic_year(reference_date)
    
    # Student data with academic year
    student_data = {
        'id': student_id,
        'email': email,
        'name': f"{first_name} {last_name}",
        'establishment_id': establishment_id,
        'academic_year': academic_year,  # NEW FIELD
        'created_at': datetime.now().isoformat() if not existing else None
    }
    
    return student_data

# Example of the modified sync logic:
"""
# In sync_students_and_vespa_scores function, around line 550-600:

# When processing each VESPA record:
for record in vespa_records:
    # Get completion date
    completion_date = record.get('field_424', {}).get('date') if record.get('field_424') else None
    
    # Calculate academic year for this record
    if completion_date:
        academic_year = calculate_academic_year(datetime.strptime(completion_date, '%Y-%m-%d'))
    else:
        academic_year = calculate_academic_year(datetime.now())
    
    # Process student with academic year
    student_data = {
        'id': student_id,
        'email': email,
        'name': f"{first_name} {last_name}",
        'establishment_id': establishment_id,
        'academic_year': academic_year,  # Include academic year
        'created_at': datetime.now().isoformat()
    }
    
    students_batch.append(student_data)

# When upserting students, include academic_year in the on_conflict update:
supabase.table('students').upsert(
    students_batch,
    on_conflict='email',
    # Update academic_year only if the new one is more recent
    on_duplicate='academic_year = CASE WHEN EXCLUDED.academic_year > students.academic_year THEN EXCLUDED.academic_year ELSE students.academic_year END'
).execute()
"""

# Also need to update the query logic in app.py to use student.academic_year:
"""
# In app.py, update the student counting logic:

def get_dashboard_stats(establishment_id, academic_year):
    # Count students based on their academic_year field, not VESPA data
    student_count = supabase.table('students')\
        .select('id', count='exact')\
        .eq('establishment_id', establishment_id)\
        .eq('academic_year', academic_year)\  # Use the student's academic year
        .execute()
    
    # Get VESPA data for those students
    vespa_count = supabase.table('vespa_scores')\
        .select('student_id', count='exact')\
        .eq('academic_year', academic_year)\
        .in_('student_id', [s['id'] for s in students])\
        .execute()
    
    return {
        'total_students': student_count.count,
        'students_with_vespa': vespa_count.count
    }
"""
