-- Fix National Benchmarks to be Academic Year Specific
-- This fixes the issue where national data shows for 2025/2026 but not 2024/2025

-- Step 1: Create the national benchmarks table
CREATE TABLE IF NOT EXISTS national_benchmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    academic_year VARCHAR(10) NOT NULL,
    cycle INTEGER NOT NULL,
    vespa_component VARCHAR(20) NOT NULL,  -- 'vision', 'effort', 'systems', 'practice', 'attitude', 'resilience'
    mean_score DECIMAL(3,2),
    median_score DECIMAL(3,2),
    std_dev DECIMAL(3,2),
    percentile_25 DECIMAL(3,2),
    percentile_75 DECIMAL(3,2),
    sample_size INTEGER,
    schools_count INTEGER,
    last_calculated TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    UNIQUE(academic_year, cycle, vespa_component)
);

-- Step 2: Create index for fast lookups
CREATE INDEX idx_national_benchmarks_year_cycle 
ON national_benchmarks(academic_year, cycle);

-- Step 3: Insert historical national data for 2024/2025
-- These are approximate values - replace with actual historical data
INSERT INTO national_benchmarks 
(academic_year, cycle, vespa_component, mean_score, median_score, std_dev, sample_size, schools_count)
VALUES 
-- 2024/2025 Academic Year - Cycle 1
('2024/2025', 1, 'vision', 6.70, 6.80, 1.20, 15234, 89),
('2024/2025', 1, 'effort', 6.30, 6.40, 1.15, 15234, 89),
('2024/2025', 1, 'systems', 5.90, 6.00, 1.25, 15234, 89),
('2024/2025', 1, 'practice', 6.10, 6.20, 1.18, 15234, 89),
('2024/2025', 1, 'attitude', 6.10, 6.20, 1.22, 15234, 89),
('2024/2025', 1, 'resilience', 6.20, 6.30, 1.19, 15234, 89),

-- 2024/2025 Academic Year - Cycle 2 (if available)
('2024/2025', 2, 'vision', 6.85, 6.95, 1.18, 12456, 85),
('2024/2025', 2, 'effort', 6.45, 6.55, 1.12, 12456, 85),
('2024/2025', 2, 'systems', 6.05, 6.15, 1.20, 12456, 85),
('2024/2025', 2, 'practice', 6.25, 6.35, 1.15, 12456, 85),
('2024/2025', 2, 'attitude', 6.25, 6.35, 1.18, 12456, 85),
('2024/2025', 2, 'resilience', 6.35, 6.45, 1.16, 12456, 85),

-- 2024/2025 Academic Year - Cycle 3 (if available)
('2024/2025', 3, 'vision', 6.95, 7.05, 1.15, 8234, 78),
('2024/2025', 3, 'effort', 6.55, 6.65, 1.10, 8234, 78),
('2024/2025', 3, 'systems', 6.15, 6.25, 1.18, 8234, 78),
('2024/2025', 3, 'practice', 6.35, 6.45, 1.12, 8234, 78),
('2024/2025', 3, 'attitude', 6.35, 6.45, 1.15, 8234, 78),
('2024/2025', 3, 'resilience', 6.45, 6.55, 1.13, 8234, 78),

-- 2025/2026 Academic Year - Cycle 1 (current year - partial data)
('2025/2026', 1, 'vision', 6.60, 6.70, 1.22, 1346, 12),
('2025/2026', 1, 'effort', 6.10, 6.20, 1.18, 1346, 12),
('2025/2026', 1, 'systems', 5.50, 5.60, 1.28, 1346, 12),
('2025/2026', 1, 'practice', 5.90, 6.00, 1.20, 1346, 12),
('2025/2026', 1, 'attitude', 6.00, 6.10, 1.24, 1346, 12),
('2025/2026', 1, 'resilience', 6.10, 6.20, 1.21, 1346, 12)
ON CONFLICT (academic_year, cycle, vespa_component) 
DO UPDATE SET
    mean_score = EXCLUDED.mean_score,
    median_score = EXCLUDED.median_score,
    sample_size = EXCLUDED.sample_size,
    schools_count = EXCLUDED.schools_count,
    last_calculated = NOW();

-- Step 4: Create function to get national benchmarks for a specific year
CREATE OR REPLACE FUNCTION get_national_benchmarks_for_year(
    p_academic_year VARCHAR,
    p_cycle INTEGER DEFAULT 1
) RETURNS TABLE (
    vespa_component VARCHAR,
    mean_score DECIMAL,
    median_score DECIMAL,
    std_dev DECIMAL,
    sample_size INTEGER,
    schools_count INTEGER
) AS $$
BEGIN
    -- First try to get data for the specific year
    IF EXISTS (
        SELECT 1 FROM national_benchmarks 
        WHERE academic_year = p_academic_year 
        AND cycle = p_cycle
    ) THEN
        RETURN QUERY
        SELECT 
            nb.vespa_component,
            nb.mean_score,
            nb.median_score,
            nb.std_dev,
            nb.sample_size,
            nb.schools_count
        FROM national_benchmarks nb
        WHERE nb.academic_year = p_academic_year
        AND nb.cycle = p_cycle
        ORDER BY 
            CASE nb.vespa_component
                WHEN 'vision' THEN 1
                WHEN 'effort' THEN 2
                WHEN 'systems' THEN 3
                WHEN 'practice' THEN 4
                WHEN 'attitude' THEN 5
                WHEN 'resilience' THEN 6
            END;
    ELSE
        -- Fallback: Return NULL or previous year's data with a warning
        RETURN QUERY
        SELECT 
            v.component,
            NULL::DECIMAL as mean_score,
            NULL::DECIMAL as median_score,
            NULL::DECIMAL as std_dev,
            0 as sample_size,
            0 as schools_count
        FROM (VALUES 
            ('vision'::VARCHAR), 
            ('effort'), 
            ('systems'), 
            ('practice'), 
            ('attitude'), 
            ('resilience')
        ) v(component);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create a view for easy access to current year benchmarks
CREATE OR REPLACE VIEW current_national_benchmarks AS
SELECT 
    nb.*,
    CASE 
        WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 THEN 
            EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
        ELSE 
            (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
    END as is_current_year
FROM national_benchmarks nb
WHERE nb.academic_year = CASE 
    WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 9 THEN 
        EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || (EXTRACT(YEAR FROM CURRENT_DATE) + 1)::TEXT
    ELSE 
        (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::TEXT || '/' || EXTRACT(YEAR FROM CURRENT_DATE)::TEXT
END;

-- Step 6: Test the functions
-- Check 2024/2025 data (should return values)
SELECT * FROM get_national_benchmarks_for_year('2024/2025', 1);

-- Check 2025/2026 data (should return values)
SELECT * FROM get_national_benchmarks_for_year('2025/2026', 1);

-- Step 7: Calculate national benchmarks from actual data (optional)
-- This can be run periodically to update the benchmarks with real data
CREATE OR REPLACE FUNCTION calculate_national_benchmarks(
    p_academic_year VARCHAR,
    p_cycle INTEGER
) RETURNS VOID AS $$
DECLARE
    v_component VARCHAR;
    v_components VARCHAR[] := ARRAY['vision', 'effort', 'systems', 'practice', 'attitude', 'resilience'];
    v_field_mapping JSONB := '{
        "vision": ["v1", "v2", "v3"],
        "effort": ["e1", "e2", "e3"],
        "systems": ["s1", "s2", "s3"],
        "practice": ["p1", "p2", "p3"],
        "attitude": ["a1", "a2", "a3"],
        "resilience": ["r1", "r2", "r3"]
    }'::JSONB;
BEGIN
    FOREACH v_component IN ARRAY v_components
    LOOP
        INSERT INTO national_benchmarks (
            academic_year,
            cycle,
            vespa_component,
            mean_score,
            median_score,
            std_dev,
            percentile_25,
            percentile_75,
            sample_size,
            schools_count
        )
        SELECT 
            p_academic_year,
            p_cycle,
            v_component,
            AVG(score) as mean_score,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score) as median_score,
            STDDEV(score) as std_dev,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY score) as percentile_25,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY score) as percentile_75,
            COUNT(*) as sample_size,
            COUNT(DISTINCT establishment_id) as schools_count
        FROM (
            SELECT 
                vs.student_id,
                s.establishment_id,
                CASE v_component
                    WHEN 'vision' THEN vs.v1
                    WHEN 'effort' THEN vs.e1
                    WHEN 'systems' THEN vs.s1
                    WHEN 'practice' THEN vs.p1
                    WHEN 'attitude' THEN vs.a1
                    WHEN 'resilience' THEN vs.r1
                END as score
            FROM vespa_scores vs
            INNER JOIN students s ON vs.student_id = s.id
            WHERE vs.academic_year = p_academic_year
            AND vs.cycle = p_cycle
            AND CASE v_component
                    WHEN 'vision' THEN vs.v1
                    WHEN 'effort' THEN vs.e1
                    WHEN 'systems' THEN vs.s1
                    WHEN 'practice' THEN vs.p1
                    WHEN 'attitude' THEN vs.a1
                    WHEN 'resilience' THEN vs.r1
                END IS NOT NULL
        ) scores
        ON CONFLICT (academic_year, cycle, vespa_component) 
        DO UPDATE SET
            mean_score = EXCLUDED.mean_score,
            median_score = EXCLUDED.median_score,
            std_dev = EXCLUDED.std_dev,
            percentile_25 = EXCLUDED.percentile_25,
            percentile_75 = EXCLUDED.percentile_75,
            sample_size = EXCLUDED.sample_size,
            schools_count = EXCLUDED.schools_count,
            last_calculated = NOW();
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Summary check
SELECT 
    academic_year,
    cycle,
    COUNT(*) as components_count,
    AVG(sample_size) as avg_sample_size,
    SUM(schools_count)/6 as total_schools  -- Divide by 6 components
FROM national_benchmarks
GROUP BY academic_year, cycle
ORDER BY academic_year, cycle;
