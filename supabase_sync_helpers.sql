-- Supabase helper functions and procedures for the sync process

-- Create sync_logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for querying recent sync logs
CREATE INDEX IF NOT EXISTS idx_sync_logs_started_at ON sync_logs(started_at DESC);

-- Function to calculate all statistics in one go
CREATE OR REPLACE FUNCTION calculate_all_statistics()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    current_academic_year VARCHAR(10);
    est RECORD;
    cycle_num INTEGER;
    element_name VARCHAR(20);
BEGIN
    -- Clear existing statistics for current year
    DELETE FROM school_statistics 
    WHERE academic_year IN (
        TO_CHAR(CURRENT_DATE, 'YYYY'),
        TO_CHAR(CURRENT_DATE, 'YYYY') || '-' || TO_CHAR(CURRENT_DATE + INTERVAL '1 year', 'YY'),
        TO_CHAR(CURRENT_DATE - INTERVAL '1 year', 'YYYY') || '-' || TO_CHAR(CURRENT_DATE, 'YY')
    );
    
    -- Loop through all establishments
    FOR est IN SELECT * FROM establishments LOOP
        -- Calculate academic year based on establishment location
        IF est.is_australian THEN
            current_academic_year := TO_CHAR(CURRENT_DATE, 'YYYY');
        ELSE
            -- UK academic year
            IF EXTRACT(MONTH FROM CURRENT_DATE) >= 8 THEN
                current_academic_year := TO_CHAR(CURRENT_DATE, 'YYYY') || '-' || TO_CHAR(CURRENT_DATE + INTERVAL '1 year', 'YY');
            ELSE
                current_academic_year := TO_CHAR(CURRENT_DATE - INTERVAL '1 year', 'YYYY') || '-' || TO_CHAR(CURRENT_DATE, 'YY');
            END IF;
        END IF;
        
        -- Loop through cycles
        FOR cycle_num IN 1..3 LOOP
            -- Loop through elements
            FOR element_name IN SELECT unnest(ARRAY['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']) LOOP
                -- Insert statistics
                INSERT INTO school_statistics (
                    establishment_id,
                    cycle,
                    academic_year,
                    element,
                    average,
                    count,
                    min_value,
                    max_value,
                    std_dev
                )
                SELECT 
                    est.id,
                    cycle_num,
                    current_academic_year,
                    element_name,
                    AVG(CASE 
                        WHEN element_name = 'vision' THEN vs.vision
                        WHEN element_name = 'effort' THEN vs.effort
                        WHEN element_name = 'systems' THEN vs.systems
                        WHEN element_name = 'practice' THEN vs.practice
                        WHEN element_name = 'attitude' THEN vs.attitude
                        WHEN element_name = 'overall' THEN vs.overall
                    END)::NUMERIC(5,2),
                    COUNT(CASE 
                        WHEN element_name = 'vision' AND vs.vision IS NOT NULL THEN 1
                        WHEN element_name = 'effort' AND vs.effort IS NOT NULL THEN 1
                        WHEN element_name = 'systems' AND vs.systems IS NOT NULL THEN 1
                        WHEN element_name = 'practice' AND vs.practice IS NOT NULL THEN 1
                        WHEN element_name = 'attitude' AND vs.attitude IS NOT NULL THEN 1
                        WHEN element_name = 'overall' AND vs.overall IS NOT NULL THEN 1
                    END),
                    MIN(CASE 
                        WHEN element_name = 'vision' THEN vs.vision
                        WHEN element_name = 'effort' THEN vs.effort
                        WHEN element_name = 'systems' THEN vs.systems
                        WHEN element_name = 'practice' THEN vs.practice
                        WHEN element_name = 'attitude' THEN vs.attitude
                        WHEN element_name = 'overall' THEN vs.overall
                    END),
                    MAX(CASE 
                        WHEN element_name = 'vision' THEN vs.vision
                        WHEN element_name = 'effort' THEN vs.effort
                        WHEN element_name = 'systems' THEN vs.systems
                        WHEN element_name = 'practice' THEN vs.practice
                        WHEN element_name = 'attitude' THEN vs.attitude
                        WHEN element_name = 'overall' THEN vs.overall
                    END),
                    STDDEV(CASE 
                        WHEN element_name = 'vision' THEN vs.vision
                        WHEN element_name = 'effort' THEN vs.effort
                        WHEN element_name = 'systems' THEN vs.systems
                        WHEN element_name = 'practice' THEN vs.practice
                        WHEN element_name = 'attitude' THEN vs.attitude
                        WHEN element_name = 'overall' THEN vs.overall
                    END)::NUMERIC(5,2)
                FROM vespa_scores vs
                JOIN students s ON vs.student_id = s.id
                WHERE s.establishment_id = est.id
                AND vs.cycle = cycle_num
                AND vs.academic_year = current_academic_year
                HAVING COUNT(CASE 
                    WHEN element_name = 'vision' AND vs.vision IS NOT NULL THEN 1
                    WHEN element_name = 'effort' AND vs.effort IS NOT NULL THEN 1
                    WHEN element_name = 'systems' AND vs.systems IS NOT NULL THEN 1
                    WHEN element_name = 'practice' AND vs.practice IS NOT NULL THEN 1
                    WHEN element_name = 'attitude' AND vs.attitude IS NOT NULL THEN 1
                    WHEN element_name = 'overall' AND vs.overall IS NOT NULL THEN 1
                END) > 0
                ON CONFLICT (establishment_id, cycle, academic_year, element) 
                DO UPDATE SET
                    average = EXCLUDED.average,
                    count = EXCLUDED.count,
                    min_value = EXCLUDED.min_value,
                    max_value = EXCLUDED.max_value,
                    std_dev = EXCLUDED.std_dev,
                    updated_at = NOW();
            END LOOP;
        END LOOP;
    END LOOP;
END;
$$;

-- View to check sync progress
CREATE OR REPLACE VIEW sync_progress AS
SELECT 
    (SELECT COUNT(*) FROM establishments) as total_establishments,
    (SELECT COUNT(*) FROM students) as total_students,
    (SELECT COUNT(*) FROM vespa_scores) as total_vespa_scores,
    (SELECT COUNT(DISTINCT student_id || '-' || cycle) FROM vespa_scores) as unique_student_cycles,
    (SELECT COUNT(*) FROM question_responses) as total_question_responses,
    (SELECT COUNT(*) FROM school_statistics) as total_statistics,
    (SELECT MAX(started_at) FROM sync_logs WHERE status = 'completed') as last_successful_sync,
    (SELECT status FROM sync_logs ORDER BY started_at DESC LIMIT 1) as latest_sync_status;

-- Function to check data health
CREATE OR REPLACE FUNCTION check_data_health()
RETURNS TABLE (
    check_name VARCHAR,
    status VARCHAR,
    details TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Check for students without establishments
    RETURN QUERY
    SELECT 
        'Students without establishments'::VARCHAR,
        CASE WHEN COUNT(*) > 0 THEN 'WARNING' ELSE 'OK' END::VARCHAR,
        'Count: ' || COUNT(*)::TEXT
    FROM students 
    WHERE establishment_id IS NULL;
    
    -- Check for VESPA scores without valid students
    RETURN QUERY
    SELECT 
        'VESPA scores with invalid students'::VARCHAR,
        CASE WHEN COUNT(*) > 0 THEN 'ERROR' ELSE 'OK' END::VARCHAR,
        'Count: ' || COUNT(*)::TEXT
    FROM vespa_scores vs
    LEFT JOIN students s ON vs.student_id = s.id
    WHERE s.id IS NULL;
    
    -- Check for duplicate VESPA scores
    RETURN QUERY
    SELECT 
        'Duplicate VESPA scores'::VARCHAR,
        CASE WHEN COUNT(*) > 0 THEN 'WARNING' ELSE 'OK' END::VARCHAR,
        'Count: ' || COUNT(*)::TEXT
    FROM (
        SELECT student_id, cycle, COUNT(*) as cnt
        FROM vespa_scores
        GROUP BY student_id, cycle
        HAVING COUNT(*) > 1
    ) duplicates;
    
    -- Check for missing academic years
    RETURN QUERY
    SELECT 
        'VESPA scores without academic year'::VARCHAR,
        CASE WHEN COUNT(*) > 0 THEN 'WARNING' ELSE 'OK' END::VARCHAR,
        'Count: ' || COUNT(*)::TEXT
    FROM vespa_scores
    WHERE academic_year IS NULL;
    
    -- Check for incomplete VESPA scores (missing elements)
    RETURN QUERY
    SELECT 
        'Incomplete VESPA scores'::VARCHAR,
        CASE WHEN COUNT(*) > 0 THEN 'INFO' ELSE 'OK' END::VARCHAR,
        'Count: ' || COUNT(*)::TEXT
    FROM vespa_scores
    WHERE (vision IS NULL OR effort IS NULL OR systems IS NULL OR 
           practice IS NULL OR attitude IS NULL) 
    AND overall IS NOT NULL;
END;
$$;

-- Create indexes for better sync performance
CREATE INDEX IF NOT EXISTS idx_students_knack_id ON students(knack_id);
CREATE INDEX IF NOT EXISTS idx_students_establishment_id ON students(establishment_id);
CREATE INDEX IF NOT EXISTS idx_vespa_scores_student_cycle ON vespa_scores(student_id, cycle);
CREATE INDEX IF NOT EXISTS idx_vespa_scores_academic_year ON vespa_scores(academic_year);
CREATE INDEX IF NOT EXISTS idx_question_responses_student_cycle ON question_responses(student_id, cycle);