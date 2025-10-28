-- ============================================================================
-- Fix ALL Table Constraints for Multi-Year Support
-- ============================================================================
-- This ensures students, VESPA scores, AND question responses 
-- can exist across multiple academic years
-- ============================================================================

-- ============================================================================
-- 1. STUDENTS TABLE
-- ============================================================================

-- Drop old email-only constraints
ALTER TABLE students DROP CONSTRAINT IF EXISTS students_email_key;
ALTER TABLE students DROP CONSTRAINT IF EXISTS students_email_unique;

-- Add new constraint: email + academic_year
-- Allows same email across different years
ALTER TABLE students 
DROP CONSTRAINT IF EXISTS students_email_academic_year_key;

ALTER TABLE students 
ADD CONSTRAINT students_email_academic_year_key 
UNIQUE (email, academic_year);

-- ============================================================================
-- 2. VESPA_SCORES TABLE  
-- ============================================================================

-- Drop old student_id + cycle only constraint
ALTER TABLE vespa_scores 
DROP CONSTRAINT IF EXISTS vespa_scores_student_id_cycle_key;

-- Add new constraint: student_id + cycle + academic_year
-- Allows same student to have Cycle 1 scores in both 2024/2025 AND 2025/2026
ALTER TABLE vespa_scores 
DROP CONSTRAINT IF EXISTS vespa_scores_student_id_cycle_academic_year_key;

ALTER TABLE vespa_scores 
ADD CONSTRAINT vespa_scores_student_id_cycle_academic_year_key 
UNIQUE (student_id, cycle, academic_year);

-- ============================================================================
-- 3. QUESTION_RESPONSES TABLE
-- ============================================================================

-- Drop any old constraints that don't include academic_year
ALTER TABLE question_responses 
DROP CONSTRAINT IF EXISTS question_responses_student_id_cycle_question_id_key;

-- Add new constraint: student_id + cycle + academic_year + question_id
-- Allows same student to answer same question in Cycle 1 across different years
ALTER TABLE question_responses 
DROP CONSTRAINT IF EXISTS question_responses_student_cycle_year_question_key;

ALTER TABLE question_responses 
ADD CONSTRAINT question_responses_student_cycle_year_question_key 
UNIQUE (student_id, cycle, academic_year, question_id);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check all constraints are correct
SELECT 
    'students' as table_name,
    conname as constraint_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'students'::regclass
AND contype = 'u'
AND conname LIKE '%email%'

UNION ALL

SELECT 
    'vespa_scores' as table_name,
    conname as constraint_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'vespa_scores'::regclass
AND contype = 'u'

UNION ALL

SELECT 
    'question_responses' as table_name,
    conname as constraint_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'question_responses'::regclass
AND contype = 'u';

