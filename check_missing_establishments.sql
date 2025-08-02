-- Find which establishment knack_ids are referenced by students but don't exist in establishments table
-- This will help identify missing establishments

-- First, let's see a sample of Year 14 students from object_10 (vespa_scores)
SELECT DISTINCT
    vs.establishment_knack_id,
    COUNT(*) as student_count,
    array_agg(DISTINCT s.year_group) as year_groups
FROM vespa_scores vs
JOIN students s ON s.knack_id = vs.student_knack_id
WHERE vs.establishment_knack_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM establishments e 
        WHERE e.knack_id = vs.establishment_knack_id
    )
GROUP BY vs.establishment_knack_id
ORDER BY student_count DESC;

-- Check if Year 14 students specifically have missing establishments
SELECT 
    s.year_group,
    COUNT(DISTINCT s.id) as total_students,
    COUNT(DISTINCT s.establishment_id) as with_establishment,
    COUNT(DISTINCT vs.establishment_knack_id) as vespa_est_refs,
    COUNT(DISTINCT CASE 
        WHEN vs.establishment_knack_id IS NOT NULL 
        AND NOT EXISTS (SELECT 1 FROM establishments e WHERE e.knack_id = vs.establishment_knack_id) 
        THEN vs.establishment_knack_id 
    END) as missing_establishments
FROM students s
LEFT JOIN vespa_scores vs ON s.knack_id = vs.student_knack_id
WHERE s.year_group IN ('14', 'Year 14', 'Yr 14')
GROUP BY s.year_group;

-- Show sample Year 14 students with their vespa establishment references
SELECT 
    s.id,
    s.name,
    s.email,
    s.year_group,
    s.establishment_id as current_est_id,
    vs.establishment_knack_id as vespa_est_knack_id,
    e.name as establishment_name
FROM students s
JOIN vespa_scores vs ON s.knack_id = vs.student_knack_id
LEFT JOIN establishments e ON e.knack_id = vs.establishment_knack_id
WHERE s.year_group = '14'
LIMIT 10;