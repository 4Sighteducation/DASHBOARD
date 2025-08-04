-- Check RLS status on student_comments table
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename = 'student_comments';

-- Check existing policies
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    permissive, 
    roles, 
    cmd, 
    qual, 
    with_check
FROM pg_policies
WHERE schemaname = 'public' 
AND tablename = 'student_comments';

-- TEMPORARILY DISABLE RLS for sync
-- This will allow all operations regardless of policies
ALTER TABLE student_comments DISABLE ROW LEVEL SECURITY;

-- Verify RLS is disabled
SELECT 
    tablename,
    rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename = 'student_comments';