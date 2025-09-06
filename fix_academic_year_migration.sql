-- ============================================================
-- VESPA Dashboard Academic Year Migration Script
-- Generated: 2025-09-06
-- Purpose: Fix academic year format and update existing data
-- ============================================================

BEGIN;

-- 1. Add unique constraint on student email if not exists
-- This will prevent duplicate students with same email
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'students_email_key'
    ) THEN
        ALTER TABLE students 
        ADD CONSTRAINT students_email_key UNIQUE (email);
    END IF;
END $$;

-- 2. Update VESPA scores from Aug 1, 2025 onwards to 2025/2026
UPDATE vespa_scores 
SET 
    academic_year = '2025/2026'
WHERE 
    created_at >= '2025-08-01'
    AND (academic_year IS NULL 
         OR academic_year = '2024/2025' 
         OR academic_year = '2025-26'
         OR academic_year = '2024-25');

-- Count updated records
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % VESPA responses to 2025/2026', updated_count;
END $$;

-- 3. Update question responses from Aug 1, 2025 onwards
UPDATE question_responses
SET 
    academic_year = '2025/2026'
WHERE 
    created_at >= '2025-08-01'
    AND (academic_year IS NULL 
         OR academic_year = '2024/2025' 
         OR academic_year = '2025-26'
         OR academic_year = '2024-25');

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % question responses to 2025/2026', updated_count;
END $$;

-- 4. Handle Australian schools (if is_australian field exists)
-- Update Australian school data from Jan 1, 2025 to Dec 31, 2025
UPDATE vespa_scores vr
SET 
    academic_year = '2025/2025'
FROM students s
JOIN establishments e ON s.establishment_id = e.id
WHERE 
    vr.student_id = s.id
    AND e.is_australian = true
    AND vr.created_at >= '2025-01-01'
    AND vr.created_at < '2026-01-01';

UPDATE question_responses qr
SET 
    academic_year = '2025/2025'
FROM students s
JOIN establishments e ON s.establishment_id = e.id
WHERE 
    qr.student_id = s.id
    AND e.is_australian = true
    AND qr.created_at >= '2025-01-01'
    AND qr.created_at < '2026-01-01';

-- 5. Update question_statistics table
UPDATE question_statistics
SET 
    academic_year = '2025/2026'
WHERE 
    calculated_at >= '2025-08-01'
    AND (academic_year IS NULL 
         OR academic_year = '2024/2025' 
         OR academic_year = '2025-26'
         OR academic_year = '2024-25');

-- 6. Update school_statistics table
UPDATE school_statistics
SET 
    academic_year = '2025/2026'
WHERE 
    calculated_at >= '2025-08-01'
    AND (academic_year IS NULL 
         OR academic_year = '2024/2025' 
         OR academic_year = '2025-26'
         OR academic_year = '2024-25');

-- 7. Fix any responses with wrong format from previous years
-- Convert 2024-25 format to 2024/2025 format
UPDATE vespa_scores
SET academic_year = REPLACE(REPLACE(academic_year, '-', '/20'), '/2020', '/20')
WHERE academic_year LIKE '%-%';

UPDATE question_responses
SET academic_year = REPLACE(REPLACE(academic_year, '-', '/20'), '/2020', '/20')
WHERE academic_year LIKE '%-%';

UPDATE question_statistics
SET academic_year = REPLACE(REPLACE(academic_year, '-', '/20'), '/2020', '/20')
WHERE academic_year LIKE '%-%';

UPDATE school_statistics
SET academic_year = REPLACE(REPLACE(academic_year, '-', '/20'), '/2020', '/20')
WHERE academic_year LIKE '%-%';

-- 8. Create or update academic_years lookup table for dropdown
CREATE TABLE IF NOT EXISTS academic_years (
    id SERIAL PRIMARY KEY,
    academic_year VARCHAR(9) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert academic years
INSERT INTO academic_years (academic_year, start_date, end_date, is_current)
VALUES 
    ('2023/2024', '2023-08-01', '2024-07-31', FALSE),
    ('2024/2025', '2024-08-01', '2025-07-31', FALSE),
    ('2025/2026', '2025-08-01', '2026-07-31', TRUE)
ON CONFLICT (academic_year) 
DO UPDATE SET 
    is_current = EXCLUDED.is_current,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date;

-- 9. Add function to auto-calculate academic year for new records
CREATE OR REPLACE FUNCTION calculate_academic_year(
    record_date TIMESTAMP WITH TIME ZONE,
    is_australian BOOLEAN DEFAULT FALSE
) RETURNS VARCHAR AS $$
BEGIN
    IF is_australian THEN
        -- Australian schools: calendar year
        RETURN EXTRACT(YEAR FROM record_date)::TEXT || '/' || EXTRACT(YEAR FROM record_date)::TEXT;
    ELSE
        -- Rest of world: August to July
        IF EXTRACT(MONTH FROM record_date) >= 8 THEN
            RETURN EXTRACT(YEAR FROM record_date)::TEXT || '/' || (EXTRACT(YEAR FROM record_date) + 1)::TEXT;
        ELSE
            RETURN (EXTRACT(YEAR FROM record_date) - 1)::TEXT || '/' || EXTRACT(YEAR FROM record_date)::TEXT;
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 10. Create trigger to auto-set academic year on new records
CREATE OR REPLACE FUNCTION set_academic_year_trigger()
RETURNS TRIGGER AS $$
DECLARE
    is_aus BOOLEAN DEFAULT FALSE;
BEGIN
    -- Check if establishment is Australian
    IF TG_TABLE_NAME IN ('vespa_scores', 'question_responses') THEN
        IF TG_TABLE_NAME = 'vespa_scores' THEN
            -- vespa_scores has student_id, need to join through students table
            SELECT COALESCE(e.is_australian, FALSE) INTO is_aus
            FROM students s
            JOIN establishments e ON s.establishment_id = e.id
            WHERE s.id = NEW.student_id;
        ELSIF TG_TABLE_NAME = 'question_responses' THEN
            SELECT COALESCE(e.is_australian, FALSE) INTO is_aus
            FROM students s
            JOIN establishments e ON s.establishment_id = e.id
            WHERE s.id = NEW.student_id;
        END IF;
    END IF;
    
    -- Set academic year if not provided
    IF NEW.academic_year IS NULL THEN
        NEW.academic_year := calculate_academic_year(COALESCE(NEW.created_at, NOW()), is_aus);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to relevant tables
DROP TRIGGER IF EXISTS auto_set_academic_year_vespa ON vespa_scores;
CREATE TRIGGER auto_set_academic_year_vespa
    BEFORE INSERT ON vespa_scores
    FOR EACH ROW
    EXECUTE FUNCTION set_academic_year_trigger();

DROP TRIGGER IF EXISTS auto_set_academic_year_questions ON question_responses;
CREATE TRIGGER auto_set_academic_year_questions
    BEFORE INSERT ON question_responses
    FOR EACH ROW
    EXECUTE FUNCTION set_academic_year_trigger();

-- 11. Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_vespa_scores_academic_year 
ON vespa_scores(academic_year);

CREATE INDEX IF NOT EXISTS idx_question_responses_academic_year
ON question_responses(academic_year);

CREATE INDEX IF NOT EXISTS idx_question_statistics_academic_year
ON question_statistics(academic_year);

CREATE INDEX IF NOT EXISTS idx_school_statistics_academic_year
ON school_statistics(academic_year);

-- 12. Add index on student email for faster lookups
CREATE INDEX IF NOT EXISTS idx_students_email 
ON students(lower(email));

-- 13. Verify the changes
DO $$
DECLARE
    vespa_2025_count INTEGER;
    quest_2025_count INTEGER;
    vespa_years TEXT[];
    quest_years TEXT[];
BEGIN
    -- Count 2025/2026 records
    SELECT COUNT(*) INTO vespa_2025_count
    FROM vespa_scores
    WHERE academic_year = '2025/2026';
    
    SELECT COUNT(*) INTO quest_2025_count
    FROM question_responses
    WHERE academic_year = '2025/2026';
    
    -- Get unique academic years
    SELECT ARRAY_AGG(DISTINCT academic_year ORDER BY academic_year) INTO vespa_years
    FROM vespa_scores
    WHERE academic_year IS NOT NULL;
    
    SELECT ARRAY_AGG(DISTINCT academic_year ORDER BY academic_year) INTO quest_years
    FROM question_responses
    WHERE academic_year IS NOT NULL;
    
    RAISE NOTICE '=== Migration Summary ===';
    RAISE NOTICE 'VESPA scores with 2025/2026: %', vespa_2025_count;
    RAISE NOTICE 'Question responses with 2025/2026: %', quest_2025_count;
    RAISE NOTICE 'VESPA academic years: %', vespa_years;
    RAISE NOTICE 'Question response academic years: %', quest_years;
END $$;

COMMIT;

-- ============================================================
-- END OF MIGRATION SCRIPT
-- ============================================================
-- 
-- To run this script:
-- psql $DATABASE_URL < fix_academic_year_migration.sql
-- 
-- Or in Supabase SQL Editor:
-- Copy and paste this entire script and click "Run"
-- ============================================================
