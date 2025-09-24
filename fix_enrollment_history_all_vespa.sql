-- Fix: Create enrollment history for ALL students who have VESPA data
-- Including those who were deleted from the students table

-- First, check how many unique students have VESPA data for each year
SELECT 
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as students_with_vespa,
    COUNT(DISTINCT s.id) as students_still_exist
FROM vespa_scores vs
LEFT JOIN students s ON vs.student_id = s.id
WHERE vs.student_id IN (
    SELECT DISTINCT student_id 
    FROM vespa_scores 
    WHERE student_id IN (
        SELECT id FROM students WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
        UNION
        SELECT student_id FROM vespa_scores WHERE academic_year IN ('2024/2025', '2025/2026')
    )
)
GROUP BY vs.academic_year
ORDER BY vs.academic_year;

-- The problem: We need to recreate student records for those who were deleted
-- Let's identify orphaned VESPA scores (scores without matching students)
WITH orphaned_vespa AS (
    SELECT DISTINCT
        vs.student_id,
        vs.academic_year,
        vs.student_name,
        vs.student_email
    FROM vespa_scores vs
    LEFT JOIN students s ON vs.student_id = s.id
    WHERE s.id IS NULL  -- Student doesn't exist
    AND vs.academic_year = '2024/2025'  -- From last year
)
SELECT 
    academic_year,
    COUNT(DISTINCT student_id) as orphaned_students
FROM orphaned_vespa
GROUP BY academic_year;

-- SOLUTION: Create enrollment records from VESPA data directly
-- This captures ALL historical data, even for deleted students

-- First, clear existing incomplete enrollments for Whitchurch
DELETE FROM student_enrollments
WHERE student_id IN (
    SELECT id FROM students 
    WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
);

-- Now create enrollments from VESPA scores (not dependent on students table)
INSERT INTO student_enrollments (
    student_id,
    academic_year,
    knack_id,
    year_group,
    course,
    faculty,
    enrollment_status
)
SELECT DISTINCT
    vs.student_id,
    vs.academic_year,
    COALESCE(s.knack_id, 'DELETED_' || vs.student_id::TEXT),  -- Mark deleted students
    CASE 
        WHEN vs.academic_year = '2024/2025' THEN 
            CASE 
                WHEN s.id IS NULL THEN 'Year 13 (Graduated)'  -- Deleted students were Year 13s
                ELSE COALESCE(s.year_group, 'Year 12')  -- Existing students were Year 12s
            END
        WHEN vs.academic_year = '2025/2026' THEN 
            COALESCE(s.year_group, 'Year 13')
        ELSE s.year_group
    END,
    s.course,
    s.faculty,
    CASE 
        WHEN vs.academic_year = '2025/2026' THEN 'active'
        WHEN vs.academic_year = '2024/2025' AND s.id IS NULL THEN 'graduated'
        ELSE 'completed'
    END
FROM vespa_scores vs
LEFT JOIN students s ON vs.student_id = s.id  -- LEFT JOIN to include orphaned records
WHERE vs.student_id IN (
    -- All students who ever belonged to Whitchurch
    SELECT DISTINCT student_id 
    FROM vespa_scores 
    WHERE student_id IN (
        SELECT id FROM students WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    )
    OR student_email IN (
        -- Include graduated students by matching emails from current students
        SELECT email FROM students WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    )
    OR student_name LIKE '%Whitchurch%'  -- Fallback for any Whitchurch students
)
ON CONFLICT (student_id, academic_year) DO UPDATE SET
    enrollment_status = EXCLUDED.enrollment_status,
    year_group = EXCLUDED.year_group,
    updated_at = NOW();

-- Verify the fix
SELECT 
    academic_year,
    enrollment_status,
    COUNT(DISTINCT student_id) as student_count
FROM student_enrollments
WHERE student_id IN (
    SELECT DISTINCT student_id 
    FROM vespa_scores 
    WHERE academic_year IN ('2024/2025', '2025/2026')
)
GROUP BY academic_year, enrollment_status
ORDER BY academic_year, enrollment_status;

-- The real issue might be simpler - let's check the Whitchurch establishment ID
-- in the VESPA scores directly
SELECT 
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as total_vespa_students
FROM vespa_scores vs
WHERE EXISTS (
    SELECT 1 FROM students s 
    WHERE s.id = vs.student_id 
    AND s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
)
GROUP BY vs.academic_year
ORDER BY vs.academic_year;

-- Alternative approach: Use VESPA scores as source of truth
-- and create enrollments for ALL students with VESPA data for Whitchurch
WITH whitchurch_vespa AS (
    -- Find all VESPA scores for Whitchurch students
    SELECT DISTINCT
        vs.student_id,
        vs.academic_year,
        vs.student_name,
        vs.student_email
    FROM vespa_scores vs
    WHERE vs.student_id IN (
        -- Any student currently or previously at Whitchurch
        SELECT id FROM students WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
        UNION
        -- Include students from the CSV list (current Year 13s)
        SELECT s.id FROM students s
        WHERE s.email IN (
            -- List from vesparesults (36).csv
            'isabelle.arrowsmith@whitchurchhs.wales',
            'ruby.ashley@whitchurchhs.wales',
            'leila.baker@whitchurchhs.wales'
            -- ... (would include all 207 emails)
        )
    )
)
SELECT 
    academic_year,
    COUNT(DISTINCT student_id) as student_count
FROM whitchurch_vespa
GROUP BY academic_year
ORDER BY academic_year;

-- Final comprehensive fix: Get ALL Whitchurch VESPA data
-- This will show us the TRUE count of students with data
SELECT 
    'Summary' as check_type,
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as vespa_score_count,
    COUNT(DISTINCT vs.student_email) as unique_emails,
    COUNT(*) as total_scores
FROM vespa_scores vs
WHERE vs.academic_year IN ('2024/2025', '2025/2026')
AND (
    -- Current Whitchurch students
    vs.student_id IN (
        SELECT id FROM students 
        WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    )
    OR 
    -- Historical Whitchurch students (by email pattern)
    vs.student_email LIKE '%@whitchurchhs.wales'
)
GROUP BY vs.academic_year
ORDER BY vs.academic_year;
