-- Check all Penglais School students for duplicate cycle issues in Supabase
-- This will show which students have multiple cycle records when they should only have 1

-- First, get Penglais establishment ID
WITH penglais_est AS (
  SELECT id, name
  FROM establishments
  WHERE name ILIKE '%Penglais%'
  LIMIT 1
),

-- Get all students from Penglais
penglais_students AS (
  SELECT 
    s.id,
    s.name,
    s.email,
    s.knack_id
  FROM students s
  JOIN penglais_est e ON s.establishment_id = e.id
),

-- Count cycle records per student
cycle_counts AS (
  SELECT 
    ps.name,
    ps.email,
    ps.knack_id,
    COUNT(DISTINCT vs.cycle) as num_cycles,
    STRING_AGG(DISTINCT vs.cycle::text, ', ' ORDER BY vs.cycle::text) as cycles_list,
    COUNT(DISTINCT vs.cycle) FILTER (WHERE vs.vision IS NOT NULL OR vs.effort IS NOT NULL) as cycles_with_scores,
    COUNT(DISTINCT vs.cycle) FILTER (WHERE vs.vision IS NULL AND vs.effort IS NULL AND vs.systems IS NULL AND vs.practice IS NULL AND vs.attitude IS NULL) as empty_cycles
  FROM penglais_students ps
  LEFT JOIN vespa_scores vs ON vs.student_id = ps.id
  GROUP BY ps.name, ps.email, ps.knack_id
)

-- Show students with issues
SELECT 
  name,
  email,
  num_cycles as total_cycles,
  cycles_with_scores as cycles_with_data,
  empty_cycles as empty_placeholder_cycles,
  cycles_list as cycle_numbers,
  CASE 
    WHEN cycles_with_scores = 1 AND empty_cycles > 0 THEN 'HAS DUPLICATES'
    WHEN cycles_with_scores > 1 THEN 'MULTIPLE COMPLETIONS'
    WHEN cycles_with_scores = 1 THEN 'SINGLE CYCLE OK'
    ELSE 'NO DATA'
  END as status
FROM cycle_counts
ORDER BY 
  CASE 
    WHEN cycles_with_scores = 1 AND empty_cycles > 0 THEN 1
    WHEN cycles_with_scores > 1 THEN 2
    WHEN cycles_with_scores = 1 THEN 3
    ELSE 4
  END,
  name;
