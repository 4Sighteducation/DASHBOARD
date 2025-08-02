-- Fix any NULL is_australian values in establishments table
-- This ensures all establishments have a valid boolean value

-- First, check how many establishments have NULL is_australian
SELECT 
    COUNT(*) as total_establishments,
    COUNT(is_australian) as has_is_australian_value,
    COUNT(*) - COUNT(is_australian) as null_is_australian
FROM establishments;

-- Update any NULL values to FALSE (default for non-Australian schools)
UPDATE establishments 
SET is_australian = FALSE 
WHERE is_australian IS NULL;

-- Verify the fix
SELECT 
    COUNT(*) as total_establishments,
    SUM(CASE WHEN is_australian = TRUE THEN 1 ELSE 0 END) as australian_schools,
    SUM(CASE WHEN is_australian = FALSE THEN 1 ELSE 0 END) as non_australian_schools
FROM establishments;