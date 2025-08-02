-- Create optimized views for Question Level Analysis (QLA) dashboard

-- View for easy access to top/bottom questions with full details
CREATE OR REPLACE VIEW qla_question_performance AS
WITH question_details AS (
    SELECT 
        qs.*,
        -- Add ranking within establishment/cycle
        RANK() OVER (PARTITION BY qs.establishment_id, qs.cycle, qs.academic_year ORDER BY qs.mean DESC) as rank_high_to_low,
        RANK() OVER (PARTITION BY qs.establishment_id, qs.cycle, qs.academic_year ORDER BY qs.mean ASC) as rank_low_to_high,
        -- Get national stats for comparison
        nqs.mean as national_mean,
        nqs.std_dev as national_std_dev,
        nqs.count as national_count,
        -- Calculate difference from national
        qs.mean - nqs.mean as diff_from_national
    FROM question_statistics qs
    LEFT JOIN national_question_statistics nqs 
        ON qs.question_id = nqs.question_id 
        AND qs.cycle = nqs.cycle 
        AND qs.academic_year = nqs.academic_year
    WHERE qs.mean IS NOT NULL
)
SELECT 
    *,
    -- Categorize performance
    CASE 
        WHEN rank_high_to_low <= 5 THEN 'TOP_5'
        WHEN rank_low_to_high <= 5 THEN 'BOTTOM_5'
        ELSE 'MIDDLE'
    END as performance_category,
    -- Performance vs national
    CASE 
        WHEN diff_from_national > 0.5 THEN 'WELL_ABOVE_NATIONAL'
        WHEN diff_from_national > 0.2 THEN 'ABOVE_NATIONAL'
        WHEN diff_from_national < -0.5 THEN 'WELL_BELOW_NATIONAL'
        WHEN diff_from_national < -0.2 THEN 'BELOW_NATIONAL'
        ELSE 'AT_NATIONAL'
    END as national_comparison
FROM question_details;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_qla_performance ON question_statistics(establishment_id, cycle, mean DESC);
CREATE INDEX IF NOT EXISTS idx_qla_performance_asc ON question_statistics(establishment_id, cycle, mean ASC);

-- API function to get top/bottom questions for an establishment
CREATE OR REPLACE FUNCTION get_qla_top_bottom_questions(
    p_establishment_id UUID,
    p_cycle INTEGER,
    p_academic_year VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    question_id VARCHAR,
    mean DECIMAL,
    std_dev DECIMAL,
    count INTEGER,
    mode INTEGER,
    distribution JSONB,
    performance_category VARCHAR,
    rank_high_to_low INTEGER,
    national_mean DECIMAL,
    diff_from_national DECIMAL,
    national_comparison VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.question_id,
        q.mean,
        q.std_dev,
        q.count,
        q.mode,
        q.distribution,
        q.performance_category,
        q.rank_high_to_low::INTEGER,
        q.national_mean,
        q.diff_from_national,
        q.national_comparison
    FROM qla_question_performance q
    WHERE q.establishment_id = p_establishment_id
    AND q.cycle = p_cycle
    AND (p_academic_year IS NULL OR q.academic_year = p_academic_year)
    AND q.performance_category IN ('TOP_5', 'BOTTOM_5')
    ORDER BY q.rank_high_to_low;
END;
$$ LANGUAGE plpgsql;

-- Function to get all QLA statistics with filters
CREATE OR REPLACE FUNCTION get_qla_statistics(
    p_establishment_id UUID DEFAULT NULL,
    p_cycle INTEGER DEFAULT NULL,
    p_year_group VARCHAR DEFAULT NULL,
    p_faculty VARCHAR DEFAULT NULL,
    p_group VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    question_id VARCHAR,
    mean DECIMAL,
    std_dev DECIMAL,
    count INTEGER,
    mode INTEGER,
    percentile_25 DECIMAL,
    percentile_75 DECIMAL,
    distribution JSONB,
    performance_category VARCHAR,
    national_mean DECIMAL,
    diff_from_national DECIMAL
) AS $$
BEGIN
    -- If filters are provided, we need to recalculate on the fly
    IF p_year_group IS NOT NULL OR p_faculty IS NOT NULL OR p_group IS NOT NULL THEN
        RETURN QUERY
        WITH filtered_responses AS (
            SELECT qr.*
            FROM question_responses qr
            JOIN students s ON qr.student_id = s.id
            WHERE (p_establishment_id IS NULL OR s.establishment_id = p_establishment_id)
            AND (p_cycle IS NULL OR qr.cycle = p_cycle)
            AND (p_year_group IS NULL OR s.year_group = p_year_group)
            AND (p_faculty IS NULL OR s.faculty = p_faculty)
            AND (p_group IS NULL OR s."group" = p_group)
        ),
        question_stats AS (
            SELECT 
                fr.question_id,
                AVG(fr.response_value)::DECIMAL(4,2) as mean,
                STDDEV(fr.response_value)::DECIMAL(4,2) as std_dev,
                COUNT(*)::INTEGER as count,
                MODE() WITHIN GROUP (ORDER BY fr.response_value)::INTEGER as mode,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY fr.response_value)::DECIMAL(4,2) as percentile_25,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY fr.response_value)::DECIMAL(4,2) as percentile_75,
                jsonb_build_array(
                    COUNT(*) FILTER (WHERE fr.response_value = 1),
                    COUNT(*) FILTER (WHERE fr.response_value = 2),
                    COUNT(*) FILTER (WHERE fr.response_value = 3),
                    COUNT(*) FILTER (WHERE fr.response_value = 4),
                    COUNT(*) FILTER (WHERE fr.response_value = 5)
                ) as distribution
            FROM filtered_responses fr
            GROUP BY fr.question_id
        ),
        ranked_questions AS (
            SELECT 
                qs.*,
                RANK() OVER (ORDER BY qs.mean DESC) as rank_desc,
                RANK() OVER (ORDER BY qs.mean ASC) as rank_asc
            FROM question_stats qs
        )
        SELECT 
            rq.question_id,
            rq.mean,
            rq.std_dev,
            rq.count,
            rq.mode,
            rq.percentile_25,
            rq.percentile_75,
            rq.distribution,
            CASE 
                WHEN rq.rank_desc <= 5 THEN 'TOP_5'
                WHEN rq.rank_asc <= 5 THEN 'BOTTOM_5'
                ELSE 'MIDDLE'
            END as performance_category,
            nqs.mean as national_mean,
            rq.mean - COALESCE(nqs.mean, 0) as diff_from_national
        FROM ranked_questions rq
        LEFT JOIN national_question_statistics nqs 
            ON rq.question_id = nqs.question_id 
            AND nqs.cycle = COALESCE(p_cycle, 1);
    ELSE
        -- Use pre-calculated statistics
        RETURN QUERY
        SELECT 
            q.question_id,
            q.mean,
            q.std_dev,
            q.count,
            q.mode,
            q.percentile_25,
            q.percentile_75,
            q.distribution,
            q.performance_category,
            q.national_mean,
            q.diff_from_national
        FROM qla_question_performance q
        WHERE (p_establishment_id IS NULL OR q.establishment_id = p_establishment_id)
        AND (p_cycle IS NULL OR q.cycle = p_cycle);
    END IF;
END;
$$ LANGUAGE plpgsql;