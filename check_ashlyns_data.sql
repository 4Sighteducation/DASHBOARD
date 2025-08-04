-- Check if Ashlyns School has any data in school_statistics
SELECT 
    establishment_id,
    cycle,
    academic_year,
    element,
    mean,
    count,
    calculated_at
FROM school_statistics
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
ORDER BY cycle, element;

-- Check if there's any question_statistics data for Ashlyns
SELECT 
    COUNT(*) as total_questions,
    cycle,
    academic_year
FROM question_statistics
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
GROUP BY cycle, academic_year;

-- Check if there are any students for Ashlyns
SELECT 
    COUNT(*) as student_count,
    COUNT(DISTINCT year_group) as year_groups,
    COUNT(DISTINCT course) as courses
FROM students
WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
  AND (status IS NULL OR status != 'deleted');

-- Check vespa_scores for Ashlyns students
SELECT 
    COUNT(*) as score_count,
    cycle,
    academic_year
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
GROUP BY cycle, academic_year;

-- Check if there are any student comments
SELECT 
    COUNT(*) as comment_count,
    cycle,
    comment_type
FROM student_comments sc
JOIN students s ON sc.student_id = s.id
WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec'
GROUP BY cycle, comment_type;