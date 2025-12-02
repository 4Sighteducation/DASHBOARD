-- ============================================================================
-- COMPLETE CLEANUP: VESPA Scores AND Question Responses
-- ============================================================================
-- Run ONCE to clean up ALL duplicates from old sync bug
-- SAFE: Only touches 2025/2026, uses completion_date as proof
-- ============================================================================

-- STEP 1: Preview what will be deleted
SELECT 
    'BEFORE CLEANUP' as status,
    '2025/2026 ONLY' as academic_year_affected,
    'VESPA Scores' as table_name,
    cycle,
    COUNT(*) as record_count
FROM vespa_scores
WHERE academic_year = '2025/2026'  -- ONLY current year
GROUP BY cycle
ORDER BY cycle;

-- STEP 2: Count duplicates
WITH cycle_dates AS (
    SELECT 
        student_id,
        MAX(CASE WHEN cycle = 1 THEN completion_date END) as c1_date,
        MAX(CASE WHEN cycle = 2 THEN completion_date END) as c2_date,
        MAX(CASE WHEN cycle = 3 THEN completion_date END) as c3_date
    FROM vespa_scores
    WHERE academic_year = '2025/2026'
    GROUP BY student_id
)
SELECT 
    COUNT(*) as students_with_duplicate_dates,
    'Students where all 3 cycles have same completion_date (DEFINITE duplicates)' as note
FROM cycle_dates
WHERE c1_date = c2_date 
AND c2_date = c3_date
AND c1_date IS NOT NULL;

-- STEP 3: BEGIN TRANSACTION (can rollback if needed)
BEGIN;

-- ============================================================================
-- CLEANUP PART 1: VESPA Scores
-- ============================================================================

-- Delete Type A: Cycle 2 & 3 where scores AND date match Cycle 1
WITH deleted_vespa_duplicates AS (
    DELETE FROM vespa_scores
    WHERE id IN (
        SELECT vs2.id
        FROM vespa_scores vs1
        JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
            AND vs1.academic_year = vs2.academic_year
            AND vs2.cycle IN (2, 3)
        WHERE vs1.cycle = 1
        AND vs1.academic_year = '2025/2026'  -- ONLY current year!
        -- All scores must match
        AND vs1.vision = vs2.vision
        AND vs1.effort = vs2.effort
        AND vs1.systems = vs2.systems
        AND vs1.practice = vs2.practice
        AND vs1.attitude = vs2.attitude
        AND vs1.overall = vs2.overall
        -- CRITICAL: Date must also match (impossible for real data!)
        AND vs1.completion_date = vs2.completion_date
    )
    RETURNING id
)
SELECT COUNT(*) as vespa_duplicates_deleted FROM deleted_vespa_duplicates;

-- Delete Type B: Empty Cycle 2 & 3 records (all NULLs)
WITH deleted_vespa_empty AS (
    DELETE FROM vespa_scores
    WHERE academic_year = '2025/2026'  -- ONLY current year!
    AND cycle IN (2, 3)
    AND vision IS NULL
    AND effort IS NULL
    AND systems IS NULL
    AND practice IS NULL
    AND attitude IS NULL
    AND overall IS NULL
    RETURNING id
)
SELECT COUNT(*) as vespa_empty_deleted FROM deleted_vespa_empty;

-- ============================================================================
-- CLEANUP PART 2: Question Responses (if needed)
-- ============================================================================

-- Delete question responses for Cycle 2 & 3 ONLY where:
-- 1. They're for the same student/question as Cycle 1
-- 2. The response value is identical
-- 3. The corresponding VESPA score was a duplicate (safest approach)

-- First, identify which student/cycle combos had duplicate VESPA scores
-- (We just deleted them, but we can identify the pattern)
WITH should_have_been_deleted_vespa AS (
    SELECT DISTINCT
        vs2.student_id,
        vs2.cycle
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
    AND vs1.completion_date = vs2.completion_date
),
deleted_question_responses AS (
    -- NO WAIT - If we already deleted the VESPA scores above, 
    -- we can't find the pattern anymore!
    -- Better approach: Delete question responses where response values are identical
    DELETE FROM question_responses
    WHERE id IN (
        SELECT qr2.id
        FROM question_responses qr1
        JOIN question_responses qr2 ON qr1.student_id = qr2.student_id
            AND qr1.academic_year = qr2.academic_year
            AND qr1.question_id = qr2.question_id
            AND qr2.cycle IN (2, 3)
        WHERE qr1.cycle = 1
        AND qr1.academic_year = '2025/2026'  -- ONLY current year!
        AND qr1.response_value = qr2.response_value  -- Same answer
        -- Additional safety: Only delete if ALL 3 cycles have same answer
        AND EXISTS (
            SELECT 1
            FROM question_responses qr3
            WHERE qr3.student_id = qr1.student_id
            AND qr3.academic_year = qr1.academic_year
            AND qr3.question_id = qr1.question_id
            AND qr3.cycle = 3
            AND qr3.response_value = qr1.response_value
        )
    )
    RETURNING id
)
SELECT COUNT(*) as question_responses_deleted FROM deleted_question_responses;

-- STEP 4: Review results BEFORE committing
SELECT 
    'AFTER CLEANUP (not committed yet)' as status,
    cycle,
    COUNT(*) as record_count
FROM vespa_scores
WHERE academic_year = '2025/2026'
GROUP BY cycle
ORDER BY cycle;

-- Check question responses
SELECT 
    'Question Responses After Cleanup' as status,
    cycle,
    COUNT(*) as response_count
FROM question_responses
WHERE academic_year = '2025/2026'
GROUP BY cycle
ORDER BY cycle;

-- STEP 5: If numbers look good, COMMIT:
-- COMMIT;

-- If something looks wrong, ROLLBACK:
-- ROLLBACK;

-- ============================================================================
-- After COMMIT, verify Penglais specifically
-- ============================================================================
/*
SELECT 
    e.name as school,
    COUNT(CASE WHEN vs.cycle = 1 THEN 1 END) as cycle_1_count,
    COUNT(CASE WHEN vs.cycle = 2 THEN 1 END) as cycle_2_count,
    COUNT(CASE WHEN vs.cycle = 3 THEN 1 END) as cycle_3_count
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
WHERE vs.academic_year = '2025/2026'
AND e.name ILIKE '%penglais%'
GROUP BY e.name;

-- Expected for Penglais:
-- Cycle 1: ~261 (actual completions)
-- Cycle 2: 0-5 (only genuine)
-- Cycle 3: 0
*/





