-- Fix Staff Admins Table - Add establishment relationship
-- This is CRITICAL for dashboard functionality

-- 1. Add establishment_id column to staff_admins if it doesn't exist
ALTER TABLE staff_admins 
ADD COLUMN IF NOT EXISTS establishment_id UUID REFERENCES establishments(id) ON DELETE SET NULL;

-- 2. Create index for performance
CREATE INDEX IF NOT EXISTS idx_staff_admins_establishment ON staff_admins(establishment_id);

-- 3. Update existing staff_admins with their establishment relationships
-- This requires mapping from Knack's Object_5 field_201 (Staff Admin -> Establishment connection)
-- The sync script will need to be updated to populate this field

-- 4. Add RLS (Row Level Security) policies for staff admins
ALTER TABLE staff_admins ENABLE ROW LEVEL SECURITY;

-- Policy for staff admins to see only their own record
CREATE POLICY "Staff admins can view own record" ON staff_admins
    FOR SELECT USING (auth.email() = email);

-- Policy for super users to see all staff admins
CREATE POLICY "Super users can view all staff admins" ON staff_admins
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM super_users 
            WHERE super_users.email = auth.email()
        )
    );

-- 5. Create a view for easy dashboard access
CREATE OR REPLACE VIEW dashboard_user_access AS
SELECT 
    COALESCE(sa.email, su.email) as user_email,
    sa.establishment_id,
    e.name as establishment_name,
    CASE 
        WHEN su.email IS NOT NULL THEN 'super_user'
        ELSE 'staff_admin'
    END as user_role,
    sa.knack_id as staff_admin_knack_id,
    su.knack_id as super_user_knack_id
FROM staff_admins sa
FULL OUTER JOIN super_users su ON sa.email = su.email
LEFT JOIN establishments e ON sa.establishment_id = e.id;

-- 6. Create function to get user's accessible establishments
CREATE OR REPLACE FUNCTION get_user_establishments(user_email TEXT)
RETURNS TABLE (
    establishment_id UUID,
    establishment_name TEXT,
    can_emulate BOOLEAN
) AS $$
BEGIN
    -- Check if user is a super user
    IF EXISTS (SELECT 1 FROM super_users WHERE email = user_email) THEN
        -- Super users can access all establishments
        RETURN QUERY
        SELECT 
            e.id as establishment_id,
            e.name as establishment_name,
            true as can_emulate
        FROM establishments e
        ORDER BY e.name;
    ELSE
        -- Staff admins can only access their own establishment
        RETURN QUERY
        SELECT 
            sa.establishment_id,
            e.name as establishment_name,
            false as can_emulate
        FROM staff_admins sa
        JOIN establishments e ON sa.establishment_id = e.id
        WHERE sa.email = user_email;
    END IF;
END;
$$ LANGUAGE plpgsql;