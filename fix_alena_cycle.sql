-- Fix Alena's current_cycle to match her latest_vespa_scores
UPDATE vespa_students
SET current_cycle = 3
WHERE email = 'aramsey@vespa.academy'
  AND (latest_vespa_scores->>'cycle')::int = 3;

-- Verify the fix
SELECT 
  email,
  current_cycle,
  latest_vespa_scores->>'cycle' as scores_cycle,
  latest_vespa_scores->>'vision' as vision,
  latest_vespa_scores->>'effort' as effort
FROM vespa_students
WHERE email = 'aramsey@vespa.academy';
