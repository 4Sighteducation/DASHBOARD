-- COMPREHENSIVE FIX FOR ALL DATA ISSUES
-- Run this in Supabase SQL Editor

-- ============================================
-- 1. FIX QUESTION RESPONSES ACADEMIC YEARS
-- ============================================
-- Update question_responses to match the academic_year from vespa_scores

UPDATE question_responses qr
SET academic_year = vs.academic_year
FROM vespa_scores vs
WHERE qr.student_id = vs.student_id
  AND qr.cycle = vs.cycle
  AND vs.academic_year IS NOT NULL;

-- Check the results
SELECT academic_year, COUNT(*) as count
FROM question_responses
GROUP BY academic_year
ORDER BY academic_year;

-- ============================================
-- 2. FIX STUDENT COMMENTS TABLE
-- ============================================
-- First check if student_comments table exists
DO $$
BEGIN
    -- Check if the table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'student_comments') THEN
        -- Check if academic_year column exists
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'student_comments' 
                      AND column_name = 'academic_year') THEN
            -- Add the column if it doesn't exist
            ALTER TABLE student_comments ADD COLUMN academic_year TEXT;
            RAISE NOTICE 'Added academic_year column to student_comments';
        END IF;
        
        -- Update academic_year based on vespa_scores
        UPDATE student_comments sc
        SET academic_year = vs.academic_year
        FROM vespa_scores vs
        WHERE sc.student_id = vs.student_id
          AND sc.cycle = vs.cycle
          AND vs.academic_year IS NOT NULL;
    ELSE
        RAISE NOTICE 'student_comments table does not exist - will need to create it';
    END IF;
END $$;

-- ============================================
-- 3. RECALCULATE ALL STATISTICS
-- ============================================
-- Now that academic years are fixed, recalculate everything

-- First, clear old statistics
DELETE FROM question_statistics WHERE true;

-- Calculate statistics for ALL establishments, ALL cycles, ALL academic years
INSERT INTO question_statistics (
    establishment_id, 
    question_id, 
    cycle, 
    academic_year,
    mean,
    std_dev,
    calculated_at
)
SELECT 
    s.establishment_id,
    qr.question_id,
    qr.cycle,
    qr.academic_year,
    ROUND(AVG(qr.response_value)::numeric, 2) as mean,
    ROUND(COALESCE(STDDEV(qr.response_value)::numeric, 0), 2) as std_dev,
    NOW() as calculated_at
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE qr.response_value > 0
  AND qr.academic_year IS NOT NULL
  AND qr.academic_year IN ('2024/2025', '2025/2026')  -- Focus on recent years
GROUP BY s.establishment_id, qr.question_id, qr.cycle, qr.academic_year
HAVING COUNT(*) > 0;

-- ============================================
-- 4. SHOW RESULTS
-- ============================================
SELECT 
    'Question Responses by Year' as report,
    academic_year,
    COUNT(*) as count
FROM question_responses
WHERE academic_year IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

SELECT 
    'Statistics by Year' as report,
    academic_year,
    COUNT(DISTINCT establishment_id) as establishments,
    COUNT(DISTINCT cycle) as cycles,
    COUNT(*) as total_stats
FROM question_statistics
GROUP BY academic_year
ORDER BY academic_year;

-- Check Shrewsbury specifically
SELECT 
    'Shrewsbury Statistics' as report,
    academic_year,
    cycle,
    COUNT(*) as question_count
FROM question_statistics
WHERE establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5'
GROUP BY academic_year, cycle
ORDER BY academic_year, cycle;
