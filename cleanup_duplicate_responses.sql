-- Cleanup duplicate question_responses if needed
-- BE CAREFUL: This will delete data!

-- First, check what we're dealing with
WITH duplicate_analysis AS (
    SELECT 
        student_id, 
        cycle, 
        question_id,
        COUNT(*) as count,
        MIN(created_at) as first_created,
        MAX(created_at) as last_created,
        COUNT(DISTINCT response_value) as different_values
    FROM question_responses
    GROUP BY student_id, cycle, question_id
    HAVING COUNT(*) > 1
)
SELECT 
    COUNT(*) as duplicate_groups,
    SUM(count - 1) as records_to_delete,
    MIN(first_created) as earliest_duplicate,
    MAX(last_created) as latest_duplicate
FROM duplicate_analysis;

-- If you need to clean duplicates, keeping the most recent:
/*
-- DANGEROUS: Uncomment only if you're sure!
WITH duplicates_to_delete AS (
    SELECT id, 
           ROW_NUMBER() OVER (
               PARTITION BY student_id, cycle, question_id 
               ORDER BY created_at DESC
           ) as rn
    FROM question_responses
)
DELETE FROM question_responses
WHERE id IN (
    SELECT id FROM duplicates_to_delete WHERE rn > 1
);
*/

-- Alternative: Complete fresh start for question_responses
-- This preserves students, establishments, vespa_scores, etc.
/*
-- VERY DANGEROUS: Only if you want to completely re-sync question_responses
TRUNCATE TABLE question_responses;
*/

-- After cleanup, verify the constraint is in place
SELECT 
    con.conname AS constraint_name,
    con.contype AS constraint_type,
    pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_namespace nsp ON nsp.oid = con.connamespace
JOIN pg_class cls ON cls.oid = con.conrelid
WHERE nsp.nspname = 'public'
    AND cls.relname = 'question_responses'
    AND con.contype = 'u';  -- unique constraints