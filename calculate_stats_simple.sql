-- Simple statistics calculation without stored procedure
-- Run this directly in Supabase SQL editor

-- Clear existing statistics
DELETE FROM school_statistics WHERE true;

-- Calculate and insert statistics
INSERT INTO school_statistics (
    establishment_id,
    cycle,
    academic_year,
    element,
    mean,
    count
)
SELECT 
    s.establishment_id,
    v.cycle,
    '2024/2025' as academic_year,  -- Adjust as needed
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
    COUNT(*) as count
FROM vespa_scores v
JOIN students s ON v.student_id = s.id
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
GROUP BY s.establishment_id, v.cycle, elem.element;

-- Check results
SELECT COUNT(*) as total_stats FROM school_statistics;