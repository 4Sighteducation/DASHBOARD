-- 1. Check if the Staff Admin's establishment exists
SELECT id, knack_id, name 
FROM establishments 
WHERE knack_id = '603e9f97cb8481001b31183d';

-- 2. Show some sample establishments to verify data
SELECT id, knack_id, name 
FROM establishments 
LIMIT 10;

-- 3. Check the Bangkok Prep establishment (that Super User selected)
SELECT id, knack_id, name 
FROM establishments 
WHERE id = 'd7fe1ebf-4a94-42c3-8ff6-633b35ba0c04'
   OR name LIKE '%Bangkok Prep%';

-- 4. Check the questions table structure
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'questions'
ORDER BY ordinal_position;

-- 5. Check if question_statistics table has data for Bangkok Prep
SELECT COUNT(*) as record_count, establishment_id
FROM question_statistics
WHERE establishment_id = 'd7fe1ebf-4a94-42c3-8ff6-633b35ba0c04'
GROUP BY establishment_id;

-- 6. Check school_statistics for Bangkok Prep
SELECT * 
FROM school_statistics
WHERE establishment_id = 'd7fe1ebf-4a94-42c3-8ff6-633b35ba0c04'
LIMIT 5;