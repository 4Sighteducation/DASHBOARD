-- Quick fix for the statistics procedure
-- Run this in Supabase SQL Editor

DROP FUNCTION IF EXISTS calculate_question_statistics_enhanced CASCADE;

CREATE OR REPLACE FUNCTION calculate_question_statistics_enhanced()
RETURNS void AS $$
BEGIN
    -- Log start
    RAISE NOTICE 'Starting comprehensive statistics calculation at %', NOW();
    
    -- Clear existing statistics for recalculation (with WHERE clause for Supabase)
    DELETE FROM question_statistics WHERE true;
    
    -- Calculate statistics for ALL establishments, ALL cycles, ALL academic years
    INSERT INTO question_statistics (
        establishment_id, 
        question_id, 
        cycle, 
        academic_year,
        mean,
        std_dev,
        calculated_at
    )
    SELECT 
        s.establishment_id,
        qr.question_id,
        qr.cycle,
        qr.academic_year,
        ROUND(AVG(qr.response_value)::numeric, 2) as mean,
        ROUND(COALESCE(STDDEV(qr.response_value)::numeric, 0), 2) as std_dev,
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

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION calculate_question_statistics_enhanced() TO authenticated;
