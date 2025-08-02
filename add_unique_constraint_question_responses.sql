-- Add unique constraint to prevent duplicate question responses
-- This ensures that each student can only have one response per question per cycle

-- First, let's check if there are any existing duplicates
-- (This query won't modify data, just shows if duplicates exist)
WITH duplicates AS (
    SELECT 
        student_id, 
        cycle, 
        question_id,
        COUNT(*) as count
    FROM question_responses
    GROUP BY student_id, cycle, question_id
    HAVING COUNT(*) > 1
)
SELECT COUNT(*) as duplicate_groups FROM duplicates;

-- If the above query returns 0, you can safely add the constraint
-- If it returns > 0, you need to clean duplicates first

-- Add the unique constraint
ALTER TABLE question_responses 
ADD CONSTRAINT unique_student_cycle_question 
UNIQUE (student_id, cycle, question_id);

-- Create an index for better performance (if not already created by the constraint)
CREATE INDEX IF NOT EXISTS idx_question_responses_unique 
ON question_responses(student_id, cycle, question_id);

-- Optional: If you need to clean duplicates first, run this:
-- This keeps the most recent response for each student/cycle/question combination
/*
DELETE FROM question_responses a
USING question_responses b
WHERE a.id < b.id 
  AND a.student_id = b.student_id 
  AND a.cycle = b.cycle 
  AND a.question_id = b.question_id;
*/