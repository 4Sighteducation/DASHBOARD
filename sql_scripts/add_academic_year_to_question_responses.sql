-- Add academic_year column to question_responses table
ALTER TABLE question_responses
ADD COLUMN IF NOT EXISTS academic_year character varying;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_question_responses_academic_year_cycle 
ON question_responses(academic_year, cycle);

-- Backfill academic_year from vespa_scores table (for existing data)
UPDATE question_responses qr
SET academic_year = vs.academic_year
FROM vespa_scores vs
WHERE qr.student_id = vs.student_id
AND qr.cycle = vs.cycle
AND qr.academic_year IS NULL
AND vs.academic_year IS NOT NULL;

-- For any remaining nulls, set based on current date
UPDATE question_responses
SET academic_year = CASE 
    WHEN EXTRACT(MONTH FROM COALESCE(created_at, CURRENT_DATE)) >= 9 THEN 
        CONCAT(EXTRACT(YEAR FROM COALESCE(created_at, CURRENT_DATE)), '/', EXTRACT(YEAR FROM COALESCE(created_at, CURRENT_DATE)) + 1)
    ELSE 
        CONCAT(EXTRACT(YEAR FROM COALESCE(created_at, CURRENT_DATE)) - 1, '/', EXTRACT(YEAR FROM COALESCE(created_at, CURRENT_DATE)))
END
WHERE academic_year IS NULL;

-- Verify the update
SELECT 
    cycle,
    academic_year,
    COUNT(*) as response_count,
    COUNT(DISTINCT student_id) as student_count
FROM question_responses
WHERE question_id IN ('outcome_q_confident', 'outcome_q_equipped', 'outcome_q_support')
GROUP BY cycle, academic_year
ORDER BY academic_year, cycle;