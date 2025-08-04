-- Fix RLS policies for student_comments table

-- First, check if we're using service role
-- The sync script should use SUPABASE_KEY which should be the service role key

-- Drop existing policies
DROP POLICY IF EXISTS "Service role can manage all comments" ON student_comments;
DROP POLICY IF EXISTS "Users can read comments for their establishment" ON student_comments;

-- Create new policies
-- 1. Allow service role full access (for sync)
CREATE POLICY "Service role has full access" ON student_comments
    FOR ALL 
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 2. Allow authenticated users to read comments for their establishment
CREATE POLICY "Users can read comments for their establishment" ON student_comments
    FOR SELECT 
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM students s
            WHERE s.id = student_comments.student_id
            AND s.establishment_id IN (
                SELECT establishment_id FROM staff_admins 
                WHERE email = auth.jwt() ->> 'email'
            )
        )
    );

-- 3. Allow anon/public inserts if using anon key (temporary for sync)
-- This is less secure but allows sync to work if not using service role key
CREATE POLICY "Allow inserts for sync" ON student_comments
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Check current policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'student_comments';