-- STEP 2: Populate academic_year based on existing data
-- Run this after STEP 1 succeeds

-- First, set academic years based on existing VESPA data
UPDATE students s
SET academic_year = (
    SELECT MAX(v.academic_year)
    FROM vespa_scores v
    WHERE v.student_id = s.id
)
WHERE academic_year IS NULL
AND EXISTS (
    SELECT 1 FROM vespa_scores v WHERE v.student_id = s.id
);

-- For students without VESPA data, assign based on creation date
UPDATE students
SET academic_year = 
    CASE 
        WHEN created_at >= '2025-08-01' THEN '2025/2026'
        WHEN created_at >= '2024-08-01' THEN '2024/2025'
        WHEN created_at >= '2023-08-01' THEN '2023/2024'
        ELSE '2023/2024' -- Default for very old records
    END
WHERE academic_year IS NULL;

-- Check how many records were updated
SELECT 
    academic_year,
    COUNT(*) as student_count
FROM students
GROUP BY academic_year
ORDER BY academic_year DESC;
