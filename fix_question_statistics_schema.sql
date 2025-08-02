-- Fix question_statistics table to support comprehensive QLA calculations

-- First, drop the incorrect constraint and columns
ALTER TABLE question_statistics 
DROP COLUMN IF EXISTS mean_response,
DROP COLUMN IF EXISTS response_count;

-- Ensure we have all the correct columns
ALTER TABLE question_statistics 
ADD COLUMN IF NOT EXISTS mean DECIMAL(4,2),
ADD COLUMN IF NOT EXISTS count INTEGER,
ADD COLUMN IF NOT EXISTS mode INTEGER,
ADD COLUMN IF NOT EXISTS percentile_25 DECIMAL(4,2),
ADD COLUMN IF NOT EXISTS percentile_75 DECIMAL(4,2);

-- Update the distribution column comment
COMMENT ON COLUMN question_statistics.distribution IS 'JSON array with counts for scores 1-5, e.g. [10, 20, 45, 15, 10]';

-- Create a view for top/bottom questions per establishment and cycle
CREATE OR REPLACE VIEW question_rankings AS
WITH ranked_questions AS (
    SELECT 
        qs.*,
        ROW_NUMBER() OVER (PARTITION BY establishment_id, cycle, academic_year ORDER BY mean DESC) as rank_desc,
        ROW_NUMBER() OVER (PARTITION BY establishment_id, cycle, academic_year ORDER BY mean ASC) as rank_asc,
        COUNT(*) OVER (PARTITION BY establishment_id, cycle, academic_year) as total_questions
    FROM question_statistics qs
    WHERE mean IS NOT NULL
)
SELECT 
    *,
    CASE 
        WHEN rank_desc <= 5 THEN 'TOP_5'
        WHEN rank_asc <= 5 THEN 'BOTTOM_5'
        ELSE 'MIDDLE'
    END as performance_category
FROM ranked_questions;

-- Create an index for faster ranking queries
CREATE INDEX IF NOT EXISTS idx_question_stats_mean ON question_statistics(establishment_id, cycle, academic_year, mean DESC);

-- Create a function to calculate question statistics with all metrics
CREATE OR REPLACE FUNCTION calculate_question_statistics_enhanced()
RETURNS void AS $$
BEGIN
    -- Clear existing question statistics
    DELETE FROM question_statistics WHERE true;
    
    -- Calculate comprehensive statistics for each question
    INSERT INTO question_statistics (
        establishment_id,
        question_id,
        cycle,
        academic_year,
        mean,
        std_dev,
        count,
        mode,
        percentile_25,
        percentile_75,
        distribution
    )
    WITH question_data AS (
        SELECT 
            s.establishment_id,
            qr.question_id,
            qr.cycle,
            CASE 
                WHEN e.is_australian AND EXTRACT(MONTH FROM CURRENT_DATE) >= 7 
                    THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
                WHEN e.is_australian 
                    THEN (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
                WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 
                    THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
                ELSE 
                    (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
            END as academic_year,
            qr.response_value
        FROM question_responses qr
        JOIN students s ON qr.student_id = s.id
        JOIN establishments e ON s.establishment_id = e.id
        WHERE qr.response_value IS NOT NULL
    ),
    question_aggregates AS (
        SELECT 
            establishment_id,
            question_id,
            cycle,
            academic_year,
            AVG(response_value) as mean,
            STDDEV(response_value) as std_dev,
            COUNT(*) as count,
            MODE() WITHIN GROUP (ORDER BY response_value) as mode,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY response_value) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY response_value) as percentile_75,
            -- Calculate distribution
            jsonb_build_array(
                COUNT(*) FILTER (WHERE response_value = 1),
                COUNT(*) FILTER (WHERE response_value = 2),
                COUNT(*) FILTER (WHERE response_value = 3),
                COUNT(*) FILTER (WHERE response_value = 4),
                COUNT(*) FILTER (WHERE response_value = 5)
            ) as distribution
        FROM question_data
        GROUP BY establishment_id, question_id, cycle, academic_year
    )
    SELECT * FROM question_aggregates;
    
END;
$$ LANGUAGE plpgsql;

-- Also create national question statistics
CREATE TABLE IF NOT EXISTS national_question_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id VARCHAR(50) NOT NULL,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    academic_year VARCHAR(10),
    mean DECIMAL(4,2),
    std_dev DECIMAL(4,2),
    count INTEGER,
    mode INTEGER,
    percentile_25 DECIMAL(4,2),
    percentile_75 DECIMAL(4,2),
    distribution JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(question_id, cycle, academic_year)
);

-- Function to calculate national question statistics
CREATE OR REPLACE FUNCTION calculate_national_question_statistics()
RETURNS void AS $$
BEGIN
    -- Clear existing national question statistics
    DELETE FROM national_question_statistics WHERE true;
    
    -- Aggregate across all establishments
    INSERT INTO national_question_statistics (
        question_id,
        cycle,
        academic_year,
        mean,
        std_dev,
        count,
        mode,
        percentile_25,
        percentile_75,
        distribution
    )
    SELECT 
        question_id,
        cycle,
        academic_year,
        -- Weighted average for mean
        SUM(mean * count) / SUM(count) as mean,
        -- Pooled standard deviation
        SQRT(SUM((count - 1) * POWER(std_dev, 2)) / (SUM(count) - COUNT(*))) as std_dev,
        SUM(count) as count,
        -- Most common mode across schools
        MODE() WITHIN GROUP (ORDER BY mode) as mode,
        -- Weighted percentiles
        AVG(percentile_25) as percentile_25,
        AVG(percentile_75) as percentile_75,
        -- Aggregate distribution
        jsonb_build_array(
            SUM((distribution->0)::int),
            SUM((distribution->1)::int),
            SUM((distribution->2)::int),
            SUM((distribution->3)::int),
            SUM((distribution->4)::int)
        ) as distribution
    FROM question_statistics
    WHERE mean IS NOT NULL
    GROUP BY question_id, cycle, academic_year;
    
END;
$$ LANGUAGE plpgsql;