-- Complete profile check for test student: Ferzan Zeshan
-- Email: s251719@rochdalesfc.ac.uk

-- ===== STUDENT RECORD =====
SELECT 
    '=== STUDENT RECORD ===' as section,
    s.id as student_id,
    s.knack_id,
    s.email,
    s.name,
    s.establishment_id,
    s.year_group,
    s."group",
    s.academic_year,
    s.created_at
FROM students s
WHERE s.email = 's251719@rochdalesfc.ac.uk'
ORDER BY s.academic_year DESC;

-- ===== VESPA SCORES (ALL CYCLES) =====
SELECT 
    '=== VESPA SCORES ===' as section,
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date,
    vs.academic_year,
    vs.created_at
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.email = 's251719@rochdalesfc.ac.uk'
ORDER BY vs.cycle;

-- ===== QUESTION RESPONSES COUNT =====
SELECT 
    '=== QUESTION RESPONSES COUNT ===' as section,
    qr.cycle,
    COUNT(*) as response_count,
    vs.completion_date,
    CASE 
        WHEN COUNT(*) = 32 THEN '✅ Complete'
        ELSE '⚠️ Missing ' || (32 - COUNT(*))
    END as status
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
LEFT JOIN vespa_scores vs ON vs.student_id = s.id AND vs.cycle = qr.cycle
WHERE s.email = 's251719@rochdalesfc.ac.uk'
GROUP BY qr.cycle, vs.completion_date
ORDER BY qr.cycle;

-- ===== STUDENT RESPONSES (REFLECTIONS) =====
SELECT 
    '=== STUDENT RESPONSES ===' as section,
    sr.cycle,
    LEFT(sr.response_text, 100) || '...' as response_preview,
    sr.submitted_at,
    sr.academic_year
FROM student_responses sr
JOIN students s ON sr.student_id = s.id
WHERE s.email = 's251719@rochdalesfc.ac.uk'
ORDER BY sr.cycle;

-- ===== STUDENT GOALS =====
SELECT 
    '=== STUDENT GOALS ===' as section,
    sg.cycle,
    LEFT(sg.goal_text, 100) || '...' as goal_preview,
    sg.goal_set_date,
    sg.goal_due_date,
    sg.academic_year
FROM student_goals sg
JOIN students s ON sg.student_id = s.id
WHERE s.email = 's251719@rochdalesfc.ac.uk'
ORDER BY sg.cycle;

-- ===== STAFF COACHING NOTES =====
SELECT 
    '=== COACHING NOTES ===' as section,
    scn.cycle,
    LEFT(scn.coaching_text, 100) || '...' as coaching_preview,
    scn.coaching_date,
    scn.academic_year
FROM staff_coaching_notes scn
JOIN students s ON scn.student_id = s.id
WHERE s.email = 's251719@rochdalesfc.ac.uk'
ORDER BY scn.cycle;

-- ===== SUMMARY =====
SELECT 
    '=== SUMMARY ===' as section,
    s.name,
    s.email,
    COUNT(DISTINCT vs.cycle) as cycles_completed,
    COUNT(DISTINCT qr.cycle) as cycles_with_responses,
    COUNT(DISTINCT sr.cycle) as cycles_with_reflection,
    COUNT(DISTINCT sg.cycle) as cycles_with_goals,
    COUNT(DISTINCT scn.cycle) as cycles_with_coaching
FROM students s
LEFT JOIN vespa_scores vs ON s.id = vs.student_id
LEFT JOIN question_responses qr ON s.id = qr.student_id
LEFT JOIN student_responses sr ON s.id = sr.student_id
LEFT JOIN student_goals sg ON s.id = sg.student_id
LEFT JOIN staff_coaching_notes scn ON s.id = scn.student_id
WHERE s.email = 's251719@rochdalesfc.ac.uk'
GROUP BY s.name, s.email;

-- ===== CHECK FOR DUPLICATES =====
SELECT 
    '=== DUPLICATE CHECK ===' as section,
    'students' as table_name,
    COUNT(*) as record_count,
    CASE 
        WHEN COUNT(*) > 1 THEN '⚠️ DUPLICATES FOUND!'
        ELSE '✅ No duplicates'
    END as status
FROM students
WHERE email = 's251719@rochdalesfc.ac.uk'
UNION ALL
SELECT 
    '=== DUPLICATE CHECK ===' as section,
    'vespa_scores' as table_name,
    COUNT(*) as record_count,
    CASE 
        WHEN COUNT(*) > 3 THEN '⚠️ TOO MANY CYCLES!'
        ELSE '✅ Normal'
    END as status
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.email = 's251719@rochdalesfc.ac.uk';

-- ===== LAST UPDATE TIMESTAMPS =====
SELECT 
    '=== LAST UPDATES ===' as section,
    MAX(vs.completion_date) as last_score_completion,
    MAX(qr.created_at) as last_response_added,
    NOW() as current_time
FROM students s
LEFT JOIN vespa_scores vs ON s.id = vs.student_id
LEFT JOIN question_responses qr ON s.id = qr.student_id
WHERE s.email = 's251719@rochdalesfc.ac.uk';

