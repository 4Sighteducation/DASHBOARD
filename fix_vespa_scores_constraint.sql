-- Fix for VESPA scores to allow multiple years of data per student
-- This allows students to have Cycle 1, 2, 3 for EACH academic year

-- IMPORTANT: Run this in Supabase SQL Editor

-- Step 1: Drop the existing unique constraint
ALTER TABLE vespa_scores 
DROP CONSTRAINT IF EXISTS vespa_scores_student_id_cycle_key;

-- Step 2: Add the correct unique constraint including academic_year
ALTER TABLE vespa_scores 
ADD CONSTRAINT vespa_scores_student_id_cycle_academic_year_key 
UNIQUE (student_id, cycle, academic_year);

-- Step 3: Add an index for better query performance
CREATE INDEX IF NOT EXISTS idx_vespa_scores_student_cycle_year 
ON vespa_scores(student_id, cycle, academic_year);

-- Verify the change
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'vespa_scores'::regclass
AND contype = 'u';  -- 'u' for unique constraints
