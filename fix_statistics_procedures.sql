-- Fix the school statistics procedure to use correct column names

-- First, let's update the existing procedure
CREATE OR REPLACE FUNCTION calculate_all_statistics()
RETURNS void AS $$
BEGIN
    -- Clear existing statistics
    DELETE FROM school_statistics WHERE true;
    
    -- Insert new statistics for each establishment, cycle, element, and academic year
    INSERT INTO school_statistics (
        establishment_id,
        cycle,
        academic_year,
        element,
        mean,
        count,
        percentile_25,
        percentile_50,
        percentile_75
    )
    SELECT 
        s.establishment_id,
        v.cycle,
        CASE 
            WHEN e.is_australian AND EXTRACT(MONTH FROM CURRENT_DATE) >= 7 
                THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
            WHEN e.is_australian 
                THEN (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
            WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 
                THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
            ELSE 
                (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
        END as academic_year,
        elem.element,
        AVG(
            CASE elem.element
                WHEN 'vision' THEN v.vision
                WHEN 'effort' THEN v.effort
                WHEN 'systems' THEN v.systems
                WHEN 'practice' THEN v.practice
                WHEN 'attitude' THEN v.attitude
                WHEN 'overall' THEN v.overall
            END
        ) as mean,
        COUNT(*) as count,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY 
            CASE elem.element
                WHEN 'vision' THEN v.vision
                WHEN 'effort' THEN v.effort
                WHEN 'systems' THEN v.systems
                WHEN 'practice' THEN v.practice
                WHEN 'attitude' THEN v.attitude
                WHEN 'overall' THEN v.overall
            END
        ) as percentile_25,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY 
            CASE elem.element
                WHEN 'vision' THEN v.vision
                WHEN 'effort' THEN v.effort
                WHEN 'systems' THEN v.systems
                WHEN 'practice' THEN v.practice
                WHEN 'attitude' THEN v.attitude
                WHEN 'overall' THEN v.overall
            END
        ) as percentile_50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY 
            CASE elem.element
                WHEN 'vision' THEN v.vision
                WHEN 'effort' THEN v.effort
                WHEN 'systems' THEN v.systems
                WHEN 'practice' THEN v.practice
                WHEN 'attitude' THEN v.attitude
                WHEN 'overall' THEN v.overall
            END
        ) as percentile_75
    FROM vespa_scores v
    JOIN students s ON v.student_id = s.id
    JOIN establishments e ON s.establishment_id = e.id
    CROSS JOIN (
        VALUES ('vision'), ('effort'), ('systems'), ('practice'), ('attitude'), ('overall')
    ) AS elem(element)
    WHERE 
        CASE elem.element
            WHEN 'vision' THEN v.vision
            WHEN 'effort' THEN v.effort
            WHEN 'systems' THEN v.systems
            WHEN 'practice' THEN v.practice
            WHEN 'attitude' THEN v.attitude
            WHEN 'overall' THEN v.overall
        END IS NOT NULL
    GROUP BY s.establishment_id, v.cycle, e.is_australian, elem.element;
    
    -- Clear existing question statistics (remove the old approach)
    DELETE FROM question_statistics WHERE true;
    
    -- Call the enhanced question statistics function
    PERFORM calculate_question_statistics_enhanced();
    
END;
$$ LANGUAGE plpgsql;

-- Fix the RPC function return type issue
DROP FUNCTION IF EXISTS get_qla_top_bottom_questions(UUID, INTEGER, VARCHAR);

CREATE OR REPLACE FUNCTION get_qla_top_bottom_questions(
    p_establishment_id UUID,
    p_cycle INTEGER,
    p_academic_year VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    question_id VARCHAR(50),  -- Changed to match the table definition
    mean DECIMAL(4,2),
    std_dev DECIMAL(4,2),
    count INTEGER,
    mode INTEGER,
    distribution JSONB,
    performance_category TEXT,  -- Changed from VARCHAR to TEXT
    rank_high_to_low BIGINT,   -- Changed from INTEGER to BIGINT (ROW_NUMBER returns BIGINT)
    national_mean DECIMAL(4,2),
    diff_from_national DECIMAL(4,2),
    national_comparison TEXT    -- Changed from VARCHAR to TEXT
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