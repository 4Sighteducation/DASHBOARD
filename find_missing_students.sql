-- Diagnostic: Find the missing ~250 students from 2024/2025

-- 1. How many TOTAL unique students have VESPA scores for each year?
SELECT 
    '1. Total VESPA scores by year' as check_type,
    academic_year,
    COUNT(DISTINCT student_id) as unique_students,
    COUNT(DISTINCT student_email) as unique_emails,
    COUNT(*) as total_scores
FROM vespa_scores
WHERE student_email LIKE '%@whitchurchhs.wales'
GROUP BY academic_year
ORDER BY academic_year;

-- 2. How many of these students still exist in the students table?
SELECT 
    '2. Students with VESPA who still exist' as check_type,
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as total_with_vespa,
    COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN vs.student_id END) as still_exist,
    COUNT(DISTINCT CASE WHEN s.id IS NULL THEN vs.student_id END) as deleted
FROM vespa_scores vs
LEFT JOIN students s ON vs.student_id = s.id
WHERE vs.student_email LIKE '%@whitchurchhs.wales'
GROUP BY vs.academic_year
ORDER BY vs.academic_year;

-- 3. Find the specific missing students (deleted Year 13s from 2024/2025)
WITH missing_students AS (
    SELECT DISTINCT
        vs.student_id,
        vs.student_email,
        vs.student_name,
        vs.academic_year
    FROM vespa_scores vs
    LEFT JOIN students s ON vs.student_id = s.id
    WHERE vs.student_email LIKE '%@whitchurchhs.wales'
    AND vs.academic_year = '2024/2025'
    AND s.id IS NULL  -- Student no longer exists
)
SELECT 
    '3. Missing students from 2024/2025' as check_type,
    COUNT(*) as missing_count
FROM missing_students;

-- 4. The problem: student_enrollments has a FOREIGN KEY to students table!
-- This means we CAN'T create enrollments for deleted students!
-- Let's check the constraint:
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    confrelid::regclass as references_table
FROM pg_constraint
WHERE conrelid = 'student_enrollments'::regclass
AND contype = 'f';  -- Foreign key constraints

-- 5. SOLUTION: We need to either:
-- A. Recreate the deleted students in the students table, OR
-- B. Remove the foreign key constraint, OR  
-- C. Create a different tracking mechanism

-- Let's go with Option A: Recreate deleted students
-- First, let's see what data we have for them in VESPA scores

WITH deleted_students AS (
    SELECT DISTINCT
        vs.student_id,
        vs.student_email,
        vs.student_name,
        -- Extract establishment from email domain
        '1a327b33-d924-453c-803e-82671f94a242'::UUID as establishment_id
    FROM vespa_scores vs
    LEFT JOIN students s ON vs.student_id = s.id
    WHERE vs.student_email LIKE '%@whitchurchhs.wales'
    AND vs.academic_year = '2024/2025'
    AND s.id IS NULL  -- Deleted students
)
SELECT COUNT(*) as students_to_recreate FROM deleted_students;

-- 6. RECREATE the deleted students (so we can track their history)
INSERT INTO students (
    id,  -- Use their original ID from VESPA scores
    email,
    name,
    establishment_id,
    year_group,
    academic_year,
    knack_id,
    created_at,
    updated_at
)
SELECT DISTINCT
    vs.student_id as id,
    vs.student_email as email,
    vs.student_name as name,
    '1a327b33-d924-453c-803e-82671f94a242'::UUID as establishment_id,
    'Year 13 (Graduated 2025)' as year_group,
    '2024/2025' as academic_year,  -- Their last academic year
    'GRADUATED_' || SUBSTRING(vs.student_id::TEXT, 1, 8) as knack_id,
    MIN(vs.created_at) as created_at,
    NOW() as updated_at
FROM vespa_scores vs
LEFT JOIN students s ON vs.student_id = s.id
WHERE vs.student_email LIKE '%@whitchurchhs.wales'
AND vs.academic_year = '2024/2025'
AND s.id IS NULL  -- Only recreate deleted students
GROUP BY vs.student_id, vs.student_email, vs.student_name
ON CONFLICT (id) DO NOTHING;  -- Skip if they already exist

-- 7. Now recreate enrollments for ALL Whitchurch students
DELETE FROM student_enrollments
WHERE student_id IN (
    SELECT id FROM students 
    WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
);

INSERT INTO student_enrollments (
    student_id,
    academic_year,
    knack_id,
    year_group,
    enrollment_status
)
SELECT DISTINCT
    vs.student_id,
    vs.academic_year,
    s.knack_id,
    CASE 
        WHEN vs.academic_year = '2024/2025' THEN
            CASE 
                WHEN s.year_group LIKE '%Graduated%' THEN 'Year 13'
                WHEN s.year_group = 'Year 13' THEN 'Year 12'
                ELSE s.year_group
            END
        ELSE s.year_group
    END as year_group,
    CASE 
        WHEN vs.academic_year = '2025/2026' THEN 'active'
        WHEN s.year_group LIKE '%Graduated%' THEN 'graduated'
        ELSE 'completed'
    END
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id  -- Now they all exist!
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
ON CONFLICT (student_id, academic_year) DO UPDATE SET
    year_group = EXCLUDED.year_group,
    enrollment_status = EXCLUDED.enrollment_status,
    updated_at = NOW();

-- 8. Final verification
SELECT 
    academic_year,
    COUNT(DISTINCT student_id) as student_count,
    STRING_AGG(DISTINCT enrollment_status, ', ') as statuses
FROM student_enrollments
WHERE student_id IN (
    SELECT id FROM students 
    WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
)
GROUP BY academic_year
ORDER BY academic_year;

-- Should now show:
-- 2024/2025: ~440 students (189 current + ~250 graduated)
-- 2025/2026: 207 students (current Year 13s)


