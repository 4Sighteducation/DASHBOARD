-- Fix the calculate_all_statistics stored procedure to include std_dev and distribution
CREATE OR REPLACE FUNCTION calculate_all_statistics()
RETURNS void AS $$
BEGIN
    -- Clear existing statistics
    DELETE FROM school_statistics WHERE true;
    
    -- Insert new statistics with std_dev and distribution
    INSERT INTO school_statistics (
        establishment_id,
        cycle,
        academic_year,
        element,
        mean,
        std_dev,
        count,
        percentile_25,
        percentile_50,
        percentile_75,
        distribution
    )
    WITH score_data AS (
        SELECT 
            s.establishment_id,
            v.cycle,
            CASE 
                WHEN e.is_australian THEN TO_CHAR(CURRENT_DATE, 'YYYY')
                WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 8 THEN 
                    TO_CHAR(CURRENT_DATE, 'YYYY') || '-' || TO_CHAR(EXTRACT(YEAR FROM CURRENT_DATE) + 1, 'YY')
                ELSE 
                    TO_CHAR(EXTRACT(YEAR FROM CURRENT_DATE) - 1, 'YYYY') || '-' || TO_CHAR(CURRENT_DATE, 'YY')
            END as academic_year,
            elem.element,
            CASE elem.element
                WHEN 'vision' THEN v.vision
                WHEN 'effort' THEN v.effort
                WHEN 'systems' THEN v.systems
                WHEN 'practice' THEN v.practice
                WHEN 'attitude' THEN v.attitude
                WHEN 'overall' THEN v.overall
            END as score
        FROM vespa_scores v
        JOIN students s ON v.student_id = s.id
        JOIN establishments e ON s.establishment_id = e.id
        CROSS JOIN LATERAL (
            VALUES ('vision'), ('effort'), ('systems'), ('practice'), ('attitude'), ('overall')
        ) elem(element)
        WHERE 
            CASE elem.element
                WHEN 'vision' THEN v.vision
                WHEN 'effort' THEN v.effort
                WHEN 'systems' THEN v.systems
                WHEN 'practice' THEN v.practice
                WHEN 'attitude' THEN v.attitude
                WHEN 'overall' THEN v.overall
            END IS NOT NULL
    ),
    aggregated_stats AS (
        SELECT 
            establishment_id,
            cycle,
            academic_year,
            element,
            AVG(score) as mean,
            STDDEV_POP(score) as std_dev,
            COUNT(*) as count,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY score) as percentile_25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY score) as percentile_50,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY score) as percentile_75,
            -- Create distribution array
            ARRAY_AGG(
                JSONB_BUILD_OBJECT(
                    'score', ROUND(score)::INT,
                    'count', 1
                )
            ) as raw_distribution
        FROM score_data
        GROUP BY establishment_id, cycle, academic_year, element
    )
    SELECT 
        establishment_id,
        cycle,
        academic_year,
        element,
        ROUND(mean::numeric, 2) as mean,
        ROUND(std_dev::numeric, 2) as std_dev,
        count,
        ROUND(percentile_25::numeric, 2) as percentile_25,
        ROUND(percentile_50::numeric, 2) as percentile_50,
        ROUND(percentile_75::numeric, 2) as percentile_75,
        -- Build distribution JSON array
        (
            SELECT JSONB_AGG(dist_count)
            FROM (
                SELECT 
                    score_val,
                    COUNT(*) as count
                FROM (
                    SELECT (elem->>'score')::INT as score_val
                    FROM unnest(raw_distribution) elem
                ) scores
                WHERE score_val BETWEEN 0 AND CASE 
                    WHEN element = 'overall' THEN 10 
                    ELSE 6 
                END
                GROUP BY score_val
                ORDER BY score_val
            ) dist
        ) as distribution
    FROM aggregated_stats;
    
END;
$$ LANGUAGE plpgsql;