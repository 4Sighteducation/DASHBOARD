-- Check how many students have NULL establishment_id
SELECT 
    COUNT(*) as total_students,
    COUNT(establishment_id) as with_establishment,
    COUNT(*) - COUNT(establishment_id) as missing_establishment
FROM students;

-- Check if we can match students to establishments via email domain
-- This is a backup strategy if the Knack connection is broken
SELECT 
    s.id,
    s.email,
    s.name,
    SUBSTRING(s.email FROM '@(.+)$') as email_domain,
    e.name as possible_establishment
FROM students s
LEFT JOIN establishments e ON e.name ILIKE '%' || SUBSTRING(s.email FROM '@(.+)$') || '%'
WHERE s.establishment_id IS NULL
LIMIT 20;

-- See sample of students with NULL establishment_id
SELECT 
    id, 
    knack_id, 
    email, 
    name, 
    year_group,
    establishment_id
FROM students 
WHERE establishment_id IS NULL 
LIMIT 10;

-- Check if there's a pattern in the knack_ids or other fields
-- that might help us understand the issue
SELECT 
    year_group,
    course,
    faculty,
    COUNT(*) as count,
    COUNT(establishment_id) as has_establishment
FROM students
GROUP BY year_group, course, faculty
ORDER BY count DESC
LIMIT 20;