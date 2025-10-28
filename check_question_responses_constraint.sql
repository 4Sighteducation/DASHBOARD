-- Check question_responses table constraints
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'question_responses'::regclass
AND contype IN ('u', 'p')
ORDER BY conname;

