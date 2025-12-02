-- Find which student_id has Alena Ramsey's VESPA data
-- We have 2 duplicate student records:
-- ID 1: 6d7155c9-1f16-4333-b009-41db9a5faae6 (August 2025)
-- ID 2: fbd8d15c-cb92-45cf-ac31-ee18e23bcbda (October 2025)

-- Check scores for BOTH IDs
SELECT 'OLD ID' as record_label, cycle, vision, effort, systems, practice, attitude, completion_date
FROM vespa_scores
WHERE student_id = '6d7155c9-1f16-4333-b009-41db9a5faae6'
ORDER BY cycle

UNION ALL

SELECT 'NEW ID' as record_label, cycle, vision, effort, systems, practice, attitude, completion_date
FROM vespa_scores
WHERE student_id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
ORDER BY cycle;

-- Check responses for BOTH IDs
SELECT 'OLD ID' as record_label, cycle, LEFT(response_text, 50) as response_preview
FROM student_responses
WHERE student_id = '6d7155c9-1f16-4333-b009-41db9a5faae6'
ORDER BY cycle

UNION ALL

SELECT 'NEW ID' as record_label, cycle, LEFT(response_text, 50) as response_preview
FROM student_responses
WHERE student_id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
ORDER BY cycle;

-- Check goals for BOTH IDs
SELECT 'OLD ID' as record_label, cycle, LEFT(goal_text, 50) as goal_preview
FROM student_goals
WHERE student_id = '6d7155c9-1f16-4333-b009-41db9a5faae6'
ORDER BY cycle

UNION ALL

SELECT 'NEW ID' as record_label, cycle, LEFT(goal_text, 50) as goal_preview
FROM student_goals
WHERE student_id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
ORDER BY cycle;

-- SOLUTION: Delete the duplicate (newer) record and keep the old one with data
-- DELETE FROM students WHERE id = 'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda';

