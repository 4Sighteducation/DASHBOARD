-- Simpler approach: Run the Python manual calculation to fix statistics
-- First, let's check what we have

-- Check school statistics
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN std_dev IS NULL THEN 1 END) as null_std_dev,
    COUNT(CASE WHEN distribution IS NULL THEN 1 END) as null_distribution,
    COUNT(CASE WHEN distribution = '[0,0,0,0,0,0,0]' THEN 1 END) as empty_distribution
FROM school_statistics;

-- Check national statistics  
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN std_dev IS NULL THEN 1 END) as null_std_dev,
    COUNT(CASE WHEN distribution IS NULL THEN 1 END) as null_distribution,
    COUNT(CASE WHEN distribution = '[0,0,0,0,0,0,0,0,0,0,0]' THEN 1 END) as empty_distribution
FROM national_statistics;

-- To fix: Run the Python script force_manual_statistics.py which will:
-- 1. Clear existing statistics
-- 2. Recalculate with proper std_dev and distribution values
-- 3. Then recalculate national statistics based on the fixed school statistics