-- Fix Supabase Data Issues from Previous Sync Attempts

-- 1. Fix student_name JSON strings in student_vespa_progress view
-- First, let's check the issue
SELECT id, student_name 
FROM student_vespa_progress 
WHERE student_name LIKE '{%' 
LIMIT 5;

-- Since this is a VIEW, we need to fix the underlying students table
UPDATE students
SET name = 
  CASE 
    WHEN name LIKE '{"full":%' THEN 
      -- Extract the full name from JSON
      REPLACE(REPLACE(json_extract_path_text(name::json, 'full'), '"', ''), '\', '')
    WHEN name LIKE '{"first":%' THEN 
      -- Build name from first and last
      CONCAT(
        REPLACE(REPLACE(json_extract_path_text(name::json, 'first'), '"', ''), '\', ''),
        ' ',
        REPLACE(REPLACE(json_extract_path_text(name::json, 'last'), '"', ''), '\', '')
      )
    ELSE name
  END
WHERE name LIKE '{%';

-- 2. Clean up sync_logs table - remove old incomplete entries
-- These NULL fields are expected for interrupted syncs
DELETE FROM sync_logs 
WHERE status = 'started' 
AND completed_at IS NULL 
AND started_at < NOW() - INTERVAL '1 day';

-- 3. Identify and fix students with NULL values but have VESPA scores
-- First, let's see the issue
SELECT 
  s.id,
  s.email,
  s.name,
  s.establishment_id,
  COUNT(vs.id) as score_count
FROM students s
LEFT JOIN vespa_scores vs ON s.id = vs.student_id
WHERE (s.name IS NULL OR s.establishment_id IS NULL)
AND vs.id IS NOT NULL
GROUP BY s.id, s.email, s.name, s.establishment_id
ORDER BY score_count DESC;

-- 4. Remove duplicate students (keep the one with most data)
WITH duplicate_students AS (
  SELECT 
    email,
    COUNT(*) as count,
    array_agg(id ORDER BY 
      CASE WHEN name IS NOT NULL THEN 1 ELSE 2 END,
      CASE WHEN establishment_id IS NOT NULL THEN 1 ELSE 2 END,
      created_at DESC
    ) as ids
  FROM students
  WHERE email IS NOT NULL AND email != ''
  GROUP BY email
  HAVING COUNT(*) > 1
)
DELETE FROM students
WHERE id IN (
  SELECT unnest(ids[2:]) 
  FROM duplicate_students
);

-- 5. Check for orphaned VESPA scores (scores without valid students)
DELETE FROM vespa_scores
WHERE student_id NOT IN (SELECT id FROM students);

-- 6. Analysis query to understand NULL patterns
SELECT 
  'Students with NULL names' as issue,
  COUNT(*) as count
FROM students
WHERE name IS NULL
UNION ALL
SELECT 
  'Students with NULL establishment',
  COUNT(*)
FROM students
WHERE establishment_id IS NULL
UNION ALL
SELECT 
  'VESPA scores with NULL dates',
  COUNT(*)
FROM vespa_scores
WHERE completion_date IS NULL
UNION ALL
SELECT 
  'VESPA scores with future dates',
  COUNT(*)
FROM vespa_scores
WHERE completion_date > CURRENT_DATE
UNION ALL
SELECT 
  'Students with Cycle 3 but incomplete data',
  COUNT(DISTINCT s.id)
FROM students s
JOIN vespa_scores vs ON s.id = vs.student_id
WHERE vs.cycle = 3
AND (s.name IS NULL OR s.establishment_id IS NULL);

-- 7. Create a data quality report view
CREATE OR REPLACE VIEW data_quality_report AS
SELECT 
  -- Overall counts
  (SELECT COUNT(*) FROM establishments) as total_establishments,
  (SELECT COUNT(*) FROM students) as total_students,
  (SELECT COUNT(*) FROM vespa_scores) as total_vespa_scores,
  
  -- Quality issues
  (SELECT COUNT(*) FROM students WHERE name IS NULL) as students_missing_name,
  (SELECT COUNT(*) FROM students WHERE establishment_id IS NULL) as students_missing_school,
  (SELECT COUNT(*) FROM vespa_scores WHERE completion_date IS NULL) as scores_missing_date,
  (SELECT COUNT(*) FROM vespa_scores WHERE completion_date > CURRENT_DATE) as scores_future_date,
  
  -- Completion rates
  (SELECT COUNT(DISTINCT student_id) FROM vespa_scores WHERE cycle = 1) as students_with_cycle1,
  (SELECT COUNT(DISTINCT student_id) FROM vespa_scores WHERE cycle = 2) as students_with_cycle2,
  (SELECT COUNT(DISTINCT student_id) FROM vespa_scores WHERE cycle = 3) as students_with_cycle3,
  
  -- Last sync info
  (SELECT MAX(started_at) FROM sync_logs WHERE status = 'completed') as last_successful_sync,
  (SELECT COUNT(*) FROM sync_logs WHERE status = 'failed' AND started_at > NOW() - INTERVAL '24 hours') as recent_failures;

-- 8. Fix empty string dates that should be NULL
UPDATE vespa_scores
SET completion_date = NULL
WHERE completion_date = '';

-- 9. DELETE VESPA records where ALL scores are NULL (these shouldn't exist)
DELETE FROM vespa_scores
WHERE vision IS NULL 
AND effort IS NULL 
AND systems IS NULL 
AND practice IS NULL 
AND attitude IS NULL 
AND overall IS NULL;

-- 10. Count how many bogus records we're removing
SELECT COUNT(*) as bogus_records_count
FROM vespa_scores
WHERE vision IS NULL 
AND effort IS NULL 
AND systems IS NULL 
AND practice IS NULL 
AND attitude IS NULL 
AND overall IS NULL;

-- 11. View to check students with partial VESPA data
CREATE OR REPLACE VIEW students_partial_vespa AS
SELECT 
  s.id,
  s.email,
  s.name,
  e.name as establishment_name,
  COUNT(DISTINCT vs.cycle) as cycles_completed,
  array_agg(DISTINCT vs.cycle ORDER BY vs.cycle) as cycles,
  bool_or(vs.vision IS NULL) as has_null_vision,
  bool_or(vs.effort IS NULL) as has_null_effort,
  bool_or(vs.systems IS NULL) as has_null_systems,
  bool_or(vs.practice IS NULL) as has_null_practice,
  bool_or(vs.attitude IS NULL) as has_null_attitude
FROM students s
LEFT JOIN establishments e ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs ON s.id = vs.student_id
GROUP BY s.id, s.email, s.name, e.name
HAVING COUNT(vs.id) > 0
ORDER BY cycles_completed DESC, s.name;