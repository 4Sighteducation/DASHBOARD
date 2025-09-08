-- Fix the statistics calculation to include distribution and count
-- This was working before but got lost in the migration!

DROP FUNCTION IF EXISTS calculate_question_statistics_enhanced CASCADE;

CREATE OR REPLACE FUNCTION calculate_question_statistics_enhanced()
RETURNS void AS $$
BEGIN
    -- Log start
    RAISE NOTICE 'Starting comprehensive statistics calculation with distributions at %', NOW();
    
    -- Clear existing statistics
    DELETE FROM question_statistics WHERE true;
    
    -- Calculate statistics WITH distribution arrays and counts
    INSERT INTO question_statistics (
        establishment_id,
        question_id,
        cycle,
        academic_year,
        mean,
        std_dev,
        count,
        distribution,
        calculated_at
    )
    SELECT 
        s.establishment_id,
        qr.question_id,
        qr.cycle,
        qr.academic_year,
        ROUND(AVG(qr.response_value)::numeric, 2) as mean,
        ROUND(COALESCE(STDDEV(qr.response_value)::numeric, 0), 2) as std_dev,
        COUNT(*)::integer as count,  -- THIS WAS MISSING!
        to_jsonb(ARRAY[
            COUNT(*) FILTER (WHERE qr.response_value = 1)::integer,
            COUNT(*) FILTER (WHERE qr.response_value = 2)::integer,
            COUNT(*) FILTER (WHERE qr.response_value = 3)::integer,
            COUNT(*) FILTER (WHERE qr.response_value = 4)::integer,
            COUNT(*) FILTER (WHERE qr.response_value = 5)::integer
        ]) as distribution,  -- THIS WAS MISSING!
        NOW() as calculated_at
    FROM question_responses qr
    JOIN students s ON qr.student_id = s.id
    WHERE qr.response_value > 0
      AND qr.academic_year IS NOT NULL
    GROUP BY s.establishment_id, qr.question_id, qr.cycle, qr.academic_year
    HAVING COUNT(*) > 0;
    
    -- Log completion
    RAISE NOTICE 'Statistics calculation completed. Rows inserted: %', 
        (SELECT COUNT(*) FROM question_statistics);
    
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION calculate_question_statistics_enhanced() TO authenticated;

-- Run the function to recalculate everything
SELECT calculate_question_statistics_enhanced();

-- Verify the fix
SELECT 
    'Statistics Check' as status,
    COUNT(*) as total_stats,
    COUNT(CASE WHEN distribution IS NOT NULL THEN 1 END) as with_distribution,
    COUNT(CASE WHEN count IS NOT NULL THEN 1 END) as with_count,
    COUNT(CASE WHEN distribution IS NOT NULL AND distribution::text != '[]' THEN 1 END) as with_valid_distribution
FROM question_statistics
WHERE establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5';

-- Show sample for insight questions
SELECT 
    question_id,
    academic_year,
    cycle,
    mean,
    count,
    distribution,
    CASE 
        WHEN distribution IS NOT NULL AND jsonb_array_length(distribution) >= 5 THEN
            ROUND(((distribution->3)::numeric + (distribution->4)::numeric) / count * 100, 1)
        ELSE 0
    END as agreement_percentage
FROM question_statistics
WHERE establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5'
    AND question_id IN ('q5', 'q26', 'q14', 'q16', 'q17', 'q9')
    AND academic_year = '2025/2026'
    AND cycle = 1
ORDER BY question_id;
