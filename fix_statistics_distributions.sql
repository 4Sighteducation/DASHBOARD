-- Fix missing distribution arrays and counts in question_statistics
-- Run this in Supabase SQL Editor

-- First, let's create a function to calculate distribution for a given set of responses
CREATE OR REPLACE FUNCTION calculate_distribution_for_stats()
RETURNS void AS $$
DECLARE
    stat_record RECORD;
    dist_array integer[];
    response_count integer;
BEGIN
    -- Loop through all statistics records
    FOR stat_record IN 
        SELECT id, establishment_id, question_id, academic_year, cycle
        FROM question_statistics
        WHERE distribution IS NULL OR count IS NULL
    LOOP
        -- Initialize distribution array [0,0,0,0,0] for scores 1-5
        dist_array := ARRAY[0,0,0,0,0];
        response_count := 0;
        
        -- Calculate distribution from actual responses
        WITH response_data AS (
            SELECT 
                qr.response_value,
                COUNT(*) as cnt
            FROM question_responses qr
            JOIN students s ON qr.student_id = s.id
            WHERE s.establishment_id = stat_record.establishment_id
                AND qr.question_id = stat_record.question_id
                AND qr.academic_year = stat_record.academic_year
                AND qr.cycle = stat_record.cycle
                AND qr.response_value IS NOT NULL
            GROUP BY qr.response_value
        )
        SELECT 
            ARRAY[
                COALESCE(SUM(CASE WHEN response_value = 1 THEN cnt ELSE 0 END), 0)::integer,
                COALESCE(SUM(CASE WHEN response_value = 2 THEN cnt ELSE 0 END), 0)::integer,
                COALESCE(SUM(CASE WHEN response_value = 3 THEN cnt ELSE 0 END), 0)::integer,
                COALESCE(SUM(CASE WHEN response_value = 4 THEN cnt ELSE 0 END), 0)::integer,
                COALESCE(SUM(CASE WHEN response_value = 5 THEN cnt ELSE 0 END), 0)::integer
            ],
            COALESCE(SUM(cnt), 0)::integer
        INTO dist_array, response_count
        FROM response_data;
        
        -- Update the statistics record
        UPDATE question_statistics
        SET 
            distribution = dist_array,
            count = response_count,
            calculated_at = NOW()
        WHERE id = stat_record.id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Run the function to fix all statistics
SELECT calculate_distribution_for_stats();

-- Verify the fix worked
SELECT 
    'After Fix' as status,
    COUNT(*) as total_stats,
    COUNT(CASE WHEN distribution IS NOT NULL THEN 1 END) as with_distribution,
    COUNT(CASE WHEN count IS NOT NULL THEN 1 END) as with_count
FROM question_statistics
WHERE establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5';

-- Show sample of fixed data
SELECT 
    question_id,
    academic_year,
    cycle,
    mean,
    count,
    distribution
FROM question_statistics
WHERE establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5'
    AND question_id IN ('q5', 'q26', 'q14', 'q16')
ORDER BY question_id, academic_year, cycle
LIMIT 10;
