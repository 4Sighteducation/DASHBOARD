-- Create a view that shows students based on their VESPA data academic year
-- This solves the Whitchurch issue where students were re-uploaded with new IDs
-- but we need to see them when viewing historical data

-- Drop the view if it exists
DROP VIEW IF EXISTS students_by_vespa_year CASCADE;

-- Create the new view
CREATE VIEW students_by_vespa_year AS
SELECT DISTINCT
    s.*,
    vs.academic_year as vespa_academic_year,
    COUNT(DISTINCT vs.cycle) OVER (PARTITION BY s.id, vs.academic_year) as cycles_completed,
    MAX(vs.completion_date) OVER (PARTITION BY s.id, vs.academic_year) as latest_completion
FROM students s
INNER JOIN vespa_scores vs ON s.id = vs.student_id
WHERE vs.academic_year IS NOT NULL;

-- Create an index on the view for performance
CREATE INDEX IF NOT EXISTS idx_vespa_scores_academic_year 
ON vespa_scores(academic_year, student_id);

-- Alternative approach: Update the dashboard query
-- Instead of filtering students by their academic_year field,
-- filter by whether they have VESPA data for that year

-- Example query for the dashboard to use:
/*
-- Get students for a specific establishment and academic year
-- based on their VESPA data, not their student record

SELECT DISTINCT
    s.*,
    :selected_year as display_academic_year
FROM students s
WHERE s.establishment_id = :establishment_id
AND EXISTS (
    SELECT 1 
    FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = :selected_year
)
ORDER BY s.name;
*/

-- For immediate fix: Update students who have ONLY 2024/2025 VESPA data
-- These are students who were in the system last year but haven't done assessments this year

WITH students_only_2024_25 AS (
    SELECT DISTINCT s.id
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'  -- Whitchurch
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2024/2025'
    )
    AND NOT EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2025/2026'
    )
)
UPDATE students
SET academic_year = '2024/2025'
WHERE id IN (SELECT id FROM students_only_2024_25)
AND establishment_id = '1a327b33-d924-453c-803e-82671f94a242';

-- Show the results
SELECT 
    academic_year,
    COUNT(*) as student_count
FROM students
WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY academic_year
ORDER BY academic_year DESC;

-- Also show how many students have VESPA data for each year
SELECT 
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as students_with_vespa_data
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY vs.academic_year
ORDER BY vs.academic_year DESC;
