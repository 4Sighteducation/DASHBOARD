-- Prepare database for Comparative Analytics ("Vs" Feature)

-- 1. Create materialized view for fast comparisons
CREATE MATERIALIZED VIEW IF NOT EXISTS comparative_metrics AS
SELECT 
    -- School info
    e.id as establishment_id,
    e.name as establishment_name,
    
    -- Student demographics
    s.id as student_id,
    s.year_group,
    s.faculty,
    s."group",
    
    -- VESPA scores by cycle
    vs.cycle,
    vs.academic_year,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date,
    
    -- Calculated fields for comparisons
    CASE 
        WHEN vs.overall >= 75 THEN 'High'
        WHEN vs.overall >= 50 THEN 'Medium'
        ELSE 'Low'
    END as performance_band,
    
    -- Previous cycle scores for delta calculations
    LAG(vs.overall) OVER (PARTITION BY s.id ORDER BY vs.cycle) as previous_overall,
    LAG(vs.vision) OVER (PARTITION BY s.id ORDER BY vs.cycle) as previous_vision,
    LAG(vs.effort) OVER (PARTITION BY s.id ORDER BY vs.cycle) as previous_effort,
    LAG(vs.systems) OVER (PARTITION BY s.id ORDER BY vs.cycle) as previous_systems,
    LAG(vs.practice) OVER (PARTITION BY s.id ORDER BY vs.cycle) as previous_practice,
    LAG(vs.attitude) OVER (PARTITION BY s.id ORDER BY vs.cycle) as previous_attitude
    
FROM vespa_scores vs
JOIN students s ON vs.student_id = s.id
JOIN establishments e ON s.establishment_id = e.id;

-- Create indexes for fast filtering
CREATE INDEX idx_comparative_establishment ON comparative_metrics(establishment_id);
CREATE INDEX idx_comparative_year_group ON comparative_metrics(year_group);
CREATE INDEX idx_comparative_faculty ON comparative_metrics(faculty);
CREATE INDEX idx_comparative_group ON comparative_metrics("group");
CREATE INDEX idx_comparative_cycle ON comparative_metrics(cycle);
CREATE INDEX idx_comparative_academic_year ON comparative_metrics(academic_year);

-- 2. Create comparison summary table
CREATE TABLE IF NOT EXISTS comparison_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    establishment_id UUID REFERENCES establishments(id),
    comparison_type VARCHAR(50), -- 'cycle_vs_cycle', 'group_vs_group', etc.
    dimension1 VARCHAR(100),
    dimension2 VARCHAR(100),
    metric VARCHAR(50), -- 'overall', 'vision', etc.
    
    -- Statistical results
    group1_mean DECIMAL(5,2),
    group1_std_dev DECIMAL(5,2),
    group1_count INTEGER,
    
    group2_mean DECIMAL(5,2),
    group2_std_dev DECIMAL(5,2),
    group2_count INTEGER,
    
    -- Comparison metrics
    mean_difference DECIMAL(5,2),
    percent_change DECIMAL(5,2),
    cohen_d DECIMAL(5,2), -- Effect size
    p_value DECIMAL(10,6), -- Statistical significance
    
    -- AI insights placeholder
    ai_insights JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '24 hours'
);

-- 3. Function to calculate comparison statistics
CREATE OR REPLACE FUNCTION calculate_comparison(
    p_establishment_id UUID,
    p_comparison_type VARCHAR,
    p_dimension1 VARCHAR,
    p_dimension2 VARCHAR,
    p_metric VARCHAR DEFAULT 'overall'
)
RETURNS TABLE (
    group1_mean DECIMAL,
    group1_std_dev DECIMAL,
    group1_count INTEGER,
    group2_mean DECIMAL,
    group2_std_dev DECIMAL,
    group2_count INTEGER,
    mean_difference DECIMAL,
    percent_change DECIMAL,
    cohen_d DECIMAL
) AS $$
DECLARE
    v_group1_mean DECIMAL;
    v_group1_std_dev DECIMAL;
    v_group1_count INTEGER;
    v_group2_mean DECIMAL;
    v_group2_std_dev DECIMAL;
    v_group2_count INTEGER;
    v_pooled_std_dev DECIMAL;
BEGIN
    -- Example: Compare Cycle 1 vs Cycle 3
    IF p_comparison_type = 'cycle_vs_cycle' THEN
        -- Group 1 statistics
        SELECT AVG(overall), STDDEV(overall), COUNT(*)
        INTO v_group1_mean, v_group1_std_dev, v_group1_count
        FROM comparative_metrics
        WHERE establishment_id = p_establishment_id
        AND cycle = p_dimension1::INTEGER;
        
        -- Group 2 statistics
        SELECT AVG(overall), STDDEV(overall), COUNT(*)
        INTO v_group2_mean, v_group2_std_dev, v_group2_count
        FROM comparative_metrics
        WHERE establishment_id = p_establishment_id
        AND cycle = p_dimension2::INTEGER;
    
    ELSIF p_comparison_type = 'group_vs_group' THEN
        -- Compare different student groups
        SELECT AVG(overall), STDDEV(overall), COUNT(*)
        INTO v_group1_mean, v_group1_std_dev, v_group1_count
        FROM comparative_metrics
        WHERE establishment_id = p_establishment_id
        AND "group" = p_dimension1;
        
        SELECT AVG(overall), STDDEV(overall), COUNT(*)
        INTO v_group2_mean, v_group2_std_dev, v_group2_count
        FROM comparative_metrics
        WHERE establishment_id = p_establishment_id
        AND "group" = p_dimension2;
    END IF;
    
    -- Calculate effect size (Cohen's d)
    v_pooled_std_dev := SQRT(
        ((v_group1_count - 1) * POWER(v_group1_std_dev, 2) + 
         (v_group2_count - 1) * POWER(v_group2_std_dev, 2)) / 
        (v_group1_count + v_group2_count - 2)
    );
    
    RETURN QUERY SELECT
        v_group1_mean,
        v_group1_std_dev,
        v_group1_count,
        v_group2_mean,
        v_group2_std_dev,
        v_group2_count,
        v_group2_mean - v_group1_mean as mean_difference,
        CASE 
            WHEN v_group1_mean > 0 THEN ((v_group2_mean - v_group1_mean) / v_group1_mean * 100)
            ELSE 0
        END as percent_change,
        CASE 
            WHEN v_pooled_std_dev > 0 THEN (v_group2_mean - v_group1_mean) / v_pooled_std_dev
            ELSE 0
        END as cohen_d;
END;
$$ LANGUAGE plpgsql;

-- 4. Create report templates table for advanced reporting
CREATE TABLE IF NOT EXISTS report_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_type VARCHAR(50), -- 'standard', 'comparative', 'progress'
    
    -- Report configuration
    filters JSONB, -- Which filters to apply
    metrics JSONB, -- Which metrics to include
    visualizations JSONB, -- Chart types and config
    
    -- AI prompts for insights
    ai_prompt_template TEXT,
    
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Sample report templates
INSERT INTO report_templates (name, description, template_type, filters, metrics, visualizations)
VALUES 
(
    'Cycle Progression Report',
    'Compare student progress across all cycles',
    'comparative',
    '{"cycles": ["1", "2", "3"]}',
    '["overall", "vision", "effort", "systems", "practice", "attitude"]',
    '[{"type": "line", "metric": "overall", "groupBy": "cycle"}]'
),
(
    'Faculty Comparison Report',
    'Compare performance across different faculties',
    'comparative',
    '{"groupBy": "faculty"}',
    '["overall", "vision", "effort", "systems", "practice", "attitude"]',
    '[{"type": "bar", "metric": "overall", "groupBy": "faculty"}]'
);

-- Refresh the materialized view (run this after data sync)
-- REFRESH MATERIALIZED VIEW comparative_metrics;