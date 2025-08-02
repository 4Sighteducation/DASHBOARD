-- Fix RLS for super_users table
-- First, check if table exists and create if needed
CREATE TABLE IF NOT EXISTS super_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knack_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Disable RLS temporarily to allow sync
ALTER TABLE super_users DISABLE ROW LEVEL SECURITY;

-- Or if you want to keep RLS, create proper policies
-- ALTER TABLE super_users ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
-- CREATE POLICY "Service role has full access to super_users" ON super_users
--     FOR ALL
--     TO service_role
--     USING (true)
--     WITH CHECK (true);

-- Allow authenticated users to read super_users
-- CREATE POLICY "Authenticated users can read super_users" ON super_users
--     FOR SELECT
--     TO authenticated
--     USING (true);