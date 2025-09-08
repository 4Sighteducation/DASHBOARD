-- Optional: Add email-based student matching to handle re-created accounts
-- This would merge students with the same email but different knack_ids

-- Step 1: Add index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_students_email 
ON students(LOWER(email));

-- Step 2: Create a function to merge duplicate students
CREATE OR REPLACE FUNCTION merge_duplicate_students()
RETURNS void AS $$
DECLARE
    duplicate_rec RECORD;
    primary_student_id UUID;
    duplicate_student_id UUID;
BEGIN
    -- Find students with duplicate emails
    FOR duplicate_rec IN 
        SELECT LOWER(email) as email, COUNT(*) as count
        FROM students
        GROUP BY LOWER(email)
        HAVING COUNT(*) > 1
    LOOP
        -- Get the oldest (primary) student record
        SELECT id INTO primary_student_id
        FROM students
        WHERE LOWER(email) = duplicate_rec.email
        ORDER BY created_at ASC
        LIMIT 1;
        
        -- Process each duplicate
        FOR duplicate_student_id IN
            SELECT id FROM students
            WHERE LOWER(email) = duplicate_rec.email
            AND id != primary_student_id
        LOOP
            -- Move all vespa_scores to primary student
            UPDATE vespa_scores 
            SET student_id = primary_student_id
            WHERE student_id = duplicate_student_id
            -- Only if this wouldn't create a duplicate
            AND NOT EXISTS (
                SELECT 1 FROM vespa_scores v2
                WHERE v2.student_id = primary_student_id
                AND v2.cycle = vespa_scores.cycle
                AND v2.academic_year = vespa_scores.academic_year
            );
            
            -- Move question_responses
            UPDATE question_responses
            SET student_id = primary_student_id
            WHERE student_id = duplicate_student_id
            AND NOT EXISTS (
                SELECT 1 FROM question_responses q2
                WHERE q2.student_id = primary_student_id
                AND q2.cycle = question_responses.cycle
                AND q2.question_id = question_responses.question_id
            );
            
            -- Delete the duplicate student
            DELETE FROM students WHERE id = duplicate_student_id;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Optional - Run this periodically to merge duplicates
-- SELECT merge_duplicate_students();
