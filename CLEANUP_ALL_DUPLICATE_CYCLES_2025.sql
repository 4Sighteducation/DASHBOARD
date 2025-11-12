-- ============================================================================
-- CLEANUP ALL DUPLICATE CYCLES - Current Academic Year Only (2025/2026)
-- ============================================================================
-- This removes duplicate Cycle 2 & 3 data where it's identical to Cycle 1
-- SAFE: Only affects current year, protects all historical data
-- ============================================================================

-- Step 1: Check the scope of the problem
SELECT 
    'Total VESPA records' as metric,
    COUNT(*) as count
FROM vespa_scores
WHERE academic_year = '2025/2026'

UNION ALL

SELECT 
    'Cycle 1' as metric,
    COUNT(*) as count
FROM vespa_scores
WHERE academic_year = '2025/2026' AND cycle = 1

UNION ALL

SELECT 
    'Cycle 2' as metric,
    COUNT(*) as count
FROM vespa_scores
WHERE academic_year = '2025/2026' AND cycle = 2

UNION ALL

SELECT 
    'Cycle 3' as metric,
    COUNT(*) as count
FROM vespa_scores
WHERE academic_year = '2025/2026' AND cycle = 3;

-- Step 2: Identify duplicate cycles
-- These are where Cycle 2 & 3 are IDENTICAL to Cycle 1
WITH duplicate_analysis AS (
    SELECT 
        vs1.student_id,
        vs1.academic_year,
        s.name,
        s.email,
        -- Cycle 1 data
        vs1.vision as c1_vision,
        vs1.effort as c1_effort,
        vs1.systems as c1_systems,
        vs1.practice as c1_practice,
        vs1.attitude as c1_attitude,
        vs1.overall as c1_overall,
        -- Cycle 2 data
        vs2.vision as c2_vision,
        vs2.effort as c2_effort,
        vs2.overall as c2_overall,
        -- Cycle 3 data
        vs3.vision as c3_vision,
        vs3.effort as c3_effort,
        vs3.overall as c3_overall,
        -- Check if they're identical
        CASE 
            WHEN vs1.vision = vs2.vision 
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
            THEN TRUE
            ELSE FALSE
        END as is_duplicate
    FROM vespa_scores vs1
    LEFT JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
        AND vs1.academic_year = vs2.academic_year 
        AND vs2.cycle = 2
    LEFT JOIN vespa_scores vs3 ON vs1.student_id = vs3.student_id 
        AND vs1.academic_year = vs3.academic_year 
        AND vs3.cycle = 3
    JOIN students s ON vs1.student_id = s.id
    WHERE vs1.cycle = 1
    AND vs1.academic_year = '2025/2026'
)
SELECT 
    COUNT(*) as duplicate_students
FROM duplicate_analysis
WHERE is_duplicate = TRUE;

-- Expected: Around 91 students based on Penglais data

-- Step 3: DELETE THE DUPLICATES
-- WARNING: This will delete data. Make sure you're ready!
-- ============================================================================

BEGIN;

-- Create temp table to store what we're deleting (for safety)
CREATE TEMP TABLE deleted_vespa_records AS
SELECT 
    vs.*,
    s.name,
    s.email,
    e.name as establishment_name
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
LEFT JOIN establishments e ON s.establishment_id = e.id
WHERE vs.id IN (
    -- Find all Cycle 2 & 3 records that are duplicates of Cycle 1
    SELECT vs2.id
    FROM vespa_scores vs1
    JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
        AND vs1.academic_year = vs2.academic_year
        AND vs2.cycle IN (2, 3)
    WHERE vs1.cycle = 1
    AND vs1.academic_year = '2025/2026'
    AND vs1.vision = vs2.vision
    AND vs1.effort = vs2.effort
    AND vs1.systems = vs2.systems
    AND vs1.practice = vs2.practice
    AND vs1.attitude = vs2.attitude
    AND vs1.overall = vs2.overall
);

-- Show what will be deleted
SELECT 
    'Records to delete' as info,
    COUNT(*) as count
FROM deleted_vespa_records;

SELECT 
    cycle,
    COUNT(*) as count
FROM deleted_vespa_records
GROUP BY cycle
ORDER BY cycle;

-- DELETE THE DUPLICATES (Cycle 2 & 3 only, preserving Cycle 1)
DELETE FROM vespa_scores
WHERE id IN (
    SELECT vs2.id
    FROM vespa_scores vs1
    JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
        AND vs1.academic_year = vs2.academic_year
        AND vs2.cycle IN (2, 3)  -- Only delete Cycle 2 & 3
    WHERE vs1.cycle = 1
    AND vs1.academic_year = '2025/2026'
    -- All scores must match
    AND vs1.vision = vs2.vision
    AND vs1.effort = vs2.effort
    AND vs1.systems = vs2.systems
    AND vs1.practice = vs2.practice
    AND vs1.attitude = vs2.attitude
    AND vs1.overall = vs2.overall
);

-- Also delete empty records (all NULLs) for Cycle 2 & 3 in current year
DELETE FROM vespa_scores
WHERE academic_year = '2025/2026'
AND cycle IN (2, 3)
AND vision IS NULL
AND effort IS NULL
AND systems IS NULL
AND practice IS NULL
AND attitude IS NULL
AND overall IS NULL;

COMMIT;

-- Step 4: Verify cleanup
SELECT 
    'After cleanup' as status,
    cycle,
    COUNT(*) as count
FROM vespa_scores
WHERE academic_year = '2025/2026'
GROUP BY cycle
ORDER BY cycle;

-- Step 5: Check specific schools
-- Penglais should now show only students with actual Cycle 1 data
SELECT 
    e.name as establishment,
    vs.cycle,
    COUNT(*) as student_count
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
WHERE vs.academic_year = '2025/2026'
AND e.name ILIKE '%penglais%'
GROUP BY e.name, vs.cycle
ORDER BY vs.cycle;

-- Expected for Penglais:
-- Cycle 1: ~261 students
-- Cycle 2: 0 (or only those with different data)
-- Cycle 3: 0 (or only those with different data)

-- ============================================================================
-- VERIFICATION: Check a few sample students
-- ============================================================================

SELECT 
    s.name,
    s.email,
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.overall,
    vs.completion_date
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.email IN (
    'azama2@hwbcymru.net',  -- Should have only Cycle 1 now
    'edwardse9@hwbcymru.net',  -- Should have only Cycle 1 now
    'bakewellm@hwbcymru.net'  -- Should have only Cycle 1 now
)
AND vs.academic_year = '2025/2026'
ORDER BY s.email, vs.cycle;

-- Expected: Each email should appear only ONCE (Cycle 1 only)

-- ============================================================================
-- ROLLBACK PLAN (if something goes wrong)
-- ============================================================================
/*
If you need to restore the data, the deleted records are in temp table: deleted_vespa_records

To restore (before closing session):
INSERT INTO vespa_scores 
SELECT 
    id, student_id, cycle, vision, effort, systems, practice, attitude, 
    overall, completion_date, academic_year, created_at, updated_at
FROM deleted_vespa_records;
*/


