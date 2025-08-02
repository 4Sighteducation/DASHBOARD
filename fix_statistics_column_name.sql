-- Fix the column name mismatch in question_statistics table
-- The stored procedure expects 'mean_response' but the table has 'mean'

-- Option 1: Rename the column to match the stored procedure
ALTER TABLE question_statistics 
RENAME COLUMN mean TO mean_response;

-- Option 2: Update the stored procedure to use 'mean' instead of 'mean_response'
-- (This would require modifying create_statistics_function_fixed.sql)