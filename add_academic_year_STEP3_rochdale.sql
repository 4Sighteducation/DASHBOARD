-- STEP 3: Fix Rochdale Sixth Form College specifically
-- Run this after STEP 2 to ensure exactly 1026 students for 2025/2026

-- First, identify Rochdale's establishment ID
WITH rochdale AS (
    SELECT id, name 
    FROM establishments 
    WHERE name ILIKE '%Rochdale Sixth%'
    LIMIT 1
)
SELECT * FROM rochdale;

-- Set the most recent 1026 students to 2025/2026
WITH rochdale AS (
    SELECT id FROM establishments 
    WHERE name ILIKE '%Rochdale Sixth%'
    LIMIT 1
),
recent_students AS (
    SELECT s.id
    FROM students s, rochdale r
    WHERE s.establishment_id = r.id
    ORDER BY s.created_at DESC
    LIMIT 1026
)
UPDATE students s
SET academic_year = '2025/2026'
FROM recent_students rs
WHERE s.id = rs.id;

-- Set all other Rochdale students to 2024/2025
WITH rochdale AS (
    SELECT id FROM establishments 
    WHERE name ILIKE '%Rochdale Sixth%'
    LIMIT 1
)
UPDATE students s
SET academic_year = '2024/2025'
FROM rochdale r
WHERE s.establishment_id = r.id
AND (s.academic_year != '2025/2026' OR s.academic_year IS NULL);

-- Verify the fix - should show 1026 for 2025/2026
WITH rochdale AS (
    SELECT id, name FROM establishments 
    WHERE name ILIKE '%Rochdale Sixth%'
    LIMIT 1
)
SELECT 
    r.name as school,
    s.academic_year,
    COUNT(*) as student_count
FROM students s
JOIN rochdale r ON s.establishment_id = r.id
GROUP BY r.name, s.academic_year
ORDER BY s.academic_year DESC;
