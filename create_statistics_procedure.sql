-- Fix for calculating statistics for ALL schools and ALL cycles
-- This ensures the dashboard shows data for all academic years and cycles

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS calculate_question_statistics_enhanced CASCADE;

-- Create comprehensive statistics calculation function
CREATE OR REPLACE FUNCTION calculate_question_statistics_enhanced()
RETURNS void AS $$
BEGIN
    -- Log start
    RAISE NOTICE 'Starting comprehensive statistics calculation at %', NOW();
    
    -- Get current academic year
    DECLARE current_year TEXT;
    BEGIN
        SELECT DISTINCT academic_year INTO current_year
        FROM question_responses
        WHERE academic_year IS NOT NULL
        ORDER BY academic_year DESC
        LIMIT 1;
        
        IF current_year IS NULL THEN
            current_year := '2025/2026';
        END IF;
    END;
    
    -- Clear existing statistics for recalculation
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

-- Create function to get comment fields from question_responses
-- (Since we don't have a separate student_comments table yet)
CREATE OR REPLACE FUNCTION get_student_comments(
    p_establishment_id UUID,
    p_academic_year TEXT,
    p_cycle INT
)
RETURNS TABLE(
    student_id UUID,
    comment_text TEXT,
    cycle INT
) AS $$
BEGIN
    -- For now, return empty result since comments aren't being synced
    -- This prevents API errors while we implement proper comment syncing
    RETURN QUERY
    SELECT 
        NULL::UUID as student_id,
        ''::TEXT as comment_text,
        0::INT as cycle
    WHERE FALSE;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION calculate_question_statistics_enhanced() TO authenticated;
GRANT EXECUTE ON FUNCTION get_student_comments(UUID, TEXT, INT) TO authenticated;
