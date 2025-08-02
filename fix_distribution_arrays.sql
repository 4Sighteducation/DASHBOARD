-- Fix the distribution array generation in the stored procedure
CREATE OR REPLACE FUNCTION calculate_all_statistics()
RETURNS void AS $$
BEGIN
    -- Clear existing statistics
    DELETE FROM school_statistics WHERE true;
    
    -- Insert new statistics with proper distribution arrays
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
        distribution,
        average  -- Populate this too since it exists
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
    distribution_calc AS (
        SELECT 
            establishment_id,
            cycle,
            academic_year,
            element,
            score_val,
            COUNT(*) as score_count
        FROM (
            SELECT 
                establishment_id,
                cycle,
                academic_year,
                element,
                ROUND(score)::INT as score_val
            FROM score_data
        ) rounded_scores
        GROUP BY establishment_id, cycle, academic_year, element, score_val
    ),
    aggregated_stats AS (
        SELECT 
            sd.establishment_id,
            sd.cycle,
            sd.academic_year,
            sd.element,
            AVG(sd.score) as mean,
            STDDEV_POP(sd.score) as std_dev,
            COUNT(*) as count,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sd.score) as percentile_25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sd.score) as percentile_50,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sd.score) as percentile_75,
            -- Build distribution array with proper length
            CASE 
                WHEN sd.element = 'overall' THEN
                    -- For overall: 11 elements (0-10)
                    ARRAY(
                        SELECT COALESCE(dc.score_count, 0)
                        FROM generate_series(0, 10) AS gs(val)
                        LEFT JOIN distribution_calc dc 
                            ON dc.establishment_id = sd.establishment_id 
                            AND dc.cycle = sd.cycle 
                            AND dc.academic_year = sd.academic_year 
                            AND dc.element = sd.element 
                            AND dc.score_val = gs.val
                        ORDER BY gs.val
                    )
                ELSE
                    -- For other elements: 7 elements (0-6)
                    ARRAY(
                        SELECT COALESCE(dc.score_count, 0)
                        FROM generate_series(0, 6) AS gs(val)
                        LEFT JOIN distribution_calc dc 
                            ON dc.establishment_id = sd.establishment_id 
                            AND dc.cycle = sd.cycle 
                            AND dc.academic_year = sd.academic_year 
                            AND dc.element = sd.element 
                            AND dc.score_val = gs.val
                        ORDER BY gs.val
                    )
            END as distribution
        FROM score_data sd
        GROUP BY sd.establishment_id, sd.cycle, sd.academic_year, sd.element
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
        distribution,
        ROUND(mean::numeric, 2) as average  -- Same as mean
    FROM aggregated_stats;
    
END;
$$ LANGUAGE plpgsql;