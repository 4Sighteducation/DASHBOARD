-- ============================================================================
-- Check if Question Responses Have the Same Duplicate Issue
-- ============================================================================

-- Check Penglais question responses
SELECT 
    'Question Responses by Cycle' as check_type,
    qr.cycle,
    COUNT(DISTINCT qr.student_id) as unique_students,
    COUNT(*) as total_responses
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
WHERE e.name ILIKE '%penglais%'
AND qr.academic_year = '2025/2026'
GROUP BY qr.cycle
ORDER BY qr.cycle;

-- If duplicates exist, we'd see same student_count for all 3 cycles

-- Check for students with identical responses across all cycles
WITH student_response_counts AS (
    SELECT 
        qr.student_id,
        qr.question_id,
        COUNT(DISTINCT qr.cycle) as cycle_count,
        COUNT(DISTINCT qr.response_value) as unique_values
    FROM question_responses qr
    JOIN students s ON qr.student_id = s.id
    JOIN establishments e ON s.establishment_id = e.id
    WHERE e.name ILIKE '%penglais%'
    AND qr.academic_year = '2025/2026'
    GROUP BY qr.student_id, qr.question_id
    HAVING COUNT(DISTINCT qr.cycle) = 3  -- Present in all 3 cycles
    AND COUNT(DISTINCT qr.response_value) = 1  -- Same answer in all 3
)
SELECT 
    COUNT(*) as potential_duplicate_responses,
    'Responses that appear in all 3 cycles with identical values' as note
FROM student_response_counts;

-- STEP 3: If duplicates found, safe cleanup query
-- Delete question responses for Cycle 2 & 3 where the responses are IDENTICAL
-- to Cycle 1 (same student, same question, same value across all cycles)

/*
BEGIN;

WITH duplicate_responses AS (
    SELECT qr2.id
    FROM question_responses qr1
    JOIN question_responses qr2 ON qr1.student_id = qr2.student_id
        AND qr1.academic_year = qr2.academic_year
        AND qr1.question_id = qr2.question_id
        AND qr2.cycle IN (2, 3)
    WHERE qr1.cycle = 1
    AND qr1.academic_year = '2025/2026'
    AND qr1.response_value = qr2.response_value  -- Same answer
),
deleted AS (
    DELETE FROM question_responses
    WHERE id IN (SELECT id FROM duplicate_responses)
    RETURNING id
)
SELECT COUNT(*) as deleted_question_responses FROM deleted;

-- Review the count, then:
COMMIT;
-- Or if something looks wrong:
-- ROLLBACK;
*/

-- ============================================================================
-- SAFER ALTERNATIVE: Only delete where completion dates match in VESPA scores
-- ============================================================================
-- This ties question response deletion to VESPA score duplicates

/*
BEGIN;

-- Delete question responses only for student/cycle combinations where
-- VESPA scores were duplicates (same date)
WITH duplicate_vespa_combos AS (
    SELECT DISTINCT
        vs2.student_id,
        vs2.cycle,
        vs2.academic_year
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
    AND vs1.completion_date = vs2.completion_date  -- Same date = duplicate
),
deleted AS (
    DELETE FROM question_responses
    WHERE (student_id, cycle, academic_year) IN (
        SELECT student_id, cycle, academic_year FROM duplicate_vespa_combos
    )
    RETURNING id
)
SELECT COUNT(*) as deleted_question_responses FROM deleted;

COMMIT;
-- Or ROLLBACK if needed
*/





