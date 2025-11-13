-- ============================================================================
-- RUN ONCE: Comprehensive Cleanup of ALL Duplicate VESPA Cycles
-- ============================================================================
-- Date: November 13, 2025
-- Purpose: Clean up duplicates caused by old sync bug (v3.0)
-- Safe: Uses completion_date as proof of duplicates
-- ============================================================================

-- STEP 1: Check the scope of the problem
SELECT 
    'Current situation' as status,
    cycle,
    COUNT(*) as record_count
FROM vespa_scores
WHERE academic_year = '2025/2026'
GROUP BY cycle
ORDER BY cycle;

-- Expected to see something like:
-- Cycle 1: ~1200 records
-- Cycle 2: ~1200 records (should be much less!)
-- Cycle 3: ~1200 records (should be much less!)

-- STEP 2: Identify duplicates by completion_date
-- Show how many students have same date for all 3 cycles (PROOF of duplication)
WITH cycle_dates AS (
    SELECT 
        student_id,
        MAX(CASE WHEN cycle = 1 THEN completion_date END) as c1_date,
        MAX(CASE WHEN cycle = 2 THEN completion_date END) as c2_date,
        MAX(CASE WHEN cycle = 3 THEN completion_date END) as c3_date,
        MAX(CASE WHEN cycle = 1 THEN overall END) as c1_overall,
        MAX(CASE WHEN cycle = 2 THEN overall END) as c2_overall,
        MAX(CASE WHEN cycle = 3 THEN overall END) as c3_overall
    FROM vespa_scores
    WHERE academic_year = '2025/2026'
    GROUP BY student_id
)
SELECT 
    COUNT(*) as students_with_identical_dates,
    'These have all 3 cycles with same completion date - DEFINITE duplicates' as note
FROM cycle_dates
WHERE c1_date = c2_date 
AND c2_date = c3_date
AND c1_date IS NOT NULL;

-- STEP 3: BEGIN TRANSACTION (for safety - can rollback if something goes wrong)
BEGIN;

-- STEP 3A: Delete Cycle 2 & 3 where they're identical to Cycle 1 (same scores AND date)
WITH deleted_duplicates AS (
    DELETE FROM vespa_scores
    WHERE id IN (
        SELECT vs2.id
        FROM vespa_scores vs1
        JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
            AND vs1.academic_year = vs2.academic_year
            AND vs2.cycle IN (2, 3)
        WHERE vs1.cycle = 1
        AND vs1.academic_year = '2025/2026'
        -- All scores must match
        AND vs1.vision = vs2.vision
        AND vs1.effort = vs2.effort
        AND vs1.systems = vs2.systems
        AND vs1.practice = vs2.practice
        AND vs1.attitude = vs2.attitude
        AND vs1.overall = vs2.overall
        -- CRITICAL: Completion date must also match (impossible for real data!)
        AND vs1.completion_date = vs2.completion_date
    )
    RETURNING id, student_id, cycle
)
SELECT COUNT(*) as deleted_count FROM deleted_duplicates;

-- STEP 3B: Delete Cycle 2 & 3 records with NULL dates where Cycle 1 has a date
-- If Cycle 1 has a date but Cycle 2/3 don't, they're incomplete/invalid records
WITH deleted_null_dates AS (
    DELETE FROM vespa_scores
    WHERE id IN (
        SELECT vs2.id
        FROM vespa_scores vs1
        JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
            AND vs1.academic_year = vs2.academic_year
            AND vs2.cycle IN (2, 3)
        WHERE vs1.cycle = 1
        AND vs1.academic_year = '2025/2026'
        AND vs1.completion_date IS NOT NULL  -- C1 has a date
        AND vs2.completion_date IS NULL      -- But C2/C3 don't
        -- Also check if ALL scores are NULL (completely empty record)
        AND vs2.vision IS NULL
        AND vs2.effort IS NULL
        AND vs2.systems IS NULL
        AND vs2.practice IS NULL
        AND vs2.attitude IS NULL
        AND vs2.overall IS NULL
    )
    RETURNING id, student_id, cycle
)
SELECT COUNT(*) as deleted_null_count FROM deleted_null_dates;

-- STEP 4: Check the result BEFORE committing
SELECT 
    'After cleanup (preview)' as status,
    cycle,
    COUNT(*) as record_count
FROM vespa_scores
WHERE academic_year = '2025/2026'
GROUP BY cycle
ORDER BY cycle;

-- Expected result for Penglais after cleanup:
-- Cycle 1: ~261 records (only those with actual data)
-- Cycle 2: 0-10 records (only genuine completions)
-- Cycle 3: 0 records

-- STEP 5: Review and COMMIT or ROLLBACK
-- If the numbers look good, COMMIT:
COMMIT;

-- If something looks wrong, ROLLBACK:
-- ROLLBACK;

-- STEP 6: Verify specific schools
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

-- Check a few other schools too
SELECT 
    e.name as establishment,
    COUNT(CASE WHEN vs.cycle = 1 THEN 1 END) as cycle_1_count,
    COUNT(CASE WHEN vs.cycle = 2 THEN 1 END) as cycle_2_count,
    COUNT(CASE WHEN vs.cycle = 3 THEN 1 END) as cycle_3_count
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
WHERE vs.academic_year = '2025/2026'
GROUP BY e.name
HAVING COUNT(CASE WHEN vs.cycle = 2 THEN 1 END) > 0  -- Only show schools with Cycle 2 data
ORDER BY e.name
LIMIT 20;

-- ============================================================================
-- SUCCESS METRICS
-- ============================================================================
-- Before cleanup: ~3600 total VESPA records (1200 × 3 cycles)
-- After cleanup: ~1400 total VESPA records (1200 C1 + ~200 genuine C2/C3)
-- Deleted: ~2200 duplicate records
-- ============================================================================


