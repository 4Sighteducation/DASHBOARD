-- Create super_users table if it doesn't exist
-- This table was missing from the original schema

CREATE TABLE IF NOT EXISTS super_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knack_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_super_users_email ON super_users(email);
CREATE INDEX IF NOT EXISTS idx_super_users_knack_id ON super_users(knack_id);

-- Add RLS policy if needed
ALTER TABLE super_users ENABLE ROW LEVEL SECURITY;

-- Grant access to service role
CREATE POLICY "Service role has full access to super_users" ON super_users
FOR ALL USING (auth.role() = 'service_role');

-- Add comment
COMMENT ON TABLE super_users IS 'Super users from Knack Object_21 with global access privileges';