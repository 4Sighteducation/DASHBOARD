-- Check the constraint on question_responses table
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'question_responses'::regclass
AND conname LIKE '%response_value%';

-- Check for any existing responses with value 0
SELECT COUNT(*), question_id 
FROM question_responses 
WHERE response_value = 0
GROUP BY question_id;

-- Check unique question_ids to see the pattern
SELECT DISTINCT question_id 
FROM question_responses 
ORDER BY question_id
LIMIT 20;