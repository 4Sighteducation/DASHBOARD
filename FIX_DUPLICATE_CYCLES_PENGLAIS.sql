-- ============================================================================
-- Fix Duplicate Cycles for Penglais School (and all schools)
-- ============================================================================
-- Run this to clean up cycles where data was incorrectly duplicated
-- ============================================================================

-- Step 1: Find Penglais School
SELECT id as establishment_id, name, knack_id 
FROM establishments 
WHERE name ILIKE '%penglais%';

-- Copy the establishment_id and use it below

-- Step 2: Check the issue (replace {establishment_id})
WITH cycle_data AS (
    SELECT 
        s.id,
        s.name,
        s.email,
        MAX(CASE WHEN vs.cycle = 1 THEN vs.vision END) as c1_vision,
        MAX(CASE WHEN vs.cycle = 2 THEN vs.vision END) as c2_vision,
        MAX(CASE WHEN vs.cycle = 3 THEN vs.vision END) as c3_vision,
        MAX(CASE WHEN vs.cycle = 1 THEN vs.overall END) as c1_overall,
        MAX(CASE WHEN vs.cycle = 2 THEN vs.overall END) as c2_overall,
        MAX(CASE WHEN vs.cycle = 3 THEN vs.overall END) as c3_overall
    FROM students s
    LEFT JOIN vespa_scores vs ON s.id = vs.student_id AND vs.academic_year = s.academic_year
    WHERE s.establishment_id = '{establishment_id}'  -- REPLACE THIS
    AND s.academic_year = '2025/2026'
    GROUP BY s.id, s.name, s.email
)
SELECT 
    name,
    c1_vision, c2_vision, c3_vision,
    c1_overall, c2_overall, c3_overall,
    CASE 
        WHEN c1_vision = c2_vision AND c2_vision = c3_vision 
        AND c1_overall = c2_overall AND c2_overall = c3_overall
        AND c2_vision IS NOT NULL
        THEN '⚠️ DUPLICATE'
        WHEN c2_vision IS NOT NULL OR c3_vision IS NOT NULL
        THEN '✅ Has different cycles'
        ELSE '✅ Only Cycle 1'
    END as status
FROM cycle_data
ORDER BY status DESC;

-- Step 3: DELETE duplicate Cycle 2 & 3 data for Penglais (CURRENT YEAR ONLY)
-- Run this after confirming duplicates exist above

DELETE FROM vespa_scores
WHERE id IN (
    SELECT vs.id
    FROM vespa_scores vs
    JOIN students s ON vs.student_id = s.id
    WHERE s.establishment_id = '{establishment_id}'  -- REPLACE THIS
    AND vs.academic_year = '2025/2026'
    AND vs.cycle IN (2, 3)
    AND EXISTS (
        -- Only delete if Cycle 2/3 data is identical to Cycle 1
        SELECT 1
        FROM vespa_scores vs1
        WHERE vs1.student_id = vs.student_id
        AND vs1.academic_year = vs.academic_year
        AND vs1.cycle = 1
        AND vs1.vision = vs.vision
        AND vs1.effort = vs.effort
        AND vs1.systems = vs.systems
        AND vs1.practice = vs.practice
        AND vs1.attitude = vs.attitude
        AND vs1.overall = vs.overall
    )
);

-- Step 4: Verify cleanup
SELECT 
    'After cleanup - Cycle 1' as cycle,
    COUNT(*) as count
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '{establishment_id}'  -- REPLACE THIS
AND vs.academic_year = '2025/2026'
AND vs.cycle = 1

UNION ALL

SELECT 
    'After cleanup - Cycle 2' as cycle,
    COUNT(*) as count
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '{establishment_id}'  -- REPLACE THIS
AND vs.academic_year = '2025/2026'
AND vs.cycle = 2

UNION ALL

SELECT 
    'After cleanup - Cycle 3' as cycle,
    COUNT(*) as count
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '{establishment_id}'  -- REPLACE THIS
AND vs.academic_year = '2025/2026'
AND vs.cycle = 3;

-- ============================================================================
-- OPTIONAL: Clean up ALL schools (not just Penglais)
-- ============================================================================
-- Run this if you want to fix all schools at once for 2025/2026

/*
DELETE FROM vespa_scores
WHERE id IN (
    SELECT vs.id
    FROM vespa_scores vs
    WHERE vs.academic_year = '2025/2026'
    AND vs.cycle IN (2, 3)
    AND EXISTS (
        -- Only delete if Cycle 2/3 data is identical to Cycle 1
        SELECT 1
        FROM vespa_scores vs1
        WHERE vs1.student_id = vs.student_id
        AND vs1.academic_year = vs.academic_year
        AND vs1.cycle = 1
        AND vs1.vision = vs.vision
        AND vs1.effort = vs.effort
        AND vs1.systems = vs.systems
        AND vs1.practice = vs.practice
        AND vs1.attitude = vs.attitude
        AND vs1.overall = vs.overall
    )
);

-- Check results
SELECT 
    academic_year,
    cycle,
    COUNT(*) as count
FROM vespa_scores
WHERE academic_year = '2025/2026'
GROUP BY academic_year, cycle
ORDER BY cycle;
*/

