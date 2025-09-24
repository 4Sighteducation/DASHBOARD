-- Check what data exists in national_statistics table
SELECT 
    academic_year,
    cycle,
    element,
    COUNT(*) as record_count,
    MAX(mean) as sample_mean
FROM national_statistics
GROUP BY academic_year, cycle, element
ORDER BY academic_year DESC, cycle, element
LIMIT 50;

-- Check if we have data for 2024/2025
SELECT DISTINCT academic_year 
FROM national_statistics 
ORDER BY academic_year DESC;

-- Check data for NPTC specifically for cycle 1
SELECT 
    academic_year,
    element,
    mean,
    count
FROM national_statistics
WHERE cycle = 1
AND academic_year IN ('2024/2025', '2025/2026', '2024-2025', '2025-2026')
ORDER BY academic_year, element;
