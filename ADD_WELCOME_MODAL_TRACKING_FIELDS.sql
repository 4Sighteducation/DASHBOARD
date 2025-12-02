-- Add tracking fields for welcome modal (cross-device sync)
-- Run this in Supabase SQL Editor

-- Add 3 boolean fields to track if student has seen welcome modal for each cycle
ALTER TABLE vespa_students 
ADD COLUMN IF NOT EXISTS has_seen_welcome_cycle_1 BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS has_seen_welcome_cycle_2 BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS has_seen_welcome_cycle_3 BOOLEAN DEFAULT false;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_vespa_students_welcome_tracking 
ON vespa_students(email, has_seen_welcome_cycle_1, has_seen_welcome_cycle_2, has_seen_welcome_cycle_3);

-- Fix Alena's current_cycle to match her actual cycle from scores
UPDATE vespa_students
SET current_cycle = (latest_vespa_scores->>'cycle')::int
WHERE email = 'aramsey@vespa.academy'
  AND latest_vespa_scores->>'cycle' IS NOT NULL
  AND (latest_vespa_scores->>'cycle')::int != current_cycle;

-- Verify Alena's fix
SELECT 
  email,
  current_cycle,
  latest_vespa_scores->>'cycle' as scores_cycle,
  has_seen_welcome_cycle_1,
  has_seen_welcome_cycle_2,
  has_seen_welcome_cycle_3,
  total_activities_completed,
  total_points
FROM vespa_students
WHERE email = 'aramsey@vespa.academy';

-- Check for other students with cycle mismatch
SELECT 
  email,
  current_cycle,
  (latest_vespa_scores->>'cycle')::int as scores_cycle,
  latest_vespa_scores->>'vision' as vision_score
FROM vespa_students
WHERE latest_vespa_scores->>'cycle' IS NOT NULL
  AND (latest_vespa_scores->>'cycle')::int != current_cycle
LIMIT 10;

-- Optional: Fix ALL students with cycle mismatch
-- UPDATE vespa_students
-- SET current_cycle = (latest_vespa_scores->>'cycle')::int
-- WHERE latest_vespa_scores->>'cycle' IS NOT NULL
--   AND (latest_vespa_scores->>'cycle')::int != current_cycle;

COMMENT ON COLUMN vespa_students.has_seen_welcome_cycle_1 IS 'Tracks if student has seen welcome modal for Cycle 1 (cross-device sync)';
COMMENT ON COLUMN vespa_students.has_seen_welcome_cycle_2 IS 'Tracks if student has seen welcome modal for Cycle 2 (cross-device sync)';
COMMENT ON COLUMN vespa_students.has_seen_welcome_cycle_3 IS 'Tracks if student has seen welcome modal for Cycle 3 (cross-device sync)';

