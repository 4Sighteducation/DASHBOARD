-- Check student counts and responses for large schools

-- First, get the establishment IDs for these schools
SELECT id, name 
FROM establishments 
WHERE name IN ('Rochdale Sixth Form College', 'Hartpury University', 'NPTC Group of Colleges');

-- Check total students for each school
SELECT 
    e.name,
    COUNT(DISTINCT s.id) as total_students,
    COUNT(DISTINCT CASE WHEN s.status != 'deleted' OR s.status IS NULL THEN s.id END) as active_students
FROM establishments e
JOIN students s ON s.establishment_id = e.id
WHERE e.name IN ('Rochdale Sixth Form College', 'Hartpury University', 'NPTC Group of Colleges')
GROUP BY e.name;

-- Check VESPA scores count by cycle
SELECT 
    e.name,
    vs.cycle,
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as students_with_scores,
    COUNT(*) as total_score_records
FROM establishments e
JOIN students s ON s.establishment_id = e.id
JOIN vespa_scores vs ON vs.student_id = s.id
WHERE e.name IN ('Rochdale Sixth Form College', 'Hartpury University', 'NPTC Group of Colleges')
GROUP BY e.name, vs.cycle, vs.academic_year
ORDER BY e.name, vs.cycle;

-- Check question responses count
SELECT 
    e.name,
    qr.cycle,
    COUNT(DISTINCT qr.student_id) as students_with_responses,
    COUNT(*) as total_responses
FROM establishments e
JOIN students s ON s.establishment_id = e.id
JOIN question_responses qr ON qr.student_id = s.id
WHERE e.name IN ('Rochdale Sixth Form College', 'Hartpury University', 'NPTC Group of Colleges')
GROUP BY e.name, qr.cycle
ORDER BY e.name, qr.cycle;

-- Check if there's a limit issue in the data
SELECT 
    e.name,
    COUNT(DISTINCT s.id) as student_count,
    STRING_AGG(DISTINCT s.status, ', ') as student_statuses
FROM establishments e
JOIN students s ON s.establishment_id = e.id
WHERE e.name IN ('Rochdale Sixth Form College', 'Hartpury University', 'NPTC Group of Colleges')
GROUP BY e.name;