-- ==========================================
-- INVESTIGATION: VESPA Scores for Activities App
-- ==========================================
-- Date: Dec 2, 2025
-- Purpose: Understand current state of VESPA scores data for Activities student page

-- ==========================================
-- 1. Check vespa_scores table structure
-- ==========================================
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'vespa_scores'
ORDER BY ordinal_position;

-- ==========================================
-- 2. Check vespa_students table structure  
-- ==========================================
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'vespa_students'
ORDER BY ordinal_position;

-- ==========================================
-- 3. Check how many scores exist in vespa_scores
-- ==========================================
SELECT 
    COUNT(*) as total_scores,
    COUNT(DISTINCT student_email) as unique_students_with_scores,
    COUNT(DISTINCT student_id) as unique_student_ids,
    MIN(completion_date) as oldest_score,
    MAX(completion_date) as newest_score
FROM vespa_scores;

-- ==========================================
-- 4. Check score distribution by cycle
-- ==========================================
SELECT 
    cycle,
    academic_year,
    COUNT(*) as score_count,
    COUNT(DISTINCT student_email) as unique_students,
    AVG(overall) as avg_overall_score
FROM vespa_scores
WHERE student_email IS NOT NULL
GROUP BY cycle, academic_year
ORDER BY academic_year DESC, cycle;

-- ==========================================
-- 5. Check vespa_students cache status
-- ==========================================
SELECT 
    COUNT(*) as total_students,
    COUNT(latest_vespa_scores) as students_with_cached_scores,
    COUNT(*) - COUNT(latest_vespa_scores) as students_missing_cache
FROM vespa_students;

-- ==========================================
-- 6. Sample: Check what cached scores look like
-- ==========================================
SELECT 
    email,
    latest_vespa_scores,
    current_level,
    updated_at
FROM vespa_students
WHERE latest_vespa_scores IS NOT NULL
LIMIT 5;

-- ==========================================
-- 7. Find students with scores but NO cache
-- ==========================================
SELECT 
    vs.student_email,
    COUNT(DISTINCT vs.cycle) as cycles_completed,
    MAX(vs.completion_date) as latest_completion,
    vst.latest_vespa_scores as cached_data
FROM vespa_scores vs
LEFT JOIN vespa_students vst ON vs.student_email = vst.email
WHERE vs.student_email IS NOT NULL
  AND vst.latest_vespa_scores IS NULL
GROUP BY vs.student_email, vst.latest_vespa_scores
LIMIT 20;

-- ==========================================
-- 8. Check if RPC function exists
-- ==========================================
SELECT 
    proname as function_name,
    pg_get_function_arguments(oid) as arguments,
    prosrc as source_preview
FROM pg_proc
WHERE proname LIKE '%sync_latest_vespa%'
  OR proname LIKE '%vespa_students%';

-- ==========================================
-- 9. Check Cash's specific data (test student)
-- ==========================================
SELECT 
    'vespa_scores' as source,
    student_email,
    cycle,
    vision,
    effort,
    systems,
    practice,
    attitude,
    overall,
    completion_date,
    academic_year
FROM vespa_scores
WHERE student_email = 'cali@vespa.academy'
ORDER BY cycle, completion_date DESC;

-- ==========================================
-- 10. Check Cash's cache in vespa_students
-- ==========================================
SELECT 
    email,
    latest_vespa_scores,
    current_level,
    current_cycle,
    total_activities_completed
FROM vespa_students
WHERE email = 'cali@vespa.academy';

-- ==========================================
-- 11. Sample comparison: Scores vs Cache
-- ==========================================
SELECT 
    vst.email,
    vst.latest_vespa_scores as cached_scores,
    vs.cycle as latest_cycle,
    vs.vision,
    vs.effort,
    vs.completion_date as latest_completion
FROM vespa_students vst
LEFT JOIN LATERAL (
    SELECT * 
    FROM vespa_scores 
    WHERE student_email = vst.email 
    ORDER BY completion_date DESC 
    LIMIT 1
) vs ON true
WHERE vst.email IS NOT NULL
LIMIT 10;

-- ==========================================
-- 12. Find all students needing cache update
-- ==========================================
SELECT 
    vs.student_email,
    MAX(vs.cycle) as latest_cycle,
    MAX(vs.completion_date) as latest_completion,
    CASE 
        WHEN vst.email IS NULL THEN 'NOT IN vespa_students'
        WHEN vst.latest_vespa_scores IS NULL THEN 'CACHE IS NULL'
        ELSE 'CACHE EXISTS'
    END as cache_status
FROM vespa_scores vs
LEFT JOIN vespa_students vst ON vs.student_email = vst.email
WHERE vs.student_email IS NOT NULL
GROUP BY vs.student_email, vst.email, vst.latest_vespa_scores
ORDER BY cache_status, latest_completion DESC;

