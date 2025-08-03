-- IMMEDIATE FIX: Completely disable RLS for sync operations

-- 1. First, check current RLS status
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE tablename = 'staff_admins';

-- 2. Drop ALL existing policies on staff_admins
DO $$ 
DECLARE
    pol record;
BEGIN
    FOR pol IN 
        SELECT policyname 
        FROM pg_policies 
        WHERE tablename = 'staff_admins'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON staff_admins', pol.policyname);
    END LOOP;
END $$;

-- 3. Disable RLS completely
ALTER TABLE staff_admins DISABLE ROW LEVEL SECURITY;

-- 4. Verify RLS is disabled
SELECT 
    'staff_admins' as table_name,
    CASE 
        WHEN rowsecurity THEN 'ENABLED' 
        ELSE 'DISABLED' 
    END as rls_status
FROM pg_tables
WHERE tablename = 'staff_admins';

-- After sync is complete, you can re-enable with proper policies:
/*
-- Re-enable RLS
ALTER TABLE staff_admins ENABLE ROW LEVEL SECURITY;

-- Add back the read policies
CREATE POLICY "Staff admins can view own record" ON staff_admins
    FOR SELECT USING (auth.email() = email);

CREATE POLICY "Super users can view all staff admins" ON staff_admins
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM super_users 
            WHERE super_users.email = auth.email()
        )
    );

-- Add service role policies
CREATE POLICY "Service role full access" ON staff_admins
    FOR ALL 
    TO service_role
    WITH CHECK (true);
*/