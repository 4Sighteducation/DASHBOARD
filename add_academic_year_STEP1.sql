-- STEP 1: Add academic_year column to students table
-- Run this first and verify it works

-- Add the column (nullable initially to avoid errors)
ALTER TABLE students 
ADD COLUMN IF NOT EXISTS academic_year TEXT;

-- Create an index for performance
CREATE INDEX IF NOT EXISTS idx_students_academic_year 
ON students(establishment_id, academic_year);

-- Check if column was added successfully
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'students' 
AND column_name = 'academic_year';
