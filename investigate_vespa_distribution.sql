-- Investigate VESPA score distribution

-- 1. Overview: How many students have how many VESPA scores?
SELECT 
    score_count,
    COUNT(*) as student_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM students), 2) as percentage
FROM (
    SELECT 
        s.id,
        s.name,
        COUNT(v.id) as score_count
    FROM students s
    LEFT JOIN vespa_scores v ON s.id = v.student_id
    GROUP BY s.id, s.name
) student_scores
GROUP BY score_count
ORDER BY score_count;

-- 2. Distribution by cycle - which cycles have been completed?
SELECT 
    cycle,
    COUNT(DISTINCT student_id) as students_with_cycle,
    COUNT(*) as total_scores
FROM vespa_scores
GROUP BY cycle
ORDER BY cycle;

-- 3. Students with no VESPA scores at all
SELECT COUNT(*) as students_without_scores
FROM students s
WHERE NOT EXISTS (
    SELECT 1 FROM vespa_scores v WHERE v.student_id = s.id
);

-- 4. Sample of students with all 3 cycles completed
SELECT 
    s.name,
    s.email,
    e.name as establishment,
    COUNT(v.id) as cycles_completed
FROM students s
JOIN vespa_scores v ON s.id = v.student_id
LEFT JOIN establishments e ON s.establishment_id = e.id
GROUP BY s.id, s.name, s.email, e.name
HAVING COUNT(v.id) = 3
LIMIT 10;

-- 5. Distribution of scores per establishment
SELECT 
    e.name as establishment,
    COUNT(DISTINCT s.id) as total_students,
    COUNT(DISTINCT v.student_id) as students_with_scores,
    COUNT(v.id) as total_vespa_scores,
    ROUND(COUNT(v.id) * 1.0 / NULLIF(COUNT(DISTINCT s.id), 0), 2) as avg_scores_per_student
FROM establishments e
LEFT JOIN students s ON e.id = s.establishment_id
LEFT JOIN vespa_scores v ON s.id = v.student_id
WHERE e.status = 'Active'
GROUP BY e.id, e.name
HAVING COUNT(s.id) > 0
ORDER BY total_students DESC
LIMIT 20;

-- 6. Check if there are any orphaned VESPA scores (scores without valid students)
SELECT COUNT(*) as orphaned_scores
FROM vespa_scores v
WHERE NOT EXISTS (
    SELECT 1 FROM students s WHERE s.id = v.student_id
);

-- 7. Summary statistics
SELECT 
    (SELECT COUNT(*) FROM students) as total_students,
    (SELECT COUNT(DISTINCT student_id) FROM vespa_scores) as students_with_any_scores,
    (SELECT COUNT(*) FROM vespa_scores) as total_vespa_scores,
    ROUND((SELECT COUNT(*) FROM vespa_scores) * 1.0 / 
          NULLIF((SELECT COUNT(DISTINCT student_id) FROM vespa_scores), 0), 2) as avg_cycles_per_student_with_scores;