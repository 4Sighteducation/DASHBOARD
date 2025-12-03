-- Backfill Achievements for Students with Completed Activities
-- Awards achievements based on completion count

-- Achievement Requirements:
-- first_activity: 1 completion (5 points)
-- five_complete: 5 completions (25 points)
-- ten_complete: 10 completions (50 points)
-- fifteen_complete: 15 completions (75 points)
-- twenty_complete: 20 completions (100 points)

-- STEP 1: Preview which achievements students should have
WITH student_completion_counts AS (
  SELECT 
    student_email,
    COUNT(*) as completed_count
  FROM activity_responses
  WHERE status = 'completed'
  GROUP BY student_email
),
achievements_earned AS (
  SELECT 
    scc.student_email,
    scc.completed_count,
    CASE 
      WHEN scc.completed_count >= 20 THEN '20+ completions: twenty_complete (100 pts)'
      WHEN scc.completed_count >= 15 THEN '15+ completions: fifteen_complete (75 pts)'
      WHEN scc.completed_count >= 10 THEN '10+ completions: ten_complete (50 pts)'
      WHEN scc.completed_count >= 5 THEN '5+ completions: five_complete (25 pts)'
      WHEN scc.completed_count >= 1 THEN '1+ completion: first_activity (5 pts)'
      ELSE 'No achievements yet'
    END as highest_achievement,
    COALESCE(
      (SELECT COUNT(*) FROM student_achievements sa WHERE sa.student_email = scc.student_email),
      0
    ) as current_achievements
  FROM student_completion_counts scc
)
SELECT * FROM achievements_earned
WHERE current_achievements = 0 AND completed_count > 0
ORDER BY completed_count DESC;

-- STEP 2: Award achievements (UNCOMMENT AND RUN AFTER REVIEWING STEP 1)
/*
-- Award first_activity achievement (1 completion, 5 points)
INSERT INTO student_achievements (
  student_email, achievement_type, achievement_name, achievement_description, 
  icon_emoji, points_value, date_earned, is_pinned
)
SELECT DISTINCT
  ar.student_email,
  'first_activity',
  'First Steps! 🎯',
  'Complete your first activity - every journey begins with a single step!',
  '🎯',
  5,
  MIN(ar.completed_at),
  false
FROM activity_responses ar
WHERE ar.status = 'completed'
  AND NOT EXISTS (
    SELECT 1 FROM student_achievements sa 
    WHERE sa.student_email = ar.student_email 
      AND sa.achievement_type = 'first_activity'
  )
GROUP BY ar.student_email
HAVING COUNT(*) >= 1;

-- Award five_complete achievement (5 completions, 25 points)
INSERT INTO student_achievements (
  student_email, achievement_type, achievement_name, achievement_description, 
  icon_emoji, points_value, date_earned, is_pinned
)
SELECT DISTINCT
  ar.student_email,
  'five_complete',
  'Getting Going! 🚀',
  'Completed 5 activities - you''re building momentum!',
  '🚀',
  25,
  MAX(ar.completed_at),
  false
FROM activity_responses ar
WHERE ar.status = 'completed'
  AND NOT EXISTS (
    SELECT 1 FROM student_achievements sa 
    WHERE sa.student_email = ar.student_email 
      AND sa.achievement_type = 'five_complete'
  )
GROUP BY ar.student_email
HAVING COUNT(*) >= 5;

-- Award ten_complete achievement (10 completions, 50 points)
INSERT INTO student_achievements (
  student_email, achievement_type, achievement_name, achievement_description, 
  icon_emoji, points_value, date_earned, is_pinned
)
SELECT DISTINCT
  ar.student_email,
  'ten_complete',
  'On Fire! 🔥',
  'Completed 10 activities - you''re unstoppable!',
  '🔥',
  50,
  MAX(ar.completed_at),
  false
FROM activity_responses ar
WHERE ar.status = 'completed'
  AND NOT EXISTS (
    SELECT 1 FROM student_achievements sa 
    WHERE sa.student_email = ar.student_email 
      AND sa.achievement_type = 'ten_complete'
  )
GROUP BY ar.student_email
HAVING COUNT(*) >= 10;

-- Update total_achievements count in vespa_students
UPDATE vespa_students vs
SET total_achievements = (
  SELECT COUNT(*) 
  FROM student_achievements sa 
  WHERE sa.student_email = vs.email
);

-- Update total_points to include achievement bonus points
UPDATE vespa_students vs
SET total_points = vs.total_points + (
  SELECT COALESCE(SUM(points_value), 0)
  FROM student_achievements sa 
  WHERE sa.student_email = vs.email
);
*/

-- STEP 3: Verify achievements awarded correctly
/*
SELECT 
  vs.email,
  vs.total_activities_completed,
  vs.total_achievements,
  vs.total_points,
  (SELECT json_agg(achievement_type) FROM student_achievements sa WHERE sa.student_email = vs.email) as achievements
FROM vespa_students vs
WHERE vs.total_activities_completed > 0
ORDER BY vs.total_activities_completed DESC
LIMIT 20;
*/

