-- Fix incorrect academic year data in school_statistics and national_statistics tables
-- These were incorrectly set to 2025-26 based on the calculation date instead of the actual data dates

-- First, let's verify what we're about to update
SELECT 'school_statistics' as table_name, academic_year, COUNT(*) as records_to_update
FROM school_statistics
WHERE academic_year = '2025-26'
GROUP BY academic_year;

SELECT 'national_statistics' as table_name, academic_year, COUNT(*) as records_to_update
FROM national_statistics
WHERE academic_year = '2025-26'
GROUP BY academic_year;

-- Update school_statistics from 2025-26 to 2024-25
-- This assumes all current 2025-26 data should actually be 2024-25
-- based on the fact that vespa_scores shows the latest data is 2024-25
UPDATE school_statistics
SET academic_year = '2024-25'
WHERE academic_year = '2025-26';

-- Update national_statistics from 2025-26 to 2024-25
UPDATE national_statistics
SET academic_year = '2024-25'
WHERE academic_year = '2025-26';

-- Verify the updates
SELECT 'school_statistics' as table_name, academic_year, COUNT(*) as record_count
FROM school_statistics
GROUP BY academic_year
ORDER BY academic_year;

SELECT 'national_statistics' as table_name, academic_year, COUNT(*) as record_count
FROM national_statistics
GROUP BY academic_year
ORDER BY academic_year;

-- Also check if we need to update the format in question_statistics and national_question_statistics
-- They use "2024/2025" format instead of "2024-25" format
-- This might cause issues with filtering/matching

-- Optional: Standardize format from "2024/2025" to "2024-25"
-- Uncomment if you want to standardize the format across all tables
/*
UPDATE question_statistics
SET academic_year = '2024-25'
WHERE academic_year = '2024/2025';

UPDATE national_question_statistics
SET academic_year = '2024-25'
WHERE academic_year = '2024/2025';
*/