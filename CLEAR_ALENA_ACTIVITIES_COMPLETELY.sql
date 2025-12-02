-- Clear Alena's activities from BOTH tables (for clean testing)

-- Check what she has first
SELECT 'activity_responses' as table_name, cycle_number, status, COUNT(*) as count
FROM activity_responses
WHERE student_email = 'aramsey@vespa.academy'
GROUP BY cycle_number, status
UNION ALL
SELECT 'student_activities' as table_name, cycle_number, status, COUNT(*) as count
FROM student_activities
WHERE student_email = 'aramsey@vespa.academy'
GROUP BY cycle_number, status
ORDER BY table_name, cycle_number;

-- Clear activity_responses (mark as removed, don't delete)
UPDATE activity_responses
SET status = 'removed', updated_at = NOW()
WHERE student_email = 'aramsey@vespa.academy'
  AND status != 'removed';

-- Clear student_activities (mark as removed, don't delete)
UPDATE student_activities
SET status = 'removed'
WHERE student_email = 'aramsey@vespa.academy'
  AND status != 'removed';

-- Verify cleared
SELECT 
  'Remaining active activities' as check_name,
  COUNT(*) as count
FROM activity_responses
WHERE student_email = 'aramsey@vespa.academy'
  AND status != 'removed';

SELECT 
  'Remaining in student_activities' as check_name,
  COUNT(*) as count
FROM student_activities
WHERE student_email = 'aramsey@vespa.academy'
  AND status != 'removed';

