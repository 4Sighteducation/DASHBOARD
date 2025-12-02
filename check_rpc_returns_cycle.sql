-- Check what get_connected_students_for_staff RPC returns for current_cycle

-- First, check what vespa_students has
SELECT 
  email,
  current_cycle,
  current_level,
  full_name,
  latest_vespa_scores->>'cycle' as scores_cycle
FROM vespa_students
WHERE email = 'aramsey@vespa.academy';

-- Check staff_student_connections
SELECT 
  student_email,
  staff_email,
  staff_role,
  vs.current_cycle
FROM staff_student_connections ssc
LEFT JOIN vespa_students vs ON vs.email = ssc.student_email
WHERE ssc.student_email = 'aramsey@vespa.academy'
  AND ssc.staff_email = 'tut7@vespa.academy';

-- Try calling the RPC directly (simulated)
-- Check what fields get_connected_students_for_staff returns
SELECT routine_definition 
FROM information_schema.routines
WHERE routine_name = 'get_connected_students_for_staff';
