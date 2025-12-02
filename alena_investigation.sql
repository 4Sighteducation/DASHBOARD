-- Alena Ramsey Data Investigation
-- Run each query separately in Supabase SQL editor

-- Query 1: Check scores for OLD student_id (August record)
SELECT 
    'OLD_ID' as label,
    cycle, 
    vision, 
    effort, 
    systems, 
    practice, 
    attitude, 
    completion_date
FROM vespa_scores
WHERE student_id = '6d7155c9-1f16-4333-b009-41db9a5faae6'
ORDER BY cycle;

-- Query 2: Check scores for NEW student_id (October record)
SELECT 
    'NEW_ID' as label,
    cycle, 
    vision, 
    effort, 
    systems, 
    practice, 
    attitude, 
    completion_date
FROM vespa_scores
WHERE student_id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
ORDER BY cycle;

-- Query 3: Check responses for OLD ID
SELECT 
    'OLD_ID' as label,
    cycle, 
    LEFT(response_text, 100) as response_preview
FROM student_responses
WHERE student_id = '6d7155c9-1f16-4333-b009-41db9a5faae6'
ORDER BY cycle;

-- Query 4: Check responses for NEW ID
SELECT 
    'NEW_ID' as label,
    cycle, 
    LEFT(response_text, 100) as response_preview
FROM student_responses
WHERE student_id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
ORDER BY cycle;

-- Query 5: Check goals for OLD ID
SELECT 
    'OLD_ID' as label,
    cycle, 
    LEFT(goal_text, 100) as goal_preview
FROM student_goals
WHERE student_id = '6d7155c9-1f16-4333-b009-41db9a5faae6'
ORDER BY cycle;

-- Query 6: Check goals for NEW ID
SELECT 
    'NEW_ID' as label,
    cycle, 
    LEFT(goal_text, 100) as goal_preview
FROM student_goals
WHERE student_id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
ORDER BY cycle;

-- SOLUTION: Once you identify which ID has the data, DELETE the empty duplicate:
-- DELETE FROM students WHERE id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda';
-- (Only run this after confirming which ID to keep!)

