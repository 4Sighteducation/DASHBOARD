-- Quick solution: Temporarily disable RLS to load questions

-- 1. Disable RLS
ALTER TABLE questions DISABLE ROW LEVEL SECURITY;

-- 2. After running this, run your Python script:
-- python load_questions_to_supabase.py

-- 3. Then run this to re-enable RLS with proper policies:
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

-- Drop any existing policies first
DROP POLICY IF EXISTS "Allow authenticated users to read questions" ON questions;
DROP POLICY IF EXISTS "Allow authenticated users to insert questions" ON questions;
DROP POLICY IF EXISTS "Allow service role to manage questions" ON questions;

-- Create new policies
CREATE POLICY "Anyone can read questions" ON questions
    FOR SELECT 
    USING (true);  -- No authentication required for reading

CREATE POLICY "Service role can manage questions" ON questions
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Verify the questions table has data
SELECT COUNT(*) as question_count FROM questions;
SELECT question_id, question_text, vespa_category FROM questions LIMIT 5;