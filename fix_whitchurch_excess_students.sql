-- FIX WHITCHURCH: Remove incorrect 2025/2026 data
-- Problem: 445 students have 2025/2026 data, but only 207 should (current Year 13s)
-- Solution: Identify and clean up the 238 graduated students

-- ============================================================================
-- STEP 1: Identify the pattern - who has what data?
-- ============================================================================

-- Check Year Groups of students with 2025/2026 data
SELECT 
    s.year_group,
    COUNT(DISTINCT s.id) as student_count,
    'Has 2025/2026 VESPA data' as status
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2025/2026'
)
GROUP BY s.year_group
ORDER BY s.year_group;

-- ============================================================================
-- STEP 2: Find students who ONLY have old data (graduated)
-- ============================================================================

-- These are likely the graduated Year 13s who shouldn't have 2025/2026 data
WITH student_data_pattern AS (
    SELECT 
        s.id,
        s.email,
        s.name,
        s.year_group,
        s.knack_id,
        MAX(CASE WHEN vs.academic_year = '2024/2025' THEN 1 ELSE 0 END) as has_2024_25,
        MAX(CASE WHEN vs.academic_year = '2025/2026' THEN 1 ELSE 0 END) as has_2025_26,
        COUNT(DISTINCT vs.cycle) FILTER (WHERE vs.academic_year = '2024/2025') as cycles_2024_25,
        COUNT(DISTINCT vs.cycle) FILTER (WHERE vs.academic_year = '2025/2026') as cycles_2025_26
    FROM students s
    LEFT JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    GROUP BY s.id, s.email, s.name, s.year_group, s.knack_id
)
SELECT 
    'Data Pattern Analysis' as analysis,
    CASE 
        WHEN has_2024_25 = 1 AND has_2025_26 = 1 THEN 'Both Years (Continuing Students)'
        WHEN has_2024_25 = 1 AND has_2025_26 = 0 THEN '2024/25 Only (Graduated)'
        WHEN has_2024_25 = 0 AND has_2025_26 = 1 THEN '2025/26 Only (New or Error)'
        ELSE 'No VESPA Data'
    END as pattern,
    COUNT(*) as student_count,
    STRING_AGG(DISTINCT year_group, ', ' ORDER BY year_group) as year_groups
FROM student_data_pattern
GROUP BY pattern
ORDER BY pattern;

-- ============================================================================
-- STEP 3: Identify the likely graduated students (have minimal 2025/26 data)
-- ============================================================================

-- Students with suspiciously little 2025/2026 data (likely sync errors)
WITH suspicious_students AS (
    SELECT 
        s.id,
        s.email,
        s.name,
        s.year_group,
        COUNT(DISTINCT vs.cycle) FILTER (WHERE vs.academic_year = '2025/2026') as cycles_2025_26,
        MAX(vs.completion_date) FILTER (WHERE vs.academic_year = '2025/2026') as latest_2025_26_date
    FROM students s
    LEFT JOIN vespa_scores vs ON s.id = vs.student_id
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs2 
        WHERE vs2.student_id = s.id 
        AND vs2.academic_year = '2025/2026'
    )
    GROUP BY s.id, s.email, s.name, s.year_group
    HAVING COUNT(DISTINCT vs.cycle) FILTER (WHERE vs.academic_year = '2025/2026') <= 1
)
SELECT 
    'Suspicious 2025/26 Records' as category,
    COUNT(*) as total,
    COUNT(CASE WHEN year_group = 'Year 13' THEN 1 END) as year_13s,
    COUNT(CASE WHEN year_group = 'Year 12' THEN 1 END) as year_12s,
    MIN(latest_2025_26_date) as earliest_date,
    MAX(latest_2025_26_date) as latest_date
FROM suspicious_students;

-- ============================================================================
-- STEP 4: THE FIX - Remove incorrect 2025/2026 VESPA scores
-- ============================================================================

-- IMPORTANT: First, let's identify which students should NOT have 2025/2026 data
-- These would be students who:
-- 1. Have Year Group = 'Year 13' (if this wasn't updated)
-- 2. Have complete 2024/2025 data (3 cycles)
-- 3. Have minimal or no real 2025/2026 activity

-- Count students to be fixed
WITH students_to_fix AS (
    SELECT 
        s.id,
        s.email,
        s.name,
        s.year_group
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    -- They have 2025/2026 data
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2025/2026'
    )
    -- But they're likely graduated (had full 2024/2025 data)
    AND EXISTS (
        SELECT 1 
        FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2024/2025'
        AND vs.cycle = 3  -- They completed all cycles last year
    )
    -- And their 2025/26 data looks suspicious (only cycle 1, likely from sync error)
    AND NOT EXISTS (
        SELECT 1 
        FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2025/2026'
        AND vs.cycle > 1  -- No cycle 2 or 3 data for current year
    )
)
SELECT 
    'Students to Fix' as category,
    COUNT(*) as count,
    'Will remove their incorrect 2025/2026 VESPA data' as action
FROM students_to_fix;

-- ============================================================================
-- STEP 5: BACKUP before making changes
-- ============================================================================

-- Create backup of VESPA scores that will be deleted
CREATE TEMP TABLE vespa_scores_backup_2025_26 AS
SELECT vs.*
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND vs.academic_year = '2025/2026';

SELECT COUNT(*) as "Backed up records" FROM vespa_scores_backup_2025_26;

-- ============================================================================
-- STEP 6: THE ACTUAL FIX (COMMENT OUT UNTIL READY)
-- ============================================================================

/*
-- REMOVE incorrect 2025/2026 VESPA scores for graduated students
DELETE FROM vespa_scores vs
WHERE vs.student_id IN (
    SELECT s.id
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    -- They have 2025/2026 data
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs2 
        WHERE vs2.student_id = s.id 
        AND vs2.academic_year = '2025/2026'
    )
    -- But they completed Year 13 last year
    AND EXISTS (
        SELECT 1 
        FROM vespa_scores vs2 
        WHERE vs2.student_id = s.id 
        AND vs2.academic_year = '2024/2025'
        AND vs2.cycle = 3
    )
    -- And have no real current year activity
    AND NOT EXISTS (
        SELECT 1 
        FROM vespa_scores vs2 
        WHERE vs2.student_id = s.id 
        AND vs2.academic_year = '2025/2026'
        AND vs2.cycle > 1
    )
)
AND vs.academic_year = '2025/2026';
*/

-- ============================================================================
-- STEP 7: After fix - verify counts
-- ============================================================================

-- After running the DELETE, check the new counts:
SELECT 
    'After Fix' as status,
    academic_year,
    COUNT(DISTINCT student_id) as unique_students
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY academic_year
ORDER BY academic_year;

-- ============================================================================
-- ALTERNATIVE: More conservative approach - only keep verified current students
-- ============================================================================

-- If you know exactly which students should be in 2025/2026,
-- you could take the opposite approach:
-- 1. Get a list of current student emails from Knack
-- 2. Delete 2025/2026 VESPA data for anyone NOT in that list

/*
-- Example:
DELETE FROM vespa_scores vs
WHERE vs.academic_year = '2025/2026'
AND vs.student_id IN (
    SELECT s.id 
    FROM students s 
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    AND s.email NOT IN (
        -- List of 207 current student emails from Knack
        'student1@school.com',
        'student2@school.com',
        -- etc...
    )
);
*/
