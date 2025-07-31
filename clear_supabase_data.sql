-- Clear all data from Supabase tables (keeps structure intact)
-- Run these commands in order in Supabase SQL Editor

-- 1. Clear sync logs (optional - you might want to keep these for history)
-- DELETE FROM sync_logs WHERE true;

-- 2. Clear dependent tables first (due to foreign key constraints)
DELETE FROM question_responses WHERE true;
DELETE FROM vespa_scores WHERE true;
DELETE FROM school_statistics WHERE true;
DELETE FROM question_statistics WHERE true;

-- 3. Clear students
DELETE FROM students WHERE true;

-- 4. Clear establishments last
DELETE FROM establishments WHERE true;

-- 5. Reset any sequences if needed (optional)
-- This ensures IDs start fresh
ALTER SEQUENCE IF EXISTS establishments_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS students_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS vespa_scores_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS question_responses_id_seq RESTART WITH 1;

-- 6. Verify everything is empty
SELECT 
    'establishments' as table_name, COUNT(*) as count FROM establishments
UNION ALL
SELECT 'students', COUNT(*) FROM students
UNION ALL
SELECT 'vespa_scores', COUNT(*) FROM vespa_scores
UNION ALL
SELECT 'question_responses', COUNT(*) FROM question_responses
UNION ALL
SELECT 'school_statistics', COUNT(*) FROM school_statistics
UNION ALL
SELECT 'sync_logs', COUNT(*) FROM sync_logs;

-- All counts should be 0 (except sync_logs if you kept them)