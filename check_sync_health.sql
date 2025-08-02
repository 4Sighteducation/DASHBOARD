-- Comprehensive sync health check for question_responses

-- 1. Overview of question_responses
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT student_id) as unique_students,
    COUNT(DISTINCT (student_id, cycle, question_id)) as unique_responses,
    COUNT(*) - COUNT(DISTINCT (student_id, cycle, question_id)) as duplicate_count
FROM question_responses;

-- 2. Check for duplicates (should be 0 with unique constraint)
WITH duplicates AS (
    SELECT 
        student_id, 
        cycle, 
        question_id,
        COUNT(*) as duplicate_count
    FROM question_responses
    GROUP BY student_id, cycle, question_id
    HAVING COUNT(*) > 1
)
SELECT COUNT(*) as duplicate_groups, SUM(duplicate_count - 1) as extra_records
FROM duplicates;

-- 3. Distribution by cycle
SELECT 
    cycle,
    COUNT(DISTINCT student_id) as students_in_cycle,
    COUNT(DISTINCT question_id) as unique_questions,
    COUNT(*) as total_responses,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT student_id), 2) as avg_responses_per_student
FROM question_responses
GROUP BY cycle
ORDER BY cycle;

-- 4. Check created_at timestamps to see sync patterns
SELECT 
    DATE(created_at) as sync_date,
    TO_CHAR(created_at, 'HH24:MI') as sync_time,
    COUNT(*) as records_synced
FROM question_responses
GROUP BY DATE(created_at), TO_CHAR(created_at, 'HH24:MI')
ORDER BY sync_date DESC, sync_time DESC
LIMIT 20;

-- 5. Find students with incomplete responses
WITH student_response_counts AS (
    SELECT 
        student_id,
        COUNT(DISTINCT question_id) as questions_answered,
        COUNT(DISTINCT cycle) as cycles_completed
    FROM question_responses
    GROUP BY student_id
)
SELECT 
    questions_answered,
    cycles_completed,
    COUNT(*) as student_count
FROM student_response_counts
GROUP BY questions_answered, cycles_completed
ORDER BY student_count DESC
LIMIT 10;

-- 6. Verify all students have linked establishments
SELECT 
    s.year_group,
    COUNT(DISTINCT s.id) as total_students,
    COUNT(DISTINCT CASE WHEN s.establishment_id IS NOT NULL THEN s.id END) as with_establishment,
    COUNT(DISTINCT qr.student_id) as students_with_responses
FROM students s
LEFT JOIN question_responses qr ON s.id = qr.student_id
GROUP BY s.year_group
ORDER BY total_students DESC;

-- 7. Check for orphaned question_responses (student doesn't exist)
SELECT COUNT(*) as orphaned_responses
FROM question_responses qr
WHERE NOT EXISTS (
    SELECT 1 FROM students s WHERE s.id = qr.student_id
);

-- 8. Sample of most recent syncs
SELECT 
    qr.id,
    s.email as student_email,
    qr.cycle,
    qr.question_id,
    qr.response_value,
    qr.created_at
FROM question_responses qr
JOIN students s ON s.id = qr.student_id
ORDER BY qr.created_at DESC
LIMIT 10;