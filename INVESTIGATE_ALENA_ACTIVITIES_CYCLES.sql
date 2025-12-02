-- ========================================
-- DIAGNOSTIC SQL: Alena's Activities & Cycles
-- ========================================

-- 1. CHECK ALENA'S CURRENT STATE
-- What cycle is she on, what scores does she have?
SELECT 
  email,
  current_cycle,
  latest_vespa_scores->>'cycle' as scores_cycle,
  latest_vespa_scores->>'vision' as vision,
  latest_vespa_scores->>'effort' as effort,
  latest_vespa_scores->>'systems' as systems,
  latest_vespa_scores->>'practice' as practice,
  latest_vespa_scores->>'attitude' as attitude,
  latest_vespa_scores->>'completion_date' as completed_date,
  total_activities_completed,
  total_points,
  has_seen_welcome_cycle_1,
  has_seen_welcome_cycle_2,
  has_seen_welcome_cycle_3
FROM vespa_students
WHERE email = 'aramsey@vespa.academy';


-- 2. COUNT ACTIVITIES BY CYCLE AND STATUS (activity_responses)
-- This is what the student app queries
SELECT 
  'activity_responses' as table_name,
  cycle_number,
  status,
  COUNT(*) as count
FROM activity_responses
WHERE student_email = 'aramsey@vespa.academy'
GROUP BY cycle_number, status
ORDER BY cycle_number, status;


-- 3. COUNT ACTIVITIES BY CYCLE AND STATUS (student_activities)
-- This might be what staff RPC queries
SELECT 
  'student_activities' as table_name,
  cycle_number,
  status,
  COUNT(*) as count
FROM student_activities
WHERE student_email = 'aramsey@vespa.academy'
GROUP BY cycle_number, status
ORDER BY cycle_number, status;


-- 4. DETAILED VIEW: What activities does Alena actually have?
-- Show first 10 from each table
SELECT 
  'activity_responses' as source_table,
  ar.id,
  ar.activity_id,
  a.name as activity_name,
  ar.cycle_number,
  ar.status,
  ar.selected_via,
  ar.started_at,
  ar.completed_at,
  ar.points_earned
FROM activity_responses ar
LEFT JOIN activities a ON ar.activity_id = a.id
WHERE ar.student_email = 'aramsey@vespa.academy'
ORDER BY ar.cycle_number, ar.started_at DESC
LIMIT 10;


-- 5. CHECK STUDENT_ACTIVITIES TABLE
SELECT 
  'student_activities' as source_table,
  sa.id,
  sa.activity_id,
  a.name as activity_name,
  sa.cycle_number,
  sa.status,
  sa.assigned_by,
  sa.assigned_at
FROM student_activities sa
LEFT JOIN activities a ON sa.activity_id = a.id
WHERE sa.student_email = 'aramsey@vespa.academy'
ORDER BY sa.cycle_number, sa.assigned_at DESC
LIMIT 10;


-- 6. FIND ACTIVE (NOT REMOVED) ACTIVITIES
-- What would the API actually return?
SELECT 
  cycle_number,
  COUNT(*) as active_count
FROM activity_responses
WHERE student_email = 'aramsey@vespa.academy'
  AND status != 'removed'
GROUP BY cycle_number;

-- Same for student_activities
SELECT 
  cycle_number,
  COUNT(*) as active_count
FROM student_activities
WHERE student_email = 'aramsey@vespa.academy'
  AND status != 'removed'
GROUP BY cycle_number;


-- 7. CHECK IF RPC EXISTS
-- Does get_student_activity_responses function exist?
SELECT 
  routine_name,
  routine_type,
  routine_definition
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'get_student_activity_responses';


-- 8. SIMULATE RPC CALL (See what staff dashboard would get)
-- This is roughly what the RPC does
SELECT 
  ar.*,
  a.name as activity_name,
  a.vespa_category as activity_category,
  a.level as activity_level,
  a.time_minutes as activity_time_minutes
FROM activity_responses ar
LEFT JOIN activities a ON ar.activity_id = a.id
LEFT JOIN staff_student_connections ssc 
  ON ssc.student_email = ar.student_email
WHERE ar.student_email = 'aramsey@vespa.academy'
  AND ssc.staff_email = 'tut7@vespa.academy'
  AND ar.status != 'removed'
ORDER BY ar.cycle_number, ar.started_at DESC;


-- 9. CHECK FOR ORPHANED RECORDS
-- Are there student_activities without matching activity_responses?
SELECT 
  sa.cycle_number,
  sa.activity_id,
  a.name,
  sa.status as sa_status,
  ar.status as ar_status,
  CASE 
    WHEN ar.id IS NULL THEN 'ORPHANED - No activity_response!'
    WHEN sa.status != ar.status THEN 'STATUS MISMATCH!'
    ELSE 'OK'
  END as issue
FROM student_activities sa
LEFT JOIN activity_responses ar 
  ON ar.student_email = sa.student_email 
  AND ar.activity_id = sa.activity_id
  AND ar.cycle_number = sa.cycle_number
LEFT JOIN activities a ON sa.activity_id = a.id
WHERE sa.student_email = 'aramsey@vespa.academy'
ORDER BY sa.cycle_number;


-- 10. SUMMARY: What's the actual state?
SELECT 
  'Summary' as report,
  current_cycle,
  (SELECT COUNT(*) FROM activity_responses WHERE student_email = 'aramsey@vespa.academy' AND status != 'removed') as active_responses,
  (SELECT COUNT(*) FROM student_activities WHERE student_email = 'aramsey@vespa.academy' AND status != 'removed') as active_assignments,
  (SELECT COUNT(*) FROM activity_responses WHERE student_email = 'aramsey@vespa.academy' AND status = 'removed') as removed_responses,
  (SELECT COUNT(*) FROM student_activities WHERE student_email = 'aramsey@vespa.academy' AND status = 'removed') as removed_assignments
FROM vespa_students
WHERE email = 'aramsey@vespa.academy';

