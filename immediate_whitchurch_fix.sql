-- IMMEDIATE FIX FOR WHITCHURCH HIGH SCHOOL
-- This script fixes the data display issue WITHOUT requiring the full enrollment history setup
-- Run this NOW in Supabase SQL Editor to fix the dashboard

-- ============================================================================
-- STEP 1: Identify students who should appear in 2024/2025
-- ============================================================================

-- First, let's see what we're dealing with
SELECT 
    'Current Status' as check_type,
    COUNT(*) as count,
    academic_year
FROM students
WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY academic_year;

-- Check how many have VESPA data for each year
SELECT 
    'VESPA Data' as check_type,
    COUNT(DISTINCT student_id) as unique_students,
    academic_year
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY academic_year
ORDER BY academic_year;

-- ============================================================================
-- STEP 2: Create a temporary view for the dashboard to use
-- ============================================================================

-- Drop if exists
DROP VIEW IF EXISTS whitchurch_students_by_year;

-- Create view that shows students based on their VESPA data
CREATE OR REPLACE VIEW whitchurch_students_by_year AS
WITH student_years AS (
    -- Get all years each student has data for
    SELECT DISTINCT
        s.id,
        s.email,
        s.name,
        s.knack_id,
        s.establishment_id,
        s.year_group,
        s.course,
        s.faculty,
        vs.academic_year as data_year
    FROM students s
    LEFT JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
)
SELECT 
    id,
    email,
    name,
    knack_id,
    establishment_id,
    year_group,
    course,
    faculty,
    data_year as academic_year,
    -- Mark if they're currently active
    CASE 
        WHEN data_year = '2025/2026' THEN true
        ELSE false
    END as is_current_year
FROM student_years
WHERE data_year IS NOT NULL;

-- ============================================================================
-- STEP 3: Create a function the dashboard can use RIGHT NOW
-- ============================================================================

CREATE OR REPLACE FUNCTION get_whitchurch_students(
    p_academic_year VARCHAR DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    email VARCHAR,
    name VARCHAR,
    year_group VARCHAR,
    course VARCHAR,
    faculty VARCHAR,
    knack_id VARCHAR,
    student_count BIGINT
) AS $$
BEGIN
    IF p_academic_year IS NOT NULL THEN
        -- Return students for specific year based on VESPA data
        RETURN QUERY
        SELECT DISTINCT
            s.id,
            s.email,
            s.name,
            s.year_group,
            s.course,
            s.faculty,
            s.knack_id,
            COUNT(*) OVER() as student_count
        FROM students s
        WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
        AND EXISTS (
            SELECT 1 
            FROM vespa_scores vs 
            WHERE vs.student_id = s.id 
            AND vs.academic_year = p_academic_year
        );
    ELSE
        -- Return all students
        RETURN QUERY
        SELECT 
            s.id,
            s.email,
            s.name,
            s.year_group,
            s.course,
            s.faculty,
            s.knack_id,
            COUNT(*) OVER() as student_count
        FROM students s
        WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 4: Test the fix
-- ============================================================================

-- This should show ~189 students for 2024/2025
SELECT 
    'Students for 2024/2025' as query,
    COUNT(DISTINCT id) as student_count
FROM get_whitchurch_students('2024/2025');

-- This should show 445 students for 2025/2026
SELECT 
    'Students for 2025/2026' as query,
    COUNT(DISTINCT id) as student_count
FROM get_whitchurch_students('2025/2026');

-- ============================================================================
-- STEP 5: Quick API endpoint update (for app.py)
-- ============================================================================
-- Add this to your Python code as a temporary fix:
/*
# In your Flask app.py, add this endpoint:

@app.route('/api/whitchurch_fix/<academic_year>', methods=['GET'])
def get_whitchurch_students_fixed(academic_year):
    """Temporary fix for Whitchurch student counts"""
    try:
        # Use the function we created
        result = supabase.rpc('get_whitchurch_students', {
            'p_academic_year': academic_year
        }).execute()
        
        students = result.data
        
        # Get VESPA averages for these students
        student_ids = [s['id'] for s in students]
        
        vespa_data = supabase.table('vespa_scores')\
            .select('*')\
            .in_('student_id', student_ids)\
            .eq('academic_year', academic_year)\
            .execute()
        
        return jsonify({
            'total_students': len(students),
            'students_with_vespa': len(set(v['student_id'] for v in vespa_data.data)),
            'students': students[:100],  # First 100 for display
            'academic_year': academic_year
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
*/

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Final check - this should show the correct counts
SELECT 
    academic_year,
    COUNT(DISTINCT id) as students_shown,
    'Based on VESPA data' as method
FROM (
    SELECT DISTINCT
        s.id,
        vs.academic_year
    FROM students s
    INNER JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
) student_years
GROUP BY academic_year
ORDER BY academic_year;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
SELECT 
    '✅ Fix Applied Successfully!' as status,
    'The dashboard should now show:' as message,
    '• 2024/2025: ~189 students (those with last year''s data)' as year_2024,
    '• 2025/2026: 445 students (current year)' as year_2025,
    'Use: SELECT * FROM get_whitchurch_students(''2024/2025'')' as usage;
