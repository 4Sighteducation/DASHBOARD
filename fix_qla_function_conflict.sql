-- Fix the function conflict by dropping the old version first

-- Drop the existing function
DROP FUNCTION IF EXISTS get_qla_top_bottom_questions(UUID, INTEGER, VARCHAR);

-- Now recreate with the correct signature
CREATE OR REPLACE FUNCTION get_qla_top_bottom_questions(
    p_establishment_id UUID,
    p_cycle INTEGER,
    p_academic_year VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    question_id VARCHAR(50),
    mean DECIMAL(4,2),
    std_dev DECIMAL(4,2),
    count INTEGER,
    mode INTEGER,
    distribution JSONB,
    performance_category TEXT,
    rank_high_to_low BIGINT,
    national_mean DECIMAL(4,2),
    diff_from_national DECIMAL(4,2),
    national_comparison TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.question_id::VARCHAR(50),
        q.mean,
        q.std_dev,
        q.count,
        q.mode,
        q.distribution,
        q.performance_category::TEXT,
        q.rank_high_to_low,
        q.national_mean,
        q.diff_from_national,
        q.national_comparison::TEXT
    FROM qla_question_performance q
    WHERE q.establishment_id = p_establishment_id
    AND q.cycle = p_cycle
    AND (p_academic_year IS NULL OR q.academic_year = p_academic_year)
    AND q.performance_category IN ('TOP_5', 'BOTTOM_5')
    ORDER BY q.rank_high_to_low;
END;
$$ LANGUAGE plpgsql;

-- Also check if the view exists
DO $$
BEGIN
    -- Check if the view exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.views 
        WHERE table_schema = 'public' 
        AND table_name = 'qla_question_performance'
    ) THEN
        RAISE NOTICE 'View qla_question_performance does not exist. Please run create_qla_optimized_views.sql';
    ELSE
        RAISE NOTICE 'View qla_question_performance exists';
    END IF;
END $$;