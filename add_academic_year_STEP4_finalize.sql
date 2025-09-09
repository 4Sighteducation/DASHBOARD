-- STEP 4: Finalize the schema
-- Run this after verifying all students have academic_year populated

-- Check if any students still have NULL academic_year
SELECT COUNT(*) as null_count
FROM students
WHERE academic_year IS NULL;

-- If the above returns 0, proceed with making the column NOT NULL
ALTER TABLE students 
ALTER COLUMN academic_year SET NOT NULL;

-- Add a constraint to ensure valid format (YYYY/YYYY)
ALTER TABLE students
ADD CONSTRAINT check_academic_year_format 
CHECK (academic_year ~ '^\d{4}/\d{4}$');

-- Create a view for easy dashboard queries
CREATE OR REPLACE VIEW student_counts_by_year AS
SELECT 
    e.name as establishment_name,
    s.establishment_id,
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
JOIN establishments e ON s.establishment_id = e.id
GROUP BY e.name, s.establishment_id, s.academic_year
ORDER BY e.name, s.academic_year DESC;

-- Test the view
SELECT * FROM student_counts_by_year
WHERE establishment_name ILIKE '%Rochdale%';
