-- Check if we have VESPA scores data
SELECT COUNT(*) as total_vespa_scores FROM vespa_scores;

-- Check sample of VESPA scores
SELECT * FROM vespa_scores LIMIT 5;

-- Check if establishments have is_australian field
SELECT 
    COUNT(*) as total_establishments,
    COUNT(is_australian) as has_is_australian,
    SUM(CASE WHEN is_australian THEN 1 ELSE 0 END) as australian_schools
FROM establishments;

-- Check student-establishment join
SELECT COUNT(DISTINCT s.establishment_id) as schools_with_students
FROM students s
JOIN establishments e ON s.establishment_id = e.id;

-- Check vespa scores by cycle
SELECT 
    cycle,
    COUNT(*) as score_count,
    COUNT(DISTINCT student_id) as student_count
FROM vespa_scores
GROUP BY cycle
ORDER BY cycle;