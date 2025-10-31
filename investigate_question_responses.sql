-- =====================================================
-- DEEP DIVE INVESTIGATION - ASHLYNS & COFFS HARBOUR
-- =====================================================
-- Run this in Supabase SQL Editor to understand the data

-- =====================================================
-- PART 1: ESTABLISHMENT IDs
-- =====================================================

SELECT 
    id,
    name,
    is_australian,
    use_standard_year
FROM establishments
WHERE name ILIKE '%Ashlyns%' OR name ILIKE '%Coffs%'
ORDER BY name;

-- Copy the IDs from above and use them below
-- Ashlyns ID: 308cc905-c1c9-4b71-b976-dfe4d8c7d7ec
-- Coffs Harbour ID: caa446f7-c1ad-47cd-acf1-771cacf10d3a


-- =====================================================
-- PART 2: ASHLYNS SCHOOL - OVERVIEW
-- =====================================================

-- 2.1: Students by Academic Year
SELECT 
    academic_year,
    COUNT(*) as student_count,
    COUNT(DISTINCT email) as unique_emails,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM students
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
GROUP BY academic_year
ORDER BY academic_year DESC;


-- 2.2: VESPA Scores Coverage
SELECT 
    vs.academic_year,
    vs.cycle,
    COUNT(DISTINCT vs.student_id) as students_with_vespa,
    COUNT(*) as vespa_records,
    MIN(vs.completion_date) as earliest_completion,
    MAX(vs.completion_date) as latest_completion
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
GROUP BY vs.academic_year, vs.cycle
ORDER BY vs.academic_year DESC, vs.cycle;


-- 2.3: Question Responses Coverage
SELECT 
    qr.academic_year,
    qr.cycle,
    COUNT(DISTINCT qr.student_id) as students_with_responses,
    COUNT(*) as total_responses,
    COUNT(*) / 32 as approx_complete_students,
    MIN(qr.created_at) as earliest_response,
    MAX(qr.created_at) as latest_response
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
GROUP BY qr.academic_year, qr.cycle
ORDER BY qr.academic_year DESC, qr.cycle;


-- 2.4: CRITICAL - Students with VESPA but NO Question Responses
WITH vespa_students AS (
    SELECT DISTINCT 
        vs.student_id,
        vs.academic_year,
        vs.cycle
    FROM vespa_scores vs
    JOIN students s ON vs.student_id = s.id
    WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
        AND vs.academic_year = '2025/2026'
        AND vs.cycle = 1
),
response_students AS (
    SELECT DISTINCT 
        qr.student_id,
        qr.academic_year,
        qr.cycle
    FROM question_responses qr
    JOIN students s ON qr.student_id = s.id
    WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
        AND qr.academic_year = '2025/2026'
        AND qr.cycle = 1
)
SELECT 
    'Students with VESPA but NO responses' as category,
    COUNT(*) as count
FROM vespa_students v
LEFT JOIN response_students r ON v.student_id = r.student_id
WHERE r.student_id IS NULL;


-- 2.5: Sample of Missing Students (with details)
WITH vespa_students AS (
    SELECT DISTINCT 
        vs.student_id,
        s.email,
        s.name,
        s.knack_id,
        vs.completion_date as vespa_date
    FROM vespa_scores vs
    JOIN students s ON vs.student_id = s.id
    WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
        AND vs.academic_year = '2025/2026'
        AND vs.cycle = 1
),
response_students AS (
    SELECT DISTINCT 
        qr.student_id
    FROM question_responses qr
    WHERE qr.academic_year = '2025/2026'
        AND qr.cycle = 1
)
SELECT 
    v.email,
    v.name,
    v.knack_id as object_10_knack_id,
    v.vespa_date,
    CASE 
        WHEN r.student_id IS NOT NULL THEN 'HAS RESPONSES'
        ELSE 'MISSING RESPONSES'
    END as status
FROM vespa_students v
LEFT JOIN response_students r ON v.student_id = r.student_id
WHERE r.student_id IS NULL
ORDER BY v.email
LIMIT 20;


-- 2.6: Mismatch Analysis - Different Academic Years
SELECT 
    s.email,
    s.academic_year as student_year,
    vs.academic_year as vespa_year,
    qr.academic_year as response_year,
    vs.cycle
FROM students s
LEFT JOIN vespa_scores vs ON s.id = vs.student_id AND vs.cycle = 1
LEFT JOIN (
    SELECT student_id, academic_year, cycle
    FROM question_responses
    WHERE cycle = 1
    GROUP BY student_id, academic_year, cycle
) qr ON s.id = qr.student_id AND qr.cycle = 1
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND (
        s.academic_year != vs.academic_year 
        OR s.academic_year != qr.academic_year
        OR vs.academic_year != qr.academic_year
    )
ORDER BY s.email
LIMIT 20;


-- =====================================================
-- PART 3: COFFS HARBOUR - OVERVIEW
-- =====================================================

-- 3.1: Students by Academic Year
SELECT 
    academic_year,
    COUNT(*) as student_count,
    COUNT(DISTINCT email) as unique_emails,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM students
WHERE establishment_id = 'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
GROUP BY academic_year
ORDER BY academic_year DESC;


-- 3.2: VESPA Scores Coverage
SELECT 
    vs.academic_year,
    vs.cycle,
    COUNT(DISTINCT vs.student_id) as students_with_vespa,
    COUNT(*) as vespa_records,
    MIN(vs.completion_date) as earliest_completion,
    MAX(vs.completion_date) as latest_completion
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = 'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
GROUP BY vs.academic_year, vs.cycle
ORDER BY vs.academic_year DESC, vs.cycle;


-- 3.3: Question Responses Coverage
SELECT 
    qr.academic_year,
    qr.cycle,
    COUNT(DISTINCT qr.student_id) as students_with_responses,
    COUNT(*) as total_responses,
    COUNT(*) / 32 as approx_complete_students,
    MIN(qr.created_at) as earliest_response,
    MAX(qr.created_at) as latest_response
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = 'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
GROUP BY qr.academic_year, qr.cycle
ORDER BY qr.academic_year DESC, qr.cycle;


-- 3.4: Coffs Harbour - Missing Responses Analysis
WITH vespa_students AS (
    SELECT DISTINCT 
        vs.student_id,
        vs.academic_year,
        vs.cycle
    FROM vespa_scores vs
    JOIN students s ON vs.student_id = s.id
    WHERE s.establishment_id = 'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
),
response_students AS (
    SELECT DISTINCT 
        qr.student_id,
        qr.academic_year,
        qr.cycle
    FROM question_responses qr
    JOIN students s ON qr.student_id = s.id
    WHERE s.establishment_id = 'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
)
SELECT 
    v.academic_year,
    v.cycle,
    COUNT(*) as students_with_vespa,
    COUNT(r.student_id) as students_with_responses,
    COUNT(*) - COUNT(r.student_id) as missing_responses
FROM vespa_students v
LEFT JOIN response_students r 
    ON v.student_id = r.student_id 
    AND v.cycle = r.cycle
    AND v.academic_year = r.academic_year
GROUP BY v.academic_year, v.cycle
ORDER BY v.academic_year DESC, v.cycle;


-- =====================================================
-- PART 4: GLOBAL PATTERNS
-- =====================================================

-- 4.1: Question Response Distribution by Created Date
SELECT 
    DATE_TRUNC('month', qr.created_at) as month,
    qr.academic_year,
    COUNT(DISTINCT qr.student_id) as unique_students,
    COUNT(*) as total_responses
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id IN (
    '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec',  -- Ashlyns
    'caa446f7-c1ad-47cd-acf1-771cacf10d3a'   -- Coffs Harbour
)
GROUP BY DATE_TRUNC('month', qr.created_at), qr.academic_year
ORDER BY month DESC
LIMIT 50;


-- 4.2: Students with NULL academic_year
SELECT 
    e.name as school,
    COUNT(*) as students_with_null_year
FROM students s
JOIN establishments e ON s.establishment_id = e.id
WHERE s.academic_year IS NULL
    AND s.establishment_id IN (
        '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec',
        'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
    )
GROUP BY e.name;


-- 4.3: VESPA vs Question Response Alignment
SELECT 
    e.name as school,
    vs.academic_year,
    vs.cycle,
    COUNT(DISTINCT vs.student_id) as students_with_vespa,
    AVG(
        CASE 
            WHEN qr.student_id IS NOT NULL THEN 1 
            ELSE 0 
        END
    ) * 100 as pct_with_responses
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
LEFT JOIN (
    SELECT DISTINCT student_id, cycle, academic_year
    FROM question_responses
) qr ON vs.student_id = qr.student_id 
    AND vs.cycle = qr.cycle
    AND vs.academic_year = qr.academic_year
WHERE s.establishment_id IN (
    '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec',
    'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
)
GROUP BY e.name, vs.academic_year, vs.cycle
ORDER BY e.name, vs.academic_year DESC, vs.cycle;


-- =====================================================
-- PART 5: QUESTION RESPONSE QUALITY CHECK
-- =====================================================

-- 5.1: Incomplete Questionnaires (students with < 32 responses)
SELECT 
    s.email,
    s.academic_year,
    qr.cycle,
    COUNT(*) as response_count,
    CASE 
        WHEN COUNT(*) = 32 THEN 'Complete'
        WHEN COUNT(*) > 0 AND COUNT(*) < 32 THEN 'Partial'
        ELSE 'None'
    END as status
FROM students s
LEFT JOIN question_responses qr ON s.id = qr.student_id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND s.academic_year = '2025/2026'
    AND (qr.cycle = 1 OR qr.cycle IS NULL)
GROUP BY s.email, s.academic_year, qr.cycle
HAVING COUNT(*) != 32
ORDER BY response_count DESC
LIMIT 30;


-- 5.2: Response Count Distribution
SELECT 
    e.name as school,
    qr.academic_year,
    qr.cycle,
    COUNT(*) as response_count,
    COUNT(*) / 32 as complete_students,
    COUNT(*) % 32 as partial_responses
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
WHERE s.establishment_id IN (
    '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec',
    'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
)
GROUP BY e.name, qr.academic_year, qr.cycle
ORDER BY e.name, qr.academic_year DESC, qr.cycle;


-- =====================================================
-- PART 6: TEMPORAL ANALYSIS
-- =====================================================

-- 6.1: When were records created?
SELECT 
    'Ashlyns' as school,
    '2025/2026' as academic_year,
    'Students' as record_type,
    COUNT(*) as count,
    MIN(created_at) as earliest,
    MAX(created_at) as latest,
    DATE_TRUNC('day', MAX(created_at)) - DATE_TRUNC('day', MIN(created_at)) as date_range
FROM students
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND academic_year = '2025/2026'

UNION ALL

SELECT 
    'Ashlyns',
    '2025/2026',
    'VESPA Scores',
    COUNT(*),
    MIN(created_at),
    MAX(created_at),
    DATE_TRUNC('day', MAX(created_at)) - DATE_TRUNC('day', MIN(created_at))
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND vs.academic_year = '2025/2026'
    AND vs.cycle = 1

UNION ALL

SELECT 
    'Ashlyns',
    '2025/2026',
    'Question Responses',
    COUNT(*),
    MIN(created_at),
    MAX(created_at),
    DATE_TRUNC('day', MAX(created_at)) - DATE_TRUNC('day', MIN(created_at))
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND qr.academic_year = '2025/2026'
    AND qr.cycle = 1;


-- =====================================================
-- PART 7: DIAGNOSTIC - FIND THE GAP
-- =====================================================

-- 7.1: List specific students missing responses with their Knack IDs
SELECT 
    s.email,
    s.name,
    s.knack_id as object_10_id,
    s.academic_year,
    vs.completion_date,
    vs.overall as vespa_overall_score,
    COALESCE(qr_count.response_count, 0) as question_response_count
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
LEFT JOIN (
    SELECT 
        student_id,
        COUNT(*) as response_count
    FROM question_responses
    WHERE cycle = 1 AND academic_year = '2025/2026'
    GROUP BY student_id
) qr_count ON s.id = qr_count.student_id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND s.academic_year = '2025/2026'
    AND vs.cycle = 1
    AND vs.academic_year = '2025/2026'
    AND COALESCE(qr_count.response_count, 0) = 0
ORDER BY s.email
LIMIT 50;


-- =====================================================
-- PART 8: RECENT DATA CHANGES
-- =====================================================

-- 8.1: What changed in the last 7 days?
SELECT 
    DATE(created_at) as date,
    COUNT(*) as responses_created,
    COUNT(DISTINCT student_id) as unique_students
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND qr.created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;


-- 8.2: Last sync impact
SELECT 
    DATE(created_at) as date,
    academic_year,
    cycle,
    COUNT(*) as responses,
    COUNT(DISTINCT student_id) as students
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND qr.created_at >= '2025-10-30 00:00:00'
GROUP BY DATE(created_at), academic_year, cycle
ORDER BY date DESC, academic_year DESC, cycle;


-- =====================================================
-- PART 9: QUICK DIAGNOSTIC FOR ANY SCHOOL
-- =====================================================

-- 9.1: Replace with any establishment ID to check health
-- Just change the UUID below
WITH target_school AS (
    SELECT '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec' as est_id
)
SELECT 
    'Students' as metric,
    academic_year,
    COUNT(*) as count
FROM students s, target_school t
WHERE s.establishment_id = t.est_id
GROUP BY academic_year

UNION ALL

SELECT 
    'VESPA Scores' as metric,
    vs.academic_year,
    COUNT(*)
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id, target_school t
WHERE s.establishment_id = t.est_id
    AND vs.cycle = 1
GROUP BY vs.academic_year

UNION ALL

SELECT 
    'Question Responses' as metric,
    qr.academic_year,
    COUNT(*)
FROM question_responses qr
JOIN students s ON qr.student_id = s.id, target_school t
WHERE s.establishment_id = t.est_id
    AND qr.cycle = 1
GROUP BY qr.academic_year

ORDER BY metric, academic_year DESC;


-- =====================================================
-- PART 10: ASHLYNS COMPLETE SUMMARY (One Query)
-- =====================================================

-- This gives you everything at a glance
SELECT 
    'Total Students (All Years)' as metric,
    COUNT(*)::text as value,
    ''::text as academic_year
FROM students
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'

UNION ALL

SELECT 
    'Students in 2025/2026',
    COUNT(*)::text,
    '2025/2026'
FROM students
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND academic_year = '2025/2026'

UNION ALL

SELECT 
    'VESPA Scores (Cycle 1, 2025/2026)',
    COUNT(DISTINCT student_id)::text,
    '2025/2026'
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND vs.academic_year = '2025/2026'
    AND vs.cycle = 1

UNION ALL

SELECT 
    'Question Responses (Cycle 1, 2025/2026)',
    COUNT(*)::text,
    '2025/2026'
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND qr.academic_year = '2025/2026'
    AND qr.cycle = 1

UNION ALL

SELECT 
    'Students with Complete Responses',
    (COUNT(*) / 32)::text,
    '2025/2026'
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
    AND qr.academic_year = '2025/2026'
    AND qr.cycle = 1

ORDER BY metric;


-- =====================================================
-- PART 11: CHECK IF DATA EXISTS FOR CURRENT FILTERS
-- =====================================================

-- Run this to see what academic years are available
SELECT DISTINCT academic_year
FROM students
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
ORDER BY academic_year DESC;

-- Check if question_statistics table has data
SELECT 
    academic_year,
    cycle,
    COUNT(*) as stat_records,
    MAX(calculated_at) as last_calculated
FROM question_statistics
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
GROUP BY academic_year, cycle
ORDER BY academic_year DESC, cycle;


-- =====================================================
-- USAGE NOTES
-- =====================================================

/*
QUICK START:
1. Run Part 1 to get establishment IDs
2. Run Part 2.1, 2.2, 2.3 to see overview
3. Run Part 10 for quick summary

INTERPRETING RESULTS:
- Students with VESPA but no responses = Normal (not everyone completes questionnaire)
- Response count should be multiple of 32 (one complete questionnaire = 32 responses)
- Academic year mismatches (Query 2.6) should return 0 rows
- Coverage of 70-90% for question responses is typical

KEY METRICS:
- VESPA coverage should be 90%+
- Question response coverage typically 70-85%
- Complete response sets (÷32) should match student count

TROUBLESHOOTING:
- If coverage suddenly drops, check last sync report
- If academic years don't match, check sync logic
- If data missing for current year, check date filters
*/

