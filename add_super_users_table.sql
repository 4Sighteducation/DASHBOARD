-- Add Super Users table and fix Staff Admins mapping

-- 1. Create super_users table (for object_21)
CREATE TABLE IF NOT EXISTS super_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    knack_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create indexes
CREATE INDEX IF NOT EXISTS idx_super_users_email ON super_users(email);
CREATE INDEX IF NOT EXISTS idx_super_users_knack_id ON super_users(knack_id);

-- 3. Enable RLS
ALTER TABLE super_users ENABLE ROW LEVEL SECURITY;

-- 4. Add service role policy
CREATE POLICY "Service role has full access to super_users" ON super_users
FOR ALL USING (true) WITH CHECK (true);

-- 5. Check current staff_admins data (might be from wrong object)
SELECT COUNT(*) as current_count FROM staff_admins;

-- 6. View to check user access levels
CREATE OR REPLACE VIEW user_access_levels AS
SELECT 
    'super_user' as access_type,
    su.email,
    su.name,
    su.knack_id
FROM super_users su
UNION ALL
SELECT 
    'staff_admin' as access_type,
    sa.email,
    sa.name,
    sa.knack_id
FROM staff_admins sa
ORDER BY access_type, email;