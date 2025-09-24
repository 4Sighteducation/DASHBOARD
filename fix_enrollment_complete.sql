-- COMPLETE FIX: Create enrollments for ALL students with VESPA data
-- This includes graduated/deleted students

-- Step 1: Check the actual VESPA data distribution
-- This shows the TRUE number of students with data for each year
WITH vespa_summary AS (
    SELECT 
        vs.academic_year,
        COUNT(DISTINCT vs.student_id) as unique_students,
        COUNT(DISTINCT vs.student_email) as unique_emails,
        COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN vs.student_id END) as students_still_exist,
        COUNT(DISTINCT CASE WHEN s.id IS NULL THEN vs.student_id END) as students_deleted
    FROM vespa_scores vs
    LEFT JOIN students s ON vs.student_id = s.id
    WHERE vs.academic_year IN ('2024/2025', '2025/2026')
    -- Focus on Whitchurch emails
    AND (vs.student_email LIKE '%@whitchurchhs.wales' 
         OR vs.student_id IN (
            SELECT id FROM students 
            WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
         ))
    GROUP BY vs.academic_year
)
SELECT * FROM vespa_summary ORDER BY academic_year;

-- Step 2: Clear existing incomplete enrollments
DELETE FROM student_enrollments
WHERE student_id IN (
    SELECT DISTINCT student_id 
    FROM vespa_scores 
    WHERE student_email LIKE '%@whitchurchhs.wales'
);

-- Step 3: Create enrollments for ALL students with VESPA data
-- Including those who no longer exist in the students table
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
    COALESCE(s.knack_id, 'HISTORICAL_' || SUBSTRING(vs.student_id::TEXT, 1, 8)),
    CASE 
        WHEN vs.academic_year = '2024/2025' THEN
            CASE 
                -- If student still exists and is in Year 13 now, they were Year 12 last year
                WHEN s.year_group = 'Year 13' THEN 'Year 12'
                -- If student doesn't exist, they graduated (were Year 13)
                WHEN s.id IS NULL THEN 'Year 13 (Graduated)'
                ELSE COALESCE(s.year_group, 'Unknown')
            END
        WHEN vs.academic_year = '2025/2026' THEN
            COALESCE(s.year_group, 'Year 13')
        ELSE COALESCE(s.year_group, 'Unknown')
    END as year_group,
    s.course,
    s.faculty,
    CASE 
        WHEN vs.academic_year = '2025/2026' AND s.id IS NOT NULL THEN 'active'
        WHEN vs.academic_year = '2024/2025' AND s.id IS NULL THEN 'graduated'
        ELSE 'completed'
    END as enrollment_status
FROM vespa_scores vs
LEFT JOIN students s ON vs.student_id = s.id
WHERE vs.academic_year IN ('2024/2025', '2025/2026')
AND (
    vs.student_email LIKE '%@whitchurchhs.wales'
    OR vs.student_id IN (
        SELECT id FROM students 
        WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    )
)
ON CONFLICT (student_id, academic_year) 
DO UPDATE SET
    year_group = EXCLUDED.year_group,
    enrollment_status = EXCLUDED.enrollment_status,
    updated_at = NOW();

-- Step 4: Verify the complete fix
SELECT 
    'After Fix' as status,
    academic_year,
    enrollment_status,
    COUNT(DISTINCT student_id) as student_count
FROM student_enrollments
WHERE student_id IN (
    SELECT DISTINCT student_id 
    FROM vespa_scores 
    WHERE student_email LIKE '%@whitchurchhs.wales'
)
GROUP BY academic_year, enrollment_status
ORDER BY academic_year, enrollment_status;

-- Step 5: Create a function to get the correct counts
-- This will work even with deleted students
CREATE OR REPLACE FUNCTION get_whitchurch_complete_counts()
RETURNS TABLE (
    academic_year VARCHAR,
    total_students BIGINT,
    active_students BIGINT,
    graduated_students BIGINT,
    has_vespa_data BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        se.academic_year,
        COUNT(DISTINCT se.student_id) as total_students,
        COUNT(DISTINCT CASE WHEN se.enrollment_status = 'active' THEN se.student_id END) as active_students,
        COUNT(DISTINCT CASE WHEN se.enrollment_status = 'graduated' THEN se.student_id END) as graduated_students,
        COUNT(DISTINCT vs.student_id) as has_vespa_data
    FROM student_enrollments se
    LEFT JOIN vespa_scores vs ON se.student_id = vs.student_id AND se.academic_year = vs.academic_year
    WHERE se.student_id IN (
        SELECT DISTINCT student_id 
        FROM vespa_scores 
        WHERE student_email LIKE '%@whitchurchhs.wales'
    )
    GROUP BY se.academic_year
    ORDER BY se.academic_year;
END;
$$ LANGUAGE plpgsql;

-- Run the verification
SELECT * FROM get_whitchurch_complete_counts();

-- Step 6: The REAL issue - we need to find ALL Whitchurch VESPA scores
-- Let's check by email pattern and see what we get
SELECT 
    'VESPA Data Reality Check' as check_type,
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as unique_student_ids,
    COUNT(DISTINCT vs.student_email) as unique_emails,
    COUNT(DISTINCT vs.cycle) as cycles,
    MIN(vs.created_at) as earliest_score,
    MAX(vs.created_at) as latest_score
FROM vespa_scores vs
WHERE vs.student_email LIKE '%@whitchurchhs.wales'
GROUP BY vs.academic_year
ORDER BY vs.academic_year;

-- If the above shows the correct counts (~440 for 2024/2025), 
-- then the enrollment creation worked correctly


