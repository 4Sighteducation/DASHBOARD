-- Drop all the policies that are blocking access
DROP POLICY IF EXISTS "Service role has full access to trusts" ON trusts;
DROP POLICY IF EXISTS "Service role has full access to establishments" ON establishments;
DROP POLICY IF EXISTS "Service role has full access to staff_admins" ON staff_admins;
DROP POLICY IF EXISTS "Service role has full access to students" ON students;
DROP POLICY IF EXISTS "Service role has full access to vespa_scores" ON vespa_scores;
DROP POLICY IF EXISTS "Service role has full access to question_responses" ON question_responses;
DROP POLICY IF EXISTS "Service role has full access to school_statistics" ON school_statistics;
DROP POLICY IF EXISTS "Service role has full access to question_statistics" ON question_statistics;
DROP POLICY IF EXISTS "Service role has full access to national_statistics" ON national_statistics;
DROP POLICY IF EXISTS "Service role has full access to sync_logs" ON sync_logs;

-- Create permissive policies that allow all operations when using service key
-- The service key already bypasses RLS, but these policies ensure compatibility

CREATE POLICY "Enable all access for service role" ON trusts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON establishments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON staff_admins FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON students FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON vespa_scores FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON question_responses FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON school_statistics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON question_statistics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON national_statistics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for service role" ON sync_logs FOR ALL USING (true) WITH CHECK (true);