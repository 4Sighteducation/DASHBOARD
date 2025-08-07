-- Investigation SQL Queries for Rochdale College Missing from comparative_metrics
-- Run these queries in Supabase SQL Editor to diagnose the issue

-- ============================================
-- 1. CHECK IF ROCHDALE COLLEGE EXISTS IN ESTABLISHMENTS
-- ============================================
SELECT 
    id,
    name,
    trust_name,
    created_at,
    updated_at
FROM establishments
WHERE LOWER(name) LIKE '%rochdale%'
   OR LOWER(name) LIKE '%college%rochdale%'
ORDER BY name;

-- ============================================
-- 2. GET ALL ESTABLISHMENTS (to see exact naming)
-- ============================================
SELECT 
    id,
    name,
    trust_name,
    (SELECT COUNT(*) FROM students s WHERE s.establishment_id = e.id) as student_count,
    (SELECT COUNT(*) FROM vespa_scores vs 
     JOIN students s ON vs.student_id = s.id 
     WHERE s.establishment_id = e.id) as vespa_score_count
FROM establishments e
ORDER BY name;

-- ============================================
-- 3. CHECK IF ROCHDALE HAS STUDENTS
-- ============================================
SELECT 
    e.name as establishment_name,
    COUNT(DISTINCT s.id) as student_count,
    COUNT(DISTINCT s.year_group) as year_groups,
    COUNT(DISTINCT s.faculty) as faculties
FROM establishments e
LEFT JOIN students s ON s.establishment_id = e.id
WHERE LOWER(e.name) LIKE '%rochdale%'
GROUP BY e.id, e.name;

-- ============================================
-- 4. CHECK IF ROCHDALE HAS VESPA SCORES
-- ============================================
SELECT 
    e.name as establishment_name,
    COUNT(DISTINCT vs.id) as vespa_score_count,
    COUNT(DISTINCT vs.cycle) as cycles_with_data,
    MIN(vs.cycle) as first_cycle,
    MAX(vs.cycle) as last_cycle,
    COUNT(DISTINCT vs.student_id) as students_with_scores
FROM establishments e
LEFT JOIN students s ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs ON vs.student_id = s.id
WHERE LOWER(e.name) LIKE '%rochdale%'
GROUP BY e.id, e.name;

-- ============================================
-- 5. CHECK WHAT'S IN THE MATERIALIZED VIEW
-- ============================================
-- First, check if the view exists and has data
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT establishment_id) as establishment_count,
    COUNT(DISTINCT establishment_name) as unique_establishment_names
FROM comparative_metrics;

-- ============================================
-- 6. LIST ALL ESTABLISHMENTS IN THE MATERIALIZED VIEW
-- ============================================
SELECT DISTINCT 
    establishment_id,
    establishment_name
FROM comparative_metrics
ORDER BY establishment_name;

-- ============================================
-- 7. CHECK MATERIALIZED VIEW REFRESH STATUS
-- ============================================
-- PostgreSQL doesn't store refresh timestamps directly, but we can check:
SELECT 
    schemaname,
    matviewname,
    matviewowner,
    hasindexes,
    ispopulated  -- This shows if the view has been populated
FROM pg_matviews
WHERE matviewname = 'comparative_metrics';

-- ============================================
-- 8. CHECK THE SOURCE DATA THAT SHOULD BE IN THE VIEW
-- ============================================
-- This recreates what the materialized view SHOULD contain for Rochdale
SELECT 
    e.id as establishment_id,
    e.name as establishment_name,
    s.id as student_id,
    s.year_group,
    s.faculty,
    s."group",
    vs.cycle,
    vs.academic_year,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id
WHERE LOWER(e.name) LIKE '%rochdale%'
LIMIT 10;

-- ============================================
-- 9. CHECK SYNC LOGS FOR RECENT UPDATES
-- ============================================
SELECT 
    id,
    sync_type,
    status,
    started_at,
    completed_at,
    metadata,
    EXTRACT(EPOCH FROM (completed_at - started_at))/60 as duration_minutes
FROM sync_logs
ORDER BY started_at DESC
LIMIT 5;

-- ============================================
-- 10. FORCE REFRESH THE MATERIALIZED VIEW (ADMIN ONLY)
-- ============================================
-- WARNING: This can take a while depending on data size
-- REFRESH MATERIALIZED VIEW comparative_metrics;

-- ============================================
-- 11. CHECK IF THERE'S A NAMING MISMATCH
-- ============================================
-- Sometimes establishments have slightly different names in different tables
SELECT 
    'establishments' as source_table,
    id,
    name
FROM establishments
WHERE LOWER(name) LIKE '%rochdale%'
    OR LOWER(name) LIKE '%college%'

UNION ALL

SELECT DISTINCT
    'comparative_metrics' as source_table,
    establishment_id as id,
    establishment_name as name
FROM comparative_metrics
WHERE LOWER(establishment_name) LIKE '%rochdale%'
    OR LOWER(establishment_name) LIKE '%college%';

-- ============================================
-- 12. GET DETAILED STATS FOR ALL ESTABLISHMENTS
-- ============================================
-- This helps identify if Rochdale is under a different name
SELECT 
    e.id,
    e.name,
    e.trust_name,
    COUNT(DISTINCT s.id) as total_students,
    COUNT(DISTINCT vs.id) as total_vespa_scores,
    COUNT(DISTINCT vs.cycle) as cycles_with_data,
    STRING_AGG(DISTINCT vs.cycle::text, ', ' ORDER BY vs.cycle::text) as cycles,
    MAX(vs.created_at) as last_score_added
FROM establishments e
LEFT JOIN students s ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs ON vs.student_id = s.id
GROUP BY e.id, e.name, e.trust_name
HAVING COUNT(DISTINCT s.id) > 0  -- Only show establishments with students
ORDER BY e.name;

-- ============================================
-- 13. CHECK QUESTION RESPONSES FOR ROCHDALE
-- ============================================
-- Sometimes schools have responses but no VESPA scores calculated
SELECT 
    e.name,
    COUNT(DISTINCT qr.id) as response_count,
    COUNT(DISTINCT qr.student_id) as students_with_responses,
    COUNT(DISTINCT qr.cycle) as cycles_with_responses,
    STRING_AGG(DISTINCT qr.cycle::text, ', ' ORDER BY qr.cycle::text) as cycles
FROM establishments e
LEFT JOIN students s ON s.establishment_id = e.id
LEFT JOIN question_responses qr ON qr.student_id = s.id
WHERE LOWER(e.name) LIKE '%rochdale%'
GROUP BY e.id, e.name;

-- ============================================
-- 14. MANUAL REFRESH OF MATERIALIZED VIEW (IF NEEDED)
-- ============================================
-- If you determine Rochdale has data but isn't in the view, run:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY comparative_metrics;
-- Note: CONCURRENTLY allows reads during refresh but requires a unique index

-- ============================================
-- 15. CHECK DATA FRESHNESS
-- ============================================
SELECT 
    'establishments' as table_name,
    MAX(created_at) as last_created,
    MAX(updated_at) as last_updated
FROM establishments
UNION ALL
SELECT 
    'students' as table_name,
    MAX(created_at) as last_created,
    MAX(updated_at) as last_updated
FROM students
UNION ALL
SELECT 
    'vespa_scores' as table_name,
    MAX(created_at) as last_created,
    MAX(updated_at) as last_updated
FROM vespa_scores
UNION ALL
SELECT 
    'question_responses' as table_name,
    MAX(created_at) as last_created,
    MAX(updated_at) as last_updated
FROM question_responses;
