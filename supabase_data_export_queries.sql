-- Supabase Data Export Queries for Specific Schools
-- Schools:
-- - Tonyrefail Community School (53e70907-bd30-46fb-b870-e4d4a9c1d06b)
-- - Whitchurch High School (1a327b33-d924-453c-803e-82671f94a242)
-- - Ysgol Garth Olwg (65f4eb79-6f08-4797-83ae-c09b8ae3c194)
-- - Llanishen High School (027ede5d-3384-419e-8390-c86d81cc08ab)

-- ========================================================================
-- QUERY 1: VESPA SCORES DATA (Cycles 1 & 2)
-- ========================================================================
-- This query retrieves all VESPA scores for cycles 1 and 2 for the specified schools

SELECT 
    -- School Information
    e.id as establishment_id,
    e.name as school_name,
    
    -- Student Information
    s.id as student_id,
    s.name as student_name,
    s.email as student_email,
    s.year_group,
    s.course,
    s.faculty,
    
    -- VESPA Scores
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date,
    vs.academic_year,
    vs.created_at as score_created_at
    
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
INNER JOIN establishments e ON s.establishment_id = e.id
WHERE 
    e.id IN (
        '53e70907-bd30-46fb-b870-e4d4a9c1d06b', -- Tonyrefail Community School
        '1a327b33-d924-453c-803e-82671f94a242', -- Whitchurch High School
        '65f4eb79-6f08-4797-83ae-c09b8ae3c194', -- Ysgol Garth Olwg
        '027ede5d-3384-419e-8390-c86d81cc08ab'  -- Llanishen High School
    )
    AND vs.cycle IN (1, 2)
ORDER BY 
    e.name, 
    vs.cycle, 
    s.year_group, 
    s.name;

-- ========================================================================
-- QUERY 2: QUESTION RESPONSES DATA (Cycles 1 & 2)
-- ========================================================================
-- This query retrieves all individual question responses for cycles 1 and 2

SELECT 
    -- School Information
    e.id as establishment_id,
    e.name as school_name,
    
    -- Student Information
    s.id as student_id,
    s.name as student_name,
    s.email as student_email,
    s.year_group,
    s.course,
    s.faculty,
    
    -- Question Response Data
    qr.cycle,
    qr.question_id,
    q.question_text,
    q.vespa_category,
    qr.response_value,
    qr.created_at as response_created_at
    
FROM question_responses qr
INNER JOIN students s ON qr.student_id = s.id
INNER JOIN establishments e ON s.establishment_id = e.id
LEFT JOIN questions q ON qr.question_id = q.question_id
WHERE 
    e.id IN (
        '53e70907-bd30-46fb-b870-e4d4a9c1d06b', -- Tonyrefail Community School
        '1a327b33-d924-453c-803e-82671f94a242', -- Whitchurch High School
        '65f4eb79-6f08-4797-83ae-c09b8ae3c194', -- Ysgol Garth Olwg
        '027ede5d-3384-419e-8390-c86d81cc08ab'  -- Llanishen High School
    )
    AND qr.cycle IN (1, 2)
ORDER BY 
    e.name, 
    qr.cycle, 
    s.year_group, 
    s.name,
    q.question_order;

-- ========================================================================
-- QUERY 3: COMBINED SUMMARY VIEW
-- ========================================================================
-- This query provides a summary of data availability for each school

SELECT 
    e.name as school_name,
    e.id as establishment_id,
    COUNT(DISTINCT s.id) as total_students,
    COUNT(DISTINCT CASE WHEN vs.cycle = 1 THEN s.id END) as students_with_cycle1_scores,
    COUNT(DISTINCT CASE WHEN vs.cycle = 2 THEN s.id END) as students_with_cycle2_scores,
    COUNT(DISTINCT CASE WHEN qr.cycle = 1 THEN s.id END) as students_with_cycle1_responses,
    COUNT(DISTINCT CASE WHEN qr.cycle = 2 THEN s.id END) as students_with_cycle2_responses
FROM establishments e
INNER JOIN students s ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs ON vs.student_id = s.id AND vs.cycle IN (1, 2)
LEFT JOIN question_responses qr ON qr.student_id = s.id AND qr.cycle IN (1, 2)
WHERE 
    e.id IN (
        '53e70907-bd30-46fb-b870-e4d4a9c1d06b', -- Tonyrefail Community School
        '1a327b33-d924-453c-803e-82671f94a242', -- Whitchurch High School
        '65f4eb79-6f08-4797-83ae-c09b8ae3c194', -- Ysgol Garth Olwg
        '027ede5d-3384-419e-8390-c86d81cc08ab'  -- Llanishen High School
    )
GROUP BY e.name, e.id
ORDER BY e.name;

-- ========================================================================
-- QUERY 4: DETAILED STUDENT-LEVEL SUMMARY
-- ========================================================================
-- This query provides a pivot-style view with both scores and key questions in one row per student/cycle

SELECT 
    e.name as school_name,
    s.name as student_name,
    s.email as student_email,
    s.year_group,
    vs.cycle,
    vs.completion_date,
    
    -- VESPA Scores
    vs.vision as vespa_vision,
    vs.effort as vespa_effort,
    vs.systems as vespa_systems,
    vs.practice as vespa_practice,
    vs.attitude as vespa_attitude,
    vs.overall as vespa_overall,
    
    -- Sample of Question Responses (you can add more as needed)
    MAX(CASE WHEN qr.question_id = 'q1' THEN qr.response_value END) as q1_response,
    MAX(CASE WHEN qr.question_id = 'q2' THEN qr.response_value END) as q2_response,
    MAX(CASE WHEN qr.question_id = 'q3' THEN qr.response_value END) as q3_response,
    MAX(CASE WHEN qr.question_id = 'q4' THEN qr.response_value END) as q4_response,
    MAX(CASE WHEN qr.question_id = 'q5' THEN qr.response_value END) as q5_response,
    
    -- Count of total questions answered
    COUNT(DISTINCT qr.question_id) as total_questions_answered
    
FROM students s
INNER JOIN establishments e ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs ON vs.student_id = s.id
LEFT JOIN question_responses qr ON qr.student_id = s.id AND qr.cycle = vs.cycle
WHERE 
    e.id IN (
        '53e70907-bd30-46fb-b870-e4d4a9c1d06b', -- Tonyrefail Community School
        '1a327b33-d924-453c-803e-82671f94a242', -- Whitchurch High School
        '65f4eb79-6f08-4797-83ae-c09b8ae3c194', -- Ysgol Garth Olwg
        '027ede5d-3384-419e-8390-c86d81cc08ab'  -- Llanishen High School
    )
    AND vs.cycle IN (1, 2)
GROUP BY 
    e.name, s.name, s.email, s.year_group, 
    vs.cycle, vs.completion_date, vs.vision, vs.effort, 
    vs.systems, vs.practice, vs.attitude, vs.overall
ORDER BY 
    e.name, vs.cycle, s.year_group, s.name;

-- ========================================================================
-- HOW TO EXPORT TO CSV FROM SUPABASE
-- ========================================================================
/*
Method 1: Using Supabase Dashboard (Easiest)
1. Log into your Supabase project dashboard
2. Go to the SQL Editor
3. Copy and run one of the queries above
4. Click the "Download CSV" button in the results panel

Method 2: Using PostgreSQL Client (pgAdmin, DBeaver, etc.)
1. Connect to your Supabase database using the connection string
2. Run the query
3. Export results to CSV using the client's export feature

Method 3: Using PSQL Command Line
1. Connect to your database:
   psql "postgresql://[user]:[password]@[host]:[port]/[database]"

2. Run the query with CSV output:
   \copy (SELECT ... [paste query here]) TO 'output.csv' WITH CSV HEADER

Method 4: Using Python Script (if you prefer automation)
See the Python script below for automated export
*/
