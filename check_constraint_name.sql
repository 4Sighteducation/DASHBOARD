-- Check what constraints exist on vespa_scores table
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'vespa_scores'::regclass
ORDER BY conname;

-- Also check the columns in any unique constraints
SELECT 
    conname,
    array_agg(attname ORDER BY attnum) AS columns
FROM pg_constraint 
JOIN pg_attribute ON conrelid = attrelid AND attnum = ANY(conkey)
WHERE conrelid = 'vespa_scores'::regclass
AND contype = 'u'
GROUP BY conname;
