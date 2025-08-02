-- Fix existing staff_admins emails that contain HTML tags

-- First, let's see what we're dealing with
SELECT 
    id,
    email,
    CASE 
        WHEN email LIKE '%<a href="mailto:%' THEN 
            SUBSTRING(email FROM 'mailto:([^"]+)"')
        ELSE 
            email
    END as extracted_email
FROM staff_admins
WHERE email LIKE '%<a href="mailto:%'
LIMIT 10;

-- Update all emails that contain HTML to extract just the email address
UPDATE staff_admins
SET email = SUBSTRING(email FROM 'mailto:([^"]+)"')
WHERE email LIKE '%<a href="mailto:%';

-- Verify the fix
SELECT 
    COUNT(*) as total_staff,
    COUNT(CASE WHEN email LIKE '%@%' AND email NOT LIKE '%<%' THEN 1 END) as valid_emails,
    COUNT(CASE WHEN email LIKE '%<%' THEN 1 END) as still_has_html
FROM staff_admins;