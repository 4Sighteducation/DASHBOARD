-- Fix RLS policies for staff_admins table to allow sync operations
-- The sync script needs to INSERT and UPDATE records

-- Option 1: Add service role policies for sync operations
-- This allows operations when using the service role key (which sync scripts should use)

-- Policy for INSERT operations (for sync script using service role)
CREATE POLICY "Service role can insert staff admins" ON staff_admins
    FOR INSERT 
    TO service_role
    WITH CHECK (true);

-- Policy for UPDATE operations (for sync script using service role)
CREATE POLICY "Service role can update staff admins" ON staff_admins
    FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy for DELETE operations (for sync script cleanup if needed)
CREATE POLICY "Service role can delete staff admins" ON staff_admins
    FOR DELETE
    TO service_role
    USING (true);

-- If the above doesn't work because you're using anon key, use Option 2:

-- Option 2: Temporarily disable RLS for sync operations
-- Run this before sync:
-- ALTER TABLE staff_admins DISABLE ROW LEVEL SECURITY;

-- Run this after sync completes:
-- ALTER TABLE staff_admins ENABLE ROW LEVEL SECURITY;

-- Option 3: Create a sync user with special permissions
-- This is the most secure approach for production

-- Create a policy that allows a specific sync user to do everything
-- First create the sync user in Supabase Auth if not exists
-- Then create policies:

CREATE POLICY "Sync user can do everything on staff_admins" ON staff_admins
    FOR ALL
    USING (
        auth.email() = 'sync@vespa.academy' -- Replace with your sync user email
        OR auth.jwt() ->> 'role' = 'service_role'
    )
    WITH CHECK (
        auth.email() = 'sync@vespa.academy' -- Replace with your sync user email
        OR auth.jwt() ->> 'role' = 'service_role'
    );

-- Option 4: If using API key authentication, check for specific header or key
CREATE POLICY "API sync operations on staff_admins" ON staff_admins
    FOR ALL
    USING (
        current_setting('request.headers', true)::json->>'x-sync-token' = 'your-secret-sync-token'
        OR auth.jwt() ->> 'role' = 'service_role'
    )
    WITH CHECK (
        current_setting('request.headers', true)::json->>'x-sync-token' = 'your-secret-sync-token'
        OR auth.jwt() ->> 'role' = 'service_role'
    );