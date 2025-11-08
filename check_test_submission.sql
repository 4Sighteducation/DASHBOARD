-- Check if Ferzan Zeshan's data exists in Supabase
-- Email: s251719@rochdalesfc.ac.uk

-- 1. Check students table
SELECT 
    id,
    knack_id,
    email,
    name,
    academic_year,
    establishment_id
FROM students
WHERE email = 's251719@rochdalesfc.ac.uk';

-- 2. Check vespa_scores (if student exists)
SELECT 
    vs.id,
    vs.student_id,
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date,
    vs.academic_year
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
WHERE s.email = 's251719@rochdalesfc.ac.uk'
ORDER BY vs.cycle;

-- 3. Check question_responses count
SELECT 
    qr.cycle,
    COUNT(*) as response_count
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.email = 's251719@rochdalesfc.ac.uk'
GROUP BY qr.cycle;

-- 4. DELETE TEST DATA (run these if data exists)
/*
DELETE FROM question_responses 
WHERE student_id IN (
    SELECT id FROM students WHERE email = 's251719@rochdalesfc.ac.uk'
);

DELETE FROM vespa_scores 
WHERE student_id IN (
    SELECT id FROM students WHERE email = 's251719@rochdalesfc.ac.uk'
);

DELETE FROM students 
WHERE email = 's251719@rochdalesfc.ac.uk';
*/

