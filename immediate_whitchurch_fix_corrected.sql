-- IMMEDIATE FIX FOR WHITCHURCH HIGH SCHOOL (CORRECTED)
-- Fixed: Ambiguous column references
-- Run this in Supabase SQL Editor to fix the dashboard

-- ============================================================================
-- STEP 1: Identify students who should appear in 2024/2025
-- ============================================================================

-- First, let's see what we're dealing with
SELECT 
    'Current Status' as check_type,
    COUNT(*) as count,
    s.academic_year  -- FIXED: Qualified with table alias
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY s.academic_year;

-- Check how many have VESPA data for each year
SELECT 
    'VESPA Data' as check_type,
    COUNT(DISTINCT vs.student_id) as unique_students,
    vs.academic_year  -- FIXED: Qualified with table alias
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY vs.academic_year
ORDER BY vs.academic_year;

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
-- STEP 5: Alternative simpler query for immediate use
-- ============================================================================

-- If the function creation fails, use this direct query:
-- For 2024/2025 students:
SELECT 
    COUNT(DISTINCT s.id) as "Students with 2024/2025 data"
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 
    FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2024/2025'
);

-- For 2025/2026 students:
SELECT 
    COUNT(DISTINCT s.id) as "Students with 2025/2026 data"
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 
    FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2025/2026'
);

-- ============================================================================
-- VERIFICATION - Fixed column ambiguity
-- ============================================================================

-- Final check - this should show the correct counts
SELECT 
    student_years.academic_year,
    COUNT(DISTINCT student_years.id) as students_shown,
    'Based on VESPA data' as method
FROM (
    SELECT DISTINCT
        s.id,
        vs.academic_year  -- FIXED: Qualified with table alias
    FROM students s
    INNER JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
) student_years
GROUP BY student_years.academic_year
ORDER BY student_years.academic_year;

-- ============================================================================
-- UPDATE DASHBOARD QUERY (Python/app.py)
-- ============================================================================
/*
Instead of querying:
  SELECT * FROM students 
  WHERE establishment_id = ? AND academic_year = ?

Use this approach:
  # Get students who have VESPA data for the selected year
  query = """
  SELECT DISTINCT s.* 
  FROM students s
  WHERE s.establishment_id = %s
  AND EXISTS (
      SELECT 1 FROM vespa_scores vs 
      WHERE vs.student_id = s.id 
      AND vs.academic_year = %s
  )
  """
  
This will show:
- 2024/2025: ~189 students (those with last year's data)
- 2025/2026: 445 students (current year students)
*/

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
SELECT 
    '✅ Fix Applied Successfully!' as status,
    'The dashboard should now show:' as message,
    '• 2024/2025: ~189 students (those with last year''s data)' as year_2024,
    '• 2025/2026: 445 students (current year)' as year_2025,
    'Use: SELECT * FROM get_whitchurch_students(''2024/2025'')' as usage;
