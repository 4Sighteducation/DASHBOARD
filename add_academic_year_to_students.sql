-- Add academic_year column to students table
-- This will allow precise control over which students belong to which academic year

-- Step 1: Add the column (nullable initially)
ALTER TABLE students 
ADD COLUMN IF NOT EXISTS academic_year TEXT;

-- Step 2: Create an index for performance
CREATE INDEX IF NOT EXISTS idx_students_academic_year 
ON students(establishment_id, academic_year);

-- Step 3: Set initial values based on existing VESPA data
-- This assigns students to the most recent academic year they have data for
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

-- Step 4: For students without any VESPA data, assign based on creation date
-- (You may want to adjust this logic)
UPDATE students
SET academic_year = 
    CASE 
        WHEN created_at >= '2025-08-01' THEN '2025/2026'
        WHEN created_at >= '2024-08-01' THEN '2024/2025'
        WHEN created_at >= '2023-08-01' THEN '2023/2024'
        ELSE '2023/2024' -- Default for very old records
    END
WHERE academic_year IS NULL;

-- Step 5: Make the column NOT NULL now that all records have values
ALTER TABLE students 
ALTER COLUMN academic_year SET NOT NULL;

-- Step 6: Add a constraint to ensure valid format
ALTER TABLE students
ADD CONSTRAINT check_academic_year_format 
CHECK (academic_year ~ '^\d{4}/\d{4}$');

-- Step 7: Create a function to get student counts by academic year
CREATE OR REPLACE FUNCTION get_student_counts_by_year(p_establishment_id UUID)
RETURNS TABLE (
    academic_year TEXT,
    total_students BIGINT,
    students_with_vespa BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.academic_year,
        COUNT(DISTINCT s.id) as total_students,
        COUNT(DISTINCT CASE 
            WHEN EXISTS (
                SELECT 1 FROM vespa_scores v 
                WHERE v.student_id = s.id 
                AND v.academic_year = s.academic_year
            ) THEN s.id 
        END) as students_with_vespa
    FROM students s
    WHERE s.establishment_id = p_establishment_id
    GROUP BY s.academic_year
    ORDER BY s.academic_year DESC;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Fix Rochdale's specific case
-- Assign the most recent 1026 students to 2025/2026
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

-- Assign remaining Rochdale students to 2024/2025
WITH rochdale AS (
    SELECT id FROM establishments 
    WHERE name ILIKE '%Rochdale Sixth%'
    LIMIT 1
)
UPDATE students s
SET academic_year = '2024/2025'
FROM rochdale r
WHERE s.establishment_id = r.id
AND s.academic_year != '2025/2026';

-- Display the results for verification
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
