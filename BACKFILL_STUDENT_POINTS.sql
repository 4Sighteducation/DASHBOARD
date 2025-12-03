-- Backfill Student Points and Activity Counts
-- Calculates points for students based on completed activities

-- STEP 1: Preview what will be updated (DRY RUN)
WITH student_stats AS (
  SELECT 
    ar.student_email,
    COUNT(DISTINCT ar.id) as completed_count,
    SUM(
      CASE 
        WHEN a.level = 'Level 3' THEN 15
        ELSE 10
      END
    ) as calculated_points
  FROM activity_responses ar
  JOIN activities a ON a.id = ar.activity_id
  WHERE ar.status = 'completed'
  GROUP BY ar.student_email
)
SELECT 
  ss.student_email,
  vs.total_activities_completed as current_count,
  ss.completed_count as correct_count,
  vs.total_points as current_points,
  ss.calculated_points as correct_points,
  (ss.completed_count - COALESCE(vs.total_activities_completed, 0)) as count_diff,
  (ss.calculated_points - COALESCE(vs.total_points, 0)) as points_diff
FROM student_stats ss
LEFT JOIN vespa_students vs ON vs.email = ss.student_email
WHERE 
  COALESCE(vs.total_activities_completed, 0) != ss.completed_count
  OR COALESCE(vs.total_points, 0) != ss.calculated_points
ORDER BY ss.student_email;

-- STEP 2: Actual update (UNCOMMENT AND RUN AFTER REVIEWING STEP 1)
/*
WITH student_stats AS (
  SELECT 
    ar.student_email,
    COUNT(DISTINCT ar.id) as completed_count,
    SUM(
      CASE 
        WHEN a.level = 'Level 3' THEN 15
        ELSE 10
      END
    ) as calculated_points
  FROM activity_responses ar
  JOIN activities a ON a.id = ar.activity_id
  WHERE ar.status = 'completed'
  GROUP BY ar.student_email
)
UPDATE vespa_students vs
SET 
  total_activities_completed = ss.completed_count,
  total_points = ss.calculated_points,
  total_achievements = (SELECT COUNT(*) FROM student_achievements WHERE student_email = vs.email)
FROM student_stats ss
WHERE vs.email = ss.student_email;
*/

-- STEP 3: Verify (should show all correct now)
/*
WITH student_stats AS (
  SELECT 
    ar.student_email,
    COUNT(DISTINCT ar.id) as completed_count,
    SUM(
      CASE 
        WHEN a.level = 'Level 3' THEN 15
        ELSE 10
      END
    ) as calculated_points
  FROM activity_responses ar
  JOIN activities a ON a.id = ar.activity_id
  WHERE ar.status = 'completed'
  GROUP BY ar.student_email
)
SELECT 
  ss.student_email,
  vs.total_activities_completed,
  ss.completed_count,
  vs.total_points,
  ss.calculated_points,
  CASE 
    WHEN vs.total_activities_completed = ss.completed_count 
     AND vs.total_points = ss.calculated_points 
    THEN '✅ Correct' 
    ELSE '❌ Mismatch' 
  END as status
FROM student_stats ss
LEFT JOIN vespa_students vs ON vs.email = ss.student_email
ORDER BY status DESC, ss.student_email
LIMIT 50;
*/

