-- Create function to calculate all statistics
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
    GROUP BY s.establishment_id, v.cycle, academic_year, elem.element;
    
    -- Also calculate question-level statistics if needed
    INSERT INTO question_statistics (
        establishment_id,
        question_id,
        cycle,
        academic_year,
        mean_response,
        response_count
    )
    SELECT 
        s.establishment_id,
        qr.question_id,
        qr.cycle,
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
        AVG(qr.response_value) as mean_response,
        COUNT(*) as response_count
    FROM question_responses qr
    JOIN students s ON qr.student_id = s.id
    JOIN establishments e ON s.establishment_id = e.id
    GROUP BY s.establishment_id, qr.question_id, qr.cycle, academic_year;
    
END;
$$ LANGUAGE plpgsql;