-- Optional: Clean up NULL records after restoring British School Al Khubairat data
-- Run this AFTER successfully restoring the 2024/2025 data

-- First, verify the restore worked (check for non-null 2024/2025 data)
SELECT 
    academic_year,
    cycle,
    COUNT(*) as total_records,
    COUNT(CASE WHEN vision IS NOT NULL THEN 1 END) as non_null_records
FROM vespa_scores
WHERE student_id IN (
    SELECT id FROM students 
    WHERE establishment_id = (
        SELECT id FROM establishments 
        WHERE name = 'The British School Al Khubairat'
    )
)
GROUP BY academic_year, cycle
ORDER BY academic_year, cycle;

-- If satisfied with restore, remove NULL records for 2025/2026
-- UNCOMMENT to execute:
/*
DELETE FROM vespa_scores
WHERE student_id IN (
    SELECT id FROM students 
    WHERE establishment_id = (
        SELECT id FROM establishments 
        WHERE name = 'The British School Al Khubairat'
    )
)
AND academic_year = '2025/2026'
AND vision IS NULL 
AND effort IS NULL 
AND systems IS NULL 
AND practice IS NULL 
AND attitude IS NULL;
*/
