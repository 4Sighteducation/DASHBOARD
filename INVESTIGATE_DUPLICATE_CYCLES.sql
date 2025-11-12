-- ============================================================================
-- Investigate Duplicate Cycle Data for Penglais School
-- ============================================================================
-- Check if Cycle 1 data has been incorrectly duplicated to Cycles 2 & 3
-- ============================================================================

-- Step 1: Find Penglais School establishment_id
SELECT id, name, knack_id 
FROM establishments 
WHERE name ILIKE '%penglais%';

-- Step 2: Get a sample student from Penglais to check their cycles
-- Replace {establishment_id} with the ID from Step 1
SELECT 
    s.id,
    s.name,
    s.email,
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date,
    vs.academic_year
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'  -- Replace with actual ID
AND s.academic_year = '2025/2026'  -- Current year
ORDER BY s.name, vs.cycle;

-- Step 3: Check for suspicious duplicates (same scores across all cycles)
-- This query finds students where Cycle 1, 2, and 3 have IDENTICAL scores
WITH student_cycles AS (
    SELECT 
        s.id as student_id,
        s.name,
        s.email,
        vs.cycle,
        vs.vision,
        vs.effort,
        vs.systems,
        vs.practice,
        vs.attitude,
        vs.overall,
        vs.completion_date
    FROM students s
    JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '{establishment_id}'  -- Replace with actual ID
    AND vs.academic_year = '2025/2026'
),
cycle_comparison AS (
    SELECT 
        student_id,
        name,
        email,
        MAX(CASE WHEN cycle = 1 THEN vision END) as c1_vision,
        MAX(CASE WHEN cycle = 2 THEN vision END) as c2_vision,
        MAX(CASE WHEN cycle = 3 THEN vision END) as c3_vision,
        MAX(CASE WHEN cycle = 1 THEN overall END) as c1_overall,
        MAX(CASE WHEN cycle = 2 THEN overall END) as c2_overall,
        MAX(CASE WHEN cycle = 3 THEN overall END) as c3_overall,
        MAX(CASE WHEN cycle = 1 THEN completion_date END) as c1_date,
        MAX(CASE WHEN cycle = 2 THEN completion_date END) as c2_date,
        MAX(CASE WHEN cycle = 3 THEN completion_date END) as c3_date
    FROM student_cycles
    GROUP BY student_id, name, email
)
SELECT 
    name,
    email,
    c1_vision, c2_vision, c3_vision,
    c1_overall, c2_overall, c3_overall,
    c1_date, c2_date, c3_date,
    CASE 
        WHEN c1_vision = c2_vision AND c2_vision = c3_vision 
        AND c1_overall = c2_overall AND c2_overall = c3_overall
        THEN '⚠️ DUPLICATE - All cycles identical'
        WHEN c2_vision IS NOT NULL OR c3_vision IS NOT NULL
        THEN '✅ Has different cycle data'
        ELSE '✅ Only Cycle 1'
    END as status
FROM cycle_comparison
ORDER BY status DESC, name;

-- Step 4: Count how many students have this duplicate issue
SELECT 
    'Total Students' as metric,
    COUNT(DISTINCT s.id) as count
FROM students s
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'

UNION ALL

SELECT 
    'Students with Cycle 1' as metric,
    COUNT(DISTINCT s.id) as count
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'
AND vs.cycle = 1
AND vs.academic_year = '2025/2026'

UNION ALL

SELECT 
    'Students with Cycle 2' as metric,
    COUNT(DISTINCT s.id) as count
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'
AND vs.cycle = 2
AND vs.academic_year = '2025/2026'

UNION ALL

SELECT 
    'Students with Cycle 3' as metric,
    COUNT(DISTINCT s.id) as count
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'
AND vs.cycle = 3
AND vs.academic_year = '2025/2026';

-- Step 5: Check a specific student's Knack ID to cross-reference with Knack
-- Pick a student from the results above and note their Knack ID
SELECT 
    s.name,
    s.email,
    s.knack_id,
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.overall,
    vs.completion_date
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'
ORDER BY s.name, vs.cycle
LIMIT 30;

-- ============================================================================
-- CLEANUP SCRIPT - Run this if duplicates are confirmed
-- ============================================================================
-- WARNING: This will delete Cycle 2 and 3 data where it's identical to Cycle 1
-- Only run after confirming the issue exists!
-- ============================================================================

/*
-- UNCOMMENT TO RUN CLEANUP (after confirming issue)

-- Delete Cycle 2 & 3 records where all scores are identical to Cycle 1
WITH duplicate_cycles AS (
    SELECT 
        vs1.student_id,
        vs1.academic_year
    FROM vespa_scores vs1
    JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
        AND vs1.academic_year = vs2.academic_year
        AND vs2.cycle = 2
    JOIN vespa_scores vs3 ON vs1.student_id = vs3.student_id 
        AND vs1.academic_year = vs3.academic_year
        AND vs3.cycle = 3
    WHERE vs1.cycle = 1
    AND vs1.academic_year = '2025/2026'
    AND vs1.vision = vs2.vision
    AND vs1.effort = vs2.effort
    AND vs1.systems = vs2.systems
    AND vs1.practice = vs2.practice
    AND vs1.attitude = vs2.attitude
    AND vs1.overall = vs2.overall
    AND vs2.vision = vs3.vision
    AND vs2.effort = vs3.effort
    AND vs2.systems = vs3.systems
    AND vs2.practice = vs3.practice
    AND vs2.attitude = vs3.attitude
    AND vs2.overall = vs3.overall
)
DELETE FROM vespa_scores
WHERE (student_id, academic_year, cycle) IN (
    SELECT student_id, academic_year, 2
    FROM duplicate_cycles
    UNION ALL
    SELECT student_id, academic_year, 3
    FROM duplicate_cycles
);

-- Verify cleanup
SELECT 
    'After cleanup - Students with Cycle 1' as metric,
    COUNT(DISTINCT s.id) as count
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'
AND vs.cycle = 1

UNION ALL

SELECT 
    'After cleanup - Students with Cycle 2' as metric,
    COUNT(DISTINCT s.id) as count
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'
AND vs.cycle = 2

UNION ALL

SELECT 
    'After cleanup - Students with Cycle 3' as metric,
    COUNT(DISTINCT s.id) as count
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '{establishment_id}'
AND s.academic_year = '2025/2026'
AND vs.cycle = 3;

*/

