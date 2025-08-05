-- Add ERI_score column to national_statistics table
ALTER TABLE national_statistics
ADD COLUMN IF NOT EXISTS eri_score numeric;

-- Drop the existing check constraint
ALTER TABLE national_statistics 
DROP CONSTRAINT IF EXISTS national_statistics_element_check;

-- Recreate the constraint to include 'ERI'
ALTER TABLE national_statistics 
ADD CONSTRAINT national_statistics_element_check 
CHECK (element IN ('vision', 'effort', 'systems', 'practice', 'attitude', 'overall', 'ERI'));

-- Also update school_statistics constraint if it exists
ALTER TABLE school_statistics 
DROP CONSTRAINT IF EXISTS school_statistics_element_check;

ALTER TABLE school_statistics 
ADD CONSTRAINT school_statistics_element_check 
CHECK (element IN ('vision', 'effort', 'systems', 'practice', 'attitude', 'overall', 'ERI'));

-- Create or replace function to calculate national ERI for each cycle
CREATE OR REPLACE FUNCTION calculate_national_eri()
RETURNS void AS $$
BEGIN
    -- Clear existing ERI entries
    DELETE FROM national_statistics WHERE element = 'ERI';
    
    -- Calculate and insert ERI for each cycle and academic year
    INSERT INTO national_statistics (
        id,
        cycle,
        academic_year,
        element,
        mean,
        std_dev,
        count,
        percentile_25,
        percentile_50,
        percentile_75,
        eri_score,
        calculated_at
    )
    SELECT 
        gen_random_uuid() as id,
        qr.cycle,
        qr.academic_year,
        'ERI' as element,
        AVG(qr.response_value) as mean,
        STDDEV(qr.response_value) as std_dev,
        COUNT(DISTINCT qr.student_id) as count,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY qr.response_value) as percentile_25,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY qr.response_value) as percentile_50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY qr.response_value) as percentile_75,
        AVG(qr.response_value) as eri_score,
        CURRENT_TIMESTAMP as calculated_at
    FROM question_responses qr
    WHERE qr.question_id IN ('outcome_q_confident', 'outcome_q_equipped', 'outcome_q_support')
    AND qr.response_value IS NOT NULL
    AND qr.academic_year IS NOT NULL
    GROUP BY qr.cycle, qr.academic_year
    HAVING COUNT(DISTINCT qr.student_id) > 10;  -- Only calculate if we have enough responses
    
    -- Also update the eri_score for existing VESPA element rows
    UPDATE national_statistics ns
    SET eri_score = (
        SELECT AVG(qr.response_value)
        FROM question_responses qr
        WHERE qr.question_id IN ('outcome_q_confident', 'outcome_q_equipped', 'outcome_q_support')
        AND qr.response_value IS NOT NULL
        AND qr.cycle = ns.cycle
        AND (ns.academic_year IS NULL OR qr.academic_year = ns.academic_year)
    )
    WHERE ns.element IN ('vision', 'effort', 'systems', 'practice', 'attitude', 'overall');
    
END;
$$ LANGUAGE plpgsql;

-- Execute the function to populate ERI scores
SELECT calculate_national_eri();

-- Create a view for easy access to national ERI by cycle
CREATE OR REPLACE VIEW national_eri_by_cycle AS
SELECT 
    cycle,
    academic_year,
    eri_score as national_eri,
    count as student_count,
    calculated_at
FROM national_statistics
WHERE element = 'ERI'
ORDER BY cycle, academic_year DESC;

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_national_statistics_element_cycle 
ON national_statistics(element, cycle);

-- Sample query to verify the data
SELECT * FROM national_eri_by_cycle;