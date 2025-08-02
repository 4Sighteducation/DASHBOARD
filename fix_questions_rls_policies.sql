-- Quick fix for RLS policies on questions table
-- Run this if you already created the table but can't insert data

-- Add policy to allow authenticated users to insert questions
CREATE POLICY IF NOT EXISTS "Allow authenticated users to insert questions" ON questions
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Add policy to allow service role full access (if using service key)
CREATE POLICY IF NOT EXISTS "Allow service role to manage questions" ON questions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Verify policies are created
SELECT tablename, policyname, cmd, roles 
FROM pg_policies 
WHERE tablename = 'questions';