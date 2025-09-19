#!/usr/bin/env python3
"""
Fix for the API endpoint to query students based on VESPA data, not academic_year field
This needs to be applied to app.py around line 5645-5650
"""

# THE PROBLEM: Current code in app.py (around line 5645-5650)
"""
query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)

# IMPORTANT: Filter by academic_year if provided
if academic_year:
    query = query.eq('academic_year', academic_year)  # THIS IS WRONG!
"""

# THE FIX: Replace with this code
def get_fixed_student_query():
    """
    This should replace the student query logic in get_school_statistics_query function
    around lines 5640-5680 in app.py
    """
    return '''
        # Get filtered students for queries
        all_students = []
        offset = 0
        limit = 1000
        
        # First, get ALL students for this establishment
        while True:
            # Build query WITHOUT academic_year filter on students table
            query = supabase_client.table('students').select('id, email, name, year_group, course, faculty, group').eq('establishment_id', establishment_uuid)
            
            # Apply other filters (but NOT academic_year)
            if student_id:
                query = query.eq('id', student_id)
            else:
                if year_group and year_group != 'all':
                    query = query.eq('year_group', year_group)
                if group and group != 'all':
                    query = query.eq('group', group)
                if faculty and faculty != 'all':
                    query = query.eq('faculty', faculty)
            
            students_batch = query.limit(limit).offset(offset).execute()
            
            batch_count = len(students_batch.data) if students_batch.data else 0
            app.logger.info(f"Student fetch batch: offset={offset}, got {batch_count} students")
            
            if not students_batch.data:
                break
                
            all_students.extend(students_batch.data)
            
            if batch_count < limit:
                break
                
            offset += limit
        
        # Now filter by who has VESPA data for the selected academic year
        if academic_year:
            students_with_vespa = []
            
            # Check in batches who has VESPA data for this year
            for i in range(0, len(all_students), 50):
                batch = all_students[i:i+50]
                batch_ids = [s['id'] for s in batch]
                
                # Check which of these students have VESPA data for the selected year
                vespa_check = supabase_client.table('vespa_scores')\
                    .select('student_id')\
                    .in_('student_id', batch_ids)\
                    .eq('academic_year', academic_year)\
                    .execute()
                
                students_with_vespa_ids = set(v['student_id'] for v in vespa_check.data)
                
                # Keep only students who have VESPA data for this year
                for student in batch:
                    if student['id'] in students_with_vespa_ids:
                        students_with_vespa.append(student)
            
            all_students = students_with_vespa
            app.logger.info(f"After academic year filter: {len(all_students)} students have data for {academic_year}")
        
        student_ids = [s['id'] for s in all_students]
        app.logger.info(f"Found {len(student_ids)} students for establishment {establishment_id}")
'''

# ALTERNATIVE: Quick hotfix using RPC function
def create_rpc_function_for_dashboard():
    """
    Create a Supabase RPC function that the dashboard can call directly
    This bypasses the broken Python API
    """
    return '''
-- Run this in Supabase SQL Editor to create the function

CREATE OR REPLACE FUNCTION get_students_for_academic_year(
    p_establishment_id UUID,
    p_academic_year VARCHAR,
    p_year_group VARCHAR DEFAULT NULL,
    p_group VARCHAR DEFAULT NULL,
    p_faculty VARCHAR DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    email VARCHAR,
    name VARCHAR,
    year_group VARCHAR,
    course VARCHAR,
    faculty VARCHAR,
    group VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        s.id,
        s.email,
        s.name,
        s.year_group,
        s.course,
        s.faculty,
        s.group
    FROM students s
    WHERE s.establishment_id = p_establishment_id
    -- Filter by VESPA data presence, not academic_year field
    AND EXISTS (
        SELECT 1 
        FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = p_academic_year
    )
    -- Apply optional filters
    AND (p_year_group IS NULL OR s.year_group = p_year_group)
    AND (p_group IS NULL OR s.group = p_group)  
    AND (p_faculty IS NULL OR s.faculty = p_faculty);
END;
$$ LANGUAGE plpgsql;

-- Test it for Whitchurch
SELECT COUNT(*) FROM get_students_for_academic_year(
    '1a327b33-d924-453c-803e-82671f94a242'::UUID,
    '2024/2025'
); -- Should return ~440

SELECT COUNT(*) FROM get_students_for_academic_year(
    '1a327b33-d924-453c-803e-82671f94a242'::UUID,
    '2025/2026'
); -- Should return 207
'''

# The actual patch for app.py
print("""
PATCH FOR app.py (around line 5645-5650):

FIND THIS:
-----------
        while True:
            # Build query with filters
            query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)
            
            # IMPORTANT: Filter by academic_year if provided
            if academic_year:
                query = query.eq('academic_year', academic_year)

REPLACE WITH:
-------------
        while True:
            # Build query with filters
            query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)
            
            # DON'T filter by academic_year here - we'll filter by VESPA data below

Then after the loop (around line 5680), ADD:
---------------------------------------------
        # Filter by who has VESPA data for the selected academic year
        if academic_year:
            students_with_vespa = []
            
            # Check in batches who has VESPA data for this year
            for i in range(0, len(student_ids), 50):
                batch_ids = student_ids[i:i+50]
                
                # Check which students have VESPA data for the selected year
                vespa_check = supabase_client.table('vespa_scores')\
                    .select('student_id')\
                    .in_('student_id', batch_ids)\
                    .eq('academic_year', academic_year)\
                    .limit(1000)\
                    .execute()
                
                students_with_vespa_ids = set(v['student_id'] for v in vespa_check.data)
                
                # Keep only students who have VESPA data
                students_with_vespa.extend([sid for sid in batch_ids if sid in students_with_vespa_ids])
            
            student_ids = students_with_vespa
            app.logger.info(f"After academic year filter: {len(student_ids)} students have data for {academic_year}")
""")
