-- DELETE ALL Alena Ramsey data from Supabase
-- Email: aramsey@vespa.academy
-- Run these in order (respects foreign key constraints)

-- 1. Delete staff coaching notes
DELETE FROM staff_coaching_notes 
WHERE student_id IN (
    SELECT id FROM students WHERE email = 'aramsey@vespa.academy'
);

-- 2. Delete student goals
DELETE FROM student_goals 
WHERE student_id IN (
    SELECT id FROM students WHERE email = 'aramsey@vespa.academy'
);

-- 3. Delete student responses
DELETE FROM student_responses 
WHERE student_id IN (
    SELECT id FROM students WHERE email = 'aramsey@vespa.academy'
);

-- 4. Delete question responses
DELETE FROM question_responses 
WHERE student_id IN (
    SELECT id FROM students WHERE email = 'aramsey@vespa.academy'
);

-- 5. Delete VESPA scores
DELETE FROM vespa_scores 
WHERE student_id IN (
    SELECT id FROM students WHERE email = 'aramsey@vespa.academy'
);

-- 6. Delete student records
DELETE FROM students WHERE email = 'aramsey@vespa.academy';

-- Verify deletion (should return 0)
SELECT COUNT(*) as remaining_records FROM students WHERE email = 'aramsey@vespa.academy';

