-- FINAL FIX: Update question_responses academic years to match VESPA scores
-- Run this in Supabase SQL Editor

-- First, let's see what we're dealing with
SELECT 
    'Before Update' as status,
    qr.academic_year as qr_year,
    vs.academic_year as vespa_year,
    COUNT(*) as count
FROM question_responses qr
JOIN vespa_scores vs ON qr.student_id = vs.student_id AND qr.cycle = vs.cycle
GROUP BY qr.academic_year, vs.academic_year
ORDER BY qr.academic_year, vs.academic_year;

-- Now do the update
UPDATE question_responses qr
SET academic_year = vs.academic_year
FROM vespa_scores vs
WHERE qr.student_id = vs.student_id
  AND qr.cycle = vs.cycle
  AND vs.academic_year IS NOT NULL
  AND vs.academic_year IN ('2024/2025', '2025/2026');

-- Verify the update worked
SELECT 
    'After Update' as status,
    academic_year,
    COUNT(*) as count
FROM question_responses
WHERE academic_year IS NOT NULL
GROUP BY academic_year
ORDER BY academic_year;

-- Show how many records were updated
SELECT 
    'Updated Records' as status,
    COUNT(*) as total_2024_2025
FROM question_responses
WHERE academic_year = '2024/2025'
UNION ALL
SELECT 
    'Updated Records' as status,
    COUNT(*) as total_2025_2026
FROM question_responses
WHERE academic_year = '2025/2026';
