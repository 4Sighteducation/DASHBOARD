-- Investigation SQL to understand academic year discrepancies

-- 1. Check distinct academic years in each table
SELECT 'vespa_scores' as table_name, academic_year, COUNT(*) as record_count
FROM vespa_scores
WHERE academic_year IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

SELECT 'question_statistics' as table_name, academic_year, COUNT(*) as record_count
FROM question_statistics
WHERE academic_year IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

SELECT 'school_statistics' as table_name, academic_year, COUNT(*) as record_count
FROM school_statistics
WHERE academic_year IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

SELECT 'national_statistics' as table_name, academic_year, COUNT(*) as record_count
FROM national_statistics
WHERE academic_year IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

SELECT 'national_question_statistics' as table_name, academic_year, COUNT(*) as record_count
FROM national_question_statistics
WHERE academic_year IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

-- 2. Check sample of vespa_scores with completion dates to verify calculation
SELECT 
    vs.id,
    vs.completion_date,
    vs.academic_year,
    vs.cycle,
    s.establishment_id,
    e.is_australian
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
WHERE vs.completion_date IS NOT NULL
LIMIT 10;

-- 3. Check school_statistics - what dates are being used?
SELECT 
    ss.establishment_id,
    ss.academic_year,
    ss.cycle,
    ss.element,
    ss.calculated_at,
    e.name as school_name
FROM school_statistics ss
JOIN establishments e ON ss.establishment_id = e.id
WHERE ss.academic_year = '2025-26'
LIMIT 10;

-- 4. Compare actual completion dates vs academic years marked
SELECT 
    academic_year,
    MIN(completion_date) as earliest_completion,
    MAX(completion_date) as latest_completion,
    COUNT(*) as record_count
FROM vespa_scores
WHERE completion_date IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

-- 5. Check if there are any completion dates that would legitimately be 2025-26
SELECT COUNT(*) as future_dates_count
FROM vespa_scores
WHERE completion_date >= '2025-08-01';

-- 6. Check the views
SELECT 'current_school_averages' as view_name, academic_year, COUNT(*) as record_count
FROM current_school_averages
GROUP BY academic_year;

SELECT 'qla_question_performance' as view_name, academic_year, COUNT(*) as record_count
FROM qla_question_performance
GROUP BY academic_year;