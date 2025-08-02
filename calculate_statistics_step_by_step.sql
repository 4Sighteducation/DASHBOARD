-- Step 1: Clear existing school statistics
DELETE FROM school_statistics WHERE true;

-- Step 2: Calculate VESPA element statistics
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
WITH score_data AS (
    SELECT 
        s.establishment_id,
        v.cycle,
        e.is_australian,
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
    CROSS JOIN (
        VALUES ('vision'), ('effort'), ('systems'), ('practice'), ('attitude'), ('overall')
    ) AS elem(element)
)
SELECT 
    establishment_id,
    cycle,
    CASE 
        WHEN is_australian AND EXTRACT(MONTH FROM CURRENT_DATE) >= 7 
            THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
        WHEN is_australian 
            THEN (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
        WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 
            THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
        ELSE 
            (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
    END as academic_year,
    element,
    AVG(score) as mean,
    COUNT(*) as count,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY score) as percentile_25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY score) as percentile_50,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY score) as percentile_75
FROM score_data
WHERE score IS NOT NULL
GROUP BY establishment_id, cycle, is_australian, element;

-- Check results
SELECT 
    COUNT(DISTINCT establishment_id) as schools,
    COUNT(DISTINCT cycle) as cycles,
    COUNT(DISTINCT element) as elements,
    COUNT(*) as total_rows
FROM school_statistics;

-- Step 3: Clear existing question statistics
DELETE FROM question_statistics WHERE true;

-- Step 4: Calculate question-level statistics
INSERT INTO question_statistics (
    establishment_id,
    question_id,
    cycle,
    academic_year,
    mean_response,
    response_count
)
WITH response_data AS (
    SELECT 
        s.establishment_id,
        qr.question_id,
        qr.cycle,
        e.is_australian,
        qr.response_value
    FROM question_responses qr
    JOIN students s ON qr.student_id = s.id
    JOIN establishments e ON s.establishment_id = e.id
    WHERE qr.response_value IS NOT NULL
)
SELECT 
    establishment_id,
    question_id,
    cycle,
    CASE 
        WHEN is_australian AND EXTRACT(MONTH FROM CURRENT_DATE) >= 7 
            THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
        WHEN is_australian 
            THEN (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
        WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 
            THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
        ELSE 
            (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
    END as academic_year,
    AVG(response_value) as mean_response,
    COUNT(*) as response_count
FROM response_data
GROUP BY establishment_id, question_id, cycle, is_australian;

-- Check question statistics results
SELECT 
    COUNT(DISTINCT establishment_id) as schools,
    COUNT(DISTINCT question_id) as questions,
    COUNT(DISTINCT cycle) as cycles,
    COUNT(*) as total_rows
FROM question_statistics;