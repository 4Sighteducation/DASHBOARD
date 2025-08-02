-- Check for any duplicate student/cycle/question combinations
-- This should return 0 rows if the constraint is working properly
SELECT 
    student_id, 
    cycle, 
    question_id, 
    COUNT(*) as duplicate_count
FROM question_responses
GROUP BY student_id, cycle, question_id
HAVING COUNT(*) > 1;

-- Also check the constraint exists
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'question_responses'::regclass
AND contype = 'u';