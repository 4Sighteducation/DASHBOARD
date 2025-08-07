-- ============================================
-- ROCHDALE SIXTH FORM COLLEGE DIAGNOSTIC & FIX
-- ============================================

-- 1. CHECK IF ROCHDALE SIXTH FORM COLLEGE EXISTS IN ESTABLISHMENTS
SELECT 
    id,
    name,
    trust_name,
    created_at,
    updated_at
FROM establishments
WHERE LOWER(name) LIKE '%rochdale%'
   OR LOWER(name) LIKE '%sixth form%'
ORDER BY name;

-- 2. IF FOUND, CHECK ITS DATA (replace ID with actual ID from above)
-- Get the exact ID first, then run:
WITH rochdale AS (
    SELECT id, name 
    FROM establishments 
    WHERE LOWER(name) LIKE '%rochdale%'
    LIMIT 1
)
SELECT 
    e.id,
    e.name,
    COUNT(DISTINCT s.id) as student_count,
    COUNT(DISTINCT vs.id) as vespa_score_count,
    COUNT(DISTINCT vs.cycle) as cycles_with_data,
    STRING_AGG(DISTINCT vs.cycle::text, ', ' ORDER BY vs.cycle::text) as cycles,
    COUNT(DISTINCT qr.id) as question_responses
FROM establishments e
LEFT JOIN students s ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs ON vs.student_id = s.id
LEFT JOIN question_responses qr ON qr.student_id = s.id
WHERE e.id IN (SELECT id FROM rochdale)
GROUP BY e.id, e.name;

-- 3. CHECK IF IT'S IN THE MATERIALIZED VIEW
SELECT COUNT(*) as occurrences
FROM comparative_metrics
WHERE LOWER(establishment_name) LIKE '%rochdale%';

-- 4. GET LIST OF ALL ESTABLISHMENTS IN THE VIEW (sample)
SELECT DISTINCT 
    establishment_id,
    establishment_name,
    COUNT(*) as records
FROM comparative_metrics
GROUP BY establishment_id, establishment_name
ORDER BY establishment_name
LIMIT 50;

-- 5. IF ROCHDALE HAS DATA BUT ISN'T IN VIEW, CHECK WHY
-- This query recreates what SHOULD be in the materialized view for Rochdale
WITH rochdale_est AS (
    SELECT id FROM establishments WHERE LOWER(name) LIKE '%rochdale%'
)
SELECT 
    e.id as establishment_id,
    e.name as establishment_name,
    COUNT(DISTINCT s.id) as students_that_should_be_in_view,
    COUNT(DISTINCT vs.id) as scores_that_should_be_in_view
FROM establishments e
JOIN students s ON s.establishment_id = e.id
JOIN vespa_scores vs ON vs.student_id = s.id
WHERE e.id IN (SELECT id FROM rochdale_est)
GROUP BY e.id, e.name;

-- ============================================
-- FIX: REFRESH THE MATERIALIZED VIEW
-- ============================================
-- If Rochdale exists with data but isn't in the view, run this:
REFRESH MATERIALIZED VIEW comparative_metrics;

-- Note: This will take 1-2 minutes to complete
-- After refresh, verify Rochdale is now included:
SELECT 
    establishment_name,
    COUNT(*) as record_count
FROM comparative_metrics
WHERE LOWER(establishment_name) LIKE '%rochdale%'
GROUP BY establishment_name;

-- ============================================
-- ALTERNATIVE: CHECK VIEW DEFINITION
-- ============================================
-- See how the materialized view is defined
SELECT definition 
FROM pg_matviews 
WHERE matviewname = 'comparative_metrics';

-- ============================================
-- NUCLEAR OPTION: RECREATE THE VIEW
-- ============================================
-- Only if the view is corrupted or missing
-- First check if it exists:
SELECT 
    schemaname,
    matviewname,
    ispopulated
FROM pg_matviews
WHERE matviewname = 'comparative_metrics';

-- If it doesn't exist or is not populated, you need to run:
-- (Get the CREATE MATERIALIZED VIEW statement from prepare_comparative_analytics.sql)

-- ============================================
-- CHECK RECENT SYNC STATUS
-- ============================================
SELECT 
    id,
    sync_type,
    status,
    started_at,
    completed_at,
    metadata
FROM sync_logs
WHERE status = 'completed'
ORDER BY completed_at DESC
LIMIT 5;

-- Check if materialized views were refreshed in recent syncs
SELECT 
    id,
    started_at,
    completed_at,
    metadata->>'operations' as operations
FROM sync_logs
WHERE metadata::text LIKE '%refresh_materialized%'
   OR metadata::text LIKE '%comparative_metrics%'
ORDER BY completed_at DESC
LIMIT 5;
