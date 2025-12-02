-- Check Alena Ramsey's data in Supabase
-- Email: aramsey@vespa.academy
-- Name: Alena Ramsey

-- 1. Check if student exists
SELECT 
    id,
    name,
    email,
    establishment_id,
    year_group,
    "group",
    created_at
FROM students
WHERE email = 'aramsey@vespa.academy';

-- 2. Check VESPA scores for ALL cycles
SELECT 
    cycle,
    vision,
    effort,
    systems,
    practice,
    attitude,
    overall,
    completion_date,
    academic_year,
    created_at
FROM vespa_scores
WHERE email = 'aramsey@vespa.academy'
ORDER BY cycle;

-- 3. Check question responses grouped by cycle
SELECT 
    cycle,
    COUNT(*) as response_count,
    MIN(created_at) as earliest_response,
    MAX(created_at) as latest_response
FROM question_responses
WHERE email = 'aramsey@vespa.academy'
GROUP BY cycle
ORDER BY cycle;

-- 4. Check student responses (reflections)
SELECT 
    cycle,
    LEFT(response_text, 100) as response_preview,
    submitted_at,
    created_at
FROM student_responses
WHERE email = 'aramsey@vespa.academy'
ORDER BY cycle;

-- 5. Check student goals
SELECT 
    cycle,
    LEFT(goal_text, 100) as goal_preview,
    goal_set_date,
    goal_due_date,
    created_at
FROM student_goals
WHERE email = 'aramsey@vespa.academy'
ORDER BY cycle;

-- 6. Check staff coaching notes
SELECT 
    cycle,
    LEFT(coaching_text, 100) as coaching_preview,
    coaching_date,
    staff_id,
    created_at
FROM staff_coaching_notes
WHERE email = 'aramsey@vespa.academy'
ORDER BY cycle;

-- 7. Get student_id from students table for further queries
SELECT id FROM students WHERE email = 'aramsey@vespa.academy';

-- Use this ID in the queries below (replace STUDENT_ID_HERE)

-- 8. Alternative query using student_id instead of email
-- (Some tables might use student_id instead of email)
/*
SELECT * FROM student_responses WHERE student_id = STUDENT_ID_HERE;
SELECT * FROM student_goals WHERE student_id = STUDENT_ID_HERE;
SELECT * FROM staff_coaching_notes WHERE student_id = STUDENT_ID_HERE;
*/

