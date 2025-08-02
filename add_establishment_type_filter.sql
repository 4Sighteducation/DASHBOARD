-- Add a column to track establishment type for easier filtering
ALTER TABLE establishments 
ADD COLUMN IF NOT EXISTS portal_type VARCHAR(50);

-- Update the portal type based on field_63 from Knack
-- This would need to be done during sync, but we can add a comment for now
COMMENT ON COLUMN establishments.portal_type IS 'Type of portal: COACHING PORTAL or RESOURCE PORTAL from Knack field_63';