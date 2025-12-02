-- Fix RPC to also update current_cycle column
-- This ensures vespa_students.current_cycle stays in sync with latest_vespa_scores

CREATE OR REPLACE FUNCTION sync_latest_vespa_scores_to_student(p_student_email TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_latest_scores JSONB;
    v_current_academic_year TEXT;
    v_current_cycle INTEGER;
BEGIN
    -- Get student's current academic year from vespa_students (if exists)
    SELECT current_academic_year INTO v_current_academic_year
    FROM vespa_students
    WHERE email = p_student_email;
    
    -- Get latest VESPA scores with multi-year support
    IF v_current_academic_year IS NOT NULL THEN
        -- Try current academic year first
        SELECT jsonb_build_object(
            'cycle', vsc.cycle,
            'academic_year', vsc.academic_year,
            'vision', vsc.vision,
            'effort', vsc.effort,
            'systems', vsc.systems,
            'practice', vsc.practice,
            'attitude', vsc.attitude,
            'overall', vsc.overall,
            'completion_date', vsc.completion_date,
            'synced_at', NOW()
        ), vsc.cycle
        INTO v_latest_scores, v_current_cycle
        FROM vespa_scores vsc
        WHERE vsc.student_email = p_student_email
          AND vsc.academic_year = v_current_academic_year
          AND vsc.vision IS NOT NULL
          AND vsc.overall IS NOT NULL
        ORDER BY vsc.completion_date DESC, vsc.cycle DESC
        LIMIT 1;
    END IF;
    
    -- If no scores in current year, get absolute latest
    IF v_latest_scores IS NULL THEN
        SELECT jsonb_build_object(
            'cycle', vsc.cycle,
            'academic_year', vsc.academic_year,
            'vision', vsc.vision,
            'effort', vsc.effort,
            'systems', vsc.systems,
            'practice', vsc.practice,
            'attitude', vsc.attitude,
            'overall', vsc.overall,
            'completion_date', vsc.completion_date,
            'synced_at', NOW(),
            'note', 'From previous academic year'
        ), vsc.cycle
        INTO v_latest_scores, v_current_cycle
        FROM vespa_scores vsc
        WHERE vsc.student_email = p_student_email
          AND vsc.vision IS NOT NULL
          AND vsc.overall IS NOT NULL
        ORDER BY vsc.completion_date DESC, vsc.cycle DESC
        LIMIT 1;
    END IF;
    
    IF v_latest_scores IS NULL THEN
        RAISE NOTICE 'No VESPA scores found for student: %', p_student_email;
        RETURN NULL;
    END IF;
    
    -- Update or insert into vespa_students (NOW ALSO UPDATES current_cycle!)
    INSERT INTO vespa_students (
        email,
        latest_vespa_scores,
        current_cycle,
        updated_at
    )
    VALUES (
        p_student_email,
        v_latest_scores,
        v_current_cycle,
        NOW()
    )
    ON CONFLICT (email) 
    DO UPDATE SET
        latest_vespa_scores = EXCLUDED.latest_vespa_scores,
        current_cycle = EXCLUDED.current_cycle,
        updated_at = NOW();
    
    RAISE NOTICE 'Updated latest_vespa_scores for %: cycle %, year %', 
        p_student_email,
        v_latest_scores->>'cycle',
        v_latest_scores->>'academic_year';
    
    RETURN v_latest_scores;
END;
$$;

-- Run for Cash to fix the mismatch
SELECT sync_latest_vespa_scores_to_student('cali@vespa.academy');

-- Verify it worked
SELECT 
    email,
    current_cycle,
    latest_vespa_scores->>'cycle' as jsonb_cycle,
    latest_vespa_scores->>'vision' as vision,
    latest_vespa_scores->>'completion_date' as completion_date
FROM vespa_students
WHERE email = 'cali@vespa.academy';

