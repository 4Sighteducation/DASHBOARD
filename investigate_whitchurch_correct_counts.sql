-- INVESTIGATE WHITCHURCH - CORRECT UNDERSTANDING
-- 2024/2025: Should have ~440 students (Yr12 + Yr13)
-- 2025/2026: Should have ~207 students (ONLY current Yr13s)

-- ============================================================================
-- STEP 1: Check what's actually in the database
-- ============================================================================

-- Total students currently in database for Whitchurch
SELECT 
    'Total Students in DB' as check,
    COUNT(*) as count,
    COUNT(DISTINCT email) as unique_emails
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242';

-- Students by Year Group
SELECT 
    'By Year Group' as check,
    s.year_group,
    COUNT(*) as count
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY s.year_group
ORDER BY s.year_group;

-- Students by academic_year field
SELECT 
    'By Academic Year Field' as check,
    s.academic_year,
    COUNT(*) as count
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY s.academic_year;

-- ============================================================================
-- STEP 2: Check VESPA data distribution
-- ============================================================================

-- How many unique students have VESPA data for each year?
WITH vespa_summary AS (
    SELECT 
        vs.academic_year,
        vs.student_id,
        s.email,
        s.year_group,
        s.name
    FROM vespa_scores vs
    INNER JOIN students s ON vs.student_id = s.id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
)
SELECT 
    academic_year,
    COUNT(DISTINCT student_id) as unique_students,
    COUNT(DISTINCT email) as unique_emails,
    STRING_AGG(DISTINCT year_group, ', ' ORDER BY year_group) as year_groups
FROM vespa_summary
GROUP BY academic_year
ORDER BY academic_year;

-- ============================================================================
-- STEP 3: Find students with data in BOTH years (continuing students)
-- ============================================================================

WITH student_years AS (
    SELECT 
        s.id,
        s.email,
        s.name,
        s.year_group as current_year_group,
        ARRAY_AGG(DISTINCT vs.academic_year ORDER BY vs.academic_year) as years_with_data
    FROM students s
    LEFT JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    GROUP BY s.id, s.email, s.name, s.year_group
)
SELECT 
    'Student Data Pattern' as category,
    CASE 
        WHEN '2024/2025' = ANY(years_with_data) AND '2025/2026' = ANY(years_with_data) THEN 'Both Years (Continuing)'
        WHEN '2024/2025' = ANY(years_with_data) AND NOT '2025/2026' = ANY(years_with_data) THEN '2024/2025 Only (Graduated?)'
        WHEN '2025/2026' = ANY(years_with_data) AND NOT '2024/2025' = ANY(years_with_data) THEN '2025/2026 Only (New?)'
        WHEN years_with_data IS NULL OR array_length(years_with_data, 1) = 0 THEN 'No VESPA Data'
        ELSE 'Other'
    END as pattern,
    COUNT(*) as student_count,
    STRING_AGG(DISTINCT current_year_group, ', ' ORDER BY current_year_group) as year_groups
FROM student_years
GROUP BY pattern
ORDER BY pattern;

-- ============================================================================
-- STEP 4: Sample of continuing students (should be ~207 Year 13s)
-- ============================================================================

-- Students who have data in BOTH years (these should be the continuing Year 13s)
WITH continuing_students AS (
    SELECT 
        s.id,
        s.email,
        s.name,
        s.year_group,
        s.knack_id,
        ARRAY_AGG(DISTINCT vs.academic_year ORDER BY vs.academic_year) as years
    FROM students s
    INNER JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    GROUP BY s.id, s.email, s.name, s.year_group, s.knack_id
    HAVING COUNT(DISTINCT vs.academic_year) > 1
)
SELECT 
    'Continuing Students' as category,
    COUNT(*) as total_count,
    COUNT(CASE WHEN year_group = 'Year 13' THEN 1 END) as year_13_count,
    COUNT(CASE WHEN year_group = 'Year 12' THEN 1 END) as year_12_count,
    COUNT(CASE WHEN year_group NOT IN ('Year 12', 'Year 13') OR year_group IS NULL THEN 1 END) as other_count
FROM continuing_students;

-- Sample of continuing students
SELECT 
    'Sample Continuing Student' as type,
    s.name,
    s.email,
    s.year_group,
    ARRAY_AGG(DISTINCT vs.academic_year ORDER BY vs.academic_year) as years_with_data
FROM students s
INNER JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY s.id, s.name, s.email, s.year_group
HAVING COUNT(DISTINCT vs.academic_year) > 1
LIMIT 5;

-- ============================================================================
-- STEP 5: The Real Issue - Check Knack IDs
-- ============================================================================

-- Are we seeing duplicate students with different Knack IDs?
WITH email_counts AS (
    SELECT 
        LOWER(s.email) as email,
        COUNT(DISTINCT s.id) as record_count,
        COUNT(DISTINCT s.knack_id) as knack_id_count,
        ARRAY_AGG(DISTINCT s.knack_id ORDER BY s.knack_id) as knack_ids,
        ARRAY_AGG(DISTINCT s.year_group ORDER BY s.year_group) as year_groups
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    GROUP BY LOWER(s.email)
    HAVING COUNT(DISTINCT s.id) > 1 OR COUNT(DISTINCT s.knack_id) > 1
)
SELECT 
    'Duplicate Check' as check,
    COUNT(*) as emails_with_duplicates,
    SUM(record_count) as total_duplicate_records
FROM email_counts;

-- ============================================================================
-- THE ANSWER: What the counts SHOULD be
-- ============================================================================

SELECT 
    '2024/2025 Should Show' as year,
    '~440 students' as expected,
    'All Year 12s + Year 13s from last year' as description
UNION ALL
SELECT 
    '2025/2026 Should Show' as year,
    '~207 students' as expected,
    'ONLY current Year 13s (last years Year 12s)' as description;

-- ============================================================================
-- THE FIX: Count based on VESPA data presence
-- ============================================================================

-- For 2024/2025: All students who have 2024/2025 VESPA data
SELECT 
    '2024/2025 Actual' as year,
    COUNT(DISTINCT s.id) as student_count,
    'Students with 2024/2025 VESPA data' as basis
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2024/2025'
);

-- For 2025/2026: Students who ONLY have 2025/2026 data OR have both
-- But wait - if there are only 207 in Knack now, we need to understand what's happening
SELECT 
    '2025/2026 Actual' as year,
    COUNT(DISTINCT s.id) as student_count,
    'Students with 2025/2026 VESPA data' as basis
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2025/2026'
);
