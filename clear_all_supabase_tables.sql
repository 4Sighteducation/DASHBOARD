-- COMPLETE CLEAN SLATE - Clear all Supabase tables
-- Run these in order to avoid foreign key constraint issues

-- 1. First, check current record counts
SELECT 'question_responses' as table_name, COUNT(*) as count FROM question_responses
UNION ALL
SELECT 'vespa_scores', COUNT(*) FROM vespa_scores
UNION ALL
SELECT 'students', COUNT(*) FROM students
UNION ALL
SELECT 'establishments', COUNT(*) FROM establishments
UNION ALL
SELECT 'staff_admins', COUNT(*) FROM staff_admins
UNION ALL
SELECT 'super_users', COUNT(*) FROM super_users
UNION ALL
SELECT 'school_statistics', COUNT(*) FROM school_statistics
UNION ALL
SELECT 'question_statistics', COUNT(*) FROM question_statistics
UNION ALL
SELECT 'national_statistics', COUNT(*) FROM national_statistics
UNION ALL
SELECT 'sync_logs', COUNT(*) FROM sync_logs
UNION ALL
SELECT 'current_school_averages (VIEW)', COUNT(*) FROM current_school_averages;

-- 2. Clear tables in reverse dependency order
-- (Child tables first, then parent tables)

-- Clear statistics tables (no dependencies)
TRUNCATE TABLE school_statistics CASCADE;
TRUNCATE TABLE question_statistics CASCADE;
TRUNCATE TABLE national_statistics CASCADE;
-- current_school_averages is a VIEW, not a table - no need to clear
TRUNCATE TABLE sync_logs CASCADE;

-- Clear tables that depend on students
TRUNCATE TABLE question_responses CASCADE;
TRUNCATE TABLE vespa_scores CASCADE;

-- Clear students (depends on establishments)
TRUNCATE TABLE students CASCADE;

-- Clear establishments
TRUNCATE TABLE establishments CASCADE;

-- Clear staff tables (independent)
TRUNCATE TABLE staff_admins CASCADE;
TRUNCATE TABLE super_users CASCADE;

-- 3. Verify everything is cleared
SELECT 'AFTER CLEARING:' as status;
SELECT 'question_responses' as table_name, COUNT(*) as count FROM question_responses
UNION ALL
SELECT 'vespa_scores', COUNT(*) FROM vespa_scores
UNION ALL
SELECT 'students', COUNT(*) FROM students
UNION ALL
SELECT 'establishments', COUNT(*) FROM establishments
UNION ALL
SELECT 'staff_admins', COUNT(*) FROM staff_admins
UNION ALL
SELECT 'super_users', COUNT(*) FROM super_users
UNION ALL
SELECT 'school_statistics', COUNT(*) FROM school_statistics
UNION ALL
SELECT 'question_statistics', COUNT(*) FROM question_statistics
UNION ALL
SELECT 'national_statistics', COUNT(*) FROM national_statistics
UNION ALL
SELECT 'sync_logs', COUNT(*) FROM sync_logs;

-- Note: TRUNCATE CASCADE will also clear any dependent tables automatically
-- This is faster than DELETE and resets any auto-increment counters