-- Clean up ALL Alena Ramsey data from Supabase
-- Email: aramsey@vespa.academy
-- Student IDs: 6d7155c9-1f16-4333-b009-41db9a5faae6 (OLD), fbd8d15c-cb92-45cf-ac31-ee18e23bcbda (NEW)

-- Delete in order (respect foreign key constraints)

-- 1. Delete staff coaching notes
DELETE FROM staff_coaching_notes 
WHERE student_id IN (
    '6d7155c9-1f16-4333-b009-41db9a5faae6',
    'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
);

-- 2. Delete student goals
DELETE FROM student_goals 
WHERE student_id IN (
    '6d7155c9-1f16-4333-b009-41db9a5faae6',
    'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
);

-- 3. Delete student responses
DELETE FROM student_responses 
WHERE student_id IN (
    '6d7155c9-1f16-4333-b009-41db9a5faae6',
    'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
);

-- 4. Delete question responses
DELETE FROM question_responses 
WHERE student_id IN (
    '6d7155c9-1f16-4333-b009-41db9a5faae6',
    'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
);

-- 5. Delete VESPA scores
DELETE FROM vespa_scores 
WHERE student_id IN (
    '6d7155c9-1f16-4333-b009-41db9a5faae6',
    'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
);

-- 6. Finally, delete student records
DELETE FROM students 
WHERE id IN (
    '6d7155c9-1f16-4333-b009-41db9a5faae6',
    'fbd8d15c-cb92-45cf-ac31-ee18e23bcbda'
);

-- Verify deletion
SELECT COUNT(*) as remaining_records FROM students WHERE email = 'aramsey@vespa.academy';
-- Should return 0

SELECT 'CLEANED UP - Ready for fresh sync!' as status;

