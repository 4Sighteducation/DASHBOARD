-- VESPA Dashboard Supabase Schema
-- Run this in the Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Trusts table (for academy trusts)
CREATE TABLE IF NOT EXISTS trusts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knack_id VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Establishments table
CREATE TABLE IF NOT EXISTS establishments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knack_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    trust_id UUID REFERENCES trusts(id) ON DELETE SET NULL,
    is_australian BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Staff admins table
CREATE TABLE IF NOT EXISTS staff_admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knack_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Students table
CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knack_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    establishment_id UUID REFERENCES establishments(id) ON DELETE CASCADE,
    year_group VARCHAR(50),
    course VARCHAR(100),
    faculty VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. VESPA scores table (from Object_10)
CREATE TABLE IF NOT EXISTS vespa_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    vision INTEGER CHECK (vision BETWEEN 0 AND 10),
    effort INTEGER CHECK (effort BETWEEN 0 AND 10),
    systems INTEGER CHECK (systems BETWEEN 0 AND 10),
    practice INTEGER CHECK (practice BETWEEN 0 AND 10),
    attitude INTEGER CHECK (attitude BETWEEN 0 AND 10),
    overall INTEGER CHECK (overall BETWEEN 0 AND 10),
    completion_date DATE,
    academic_year VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(student_id, cycle)
);

-- 6. Question responses table (from Object_29)
CREATE TABLE IF NOT EXISTS question_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    question_id VARCHAR(50) NOT NULL,
    response_value INTEGER CHECK (response_value BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. School statistics table (pre-calculated)
CREATE TABLE IF NOT EXISTS school_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    establishment_id UUID REFERENCES establishments(id) ON DELETE CASCADE,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    academic_year VARCHAR(10),
    element VARCHAR(20) NOT NULL CHECK (element IN ('vision', 'effort', 'systems', 'practice', 'attitude', 'overall')),
    mean DECIMAL(4,2),
    std_dev DECIMAL(4,2),
    count INTEGER,
    percentile_25 DECIMAL(4,2),
    percentile_50 DECIMAL(4,2),
    percentile_75 DECIMAL(4,2),
    distribution JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(establishment_id, cycle, academic_year, element)
);

-- 8. Question statistics table
CREATE TABLE IF NOT EXISTS question_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    establishment_id UUID REFERENCES establishments(id) ON DELETE CASCADE,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    academic_year VARCHAR(10),
    question_id VARCHAR(50) NOT NULL,
    mean DECIMAL(4,2),
    std_dev DECIMAL(4,2),
    count INTEGER,
    distribution JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(establishment_id, cycle, academic_year, question_id)
);

-- 9. National statistics table (for benchmarks)
CREATE TABLE IF NOT EXISTS national_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    academic_year VARCHAR(10),
    element VARCHAR(20) NOT NULL CHECK (element IN ('vision', 'effort', 'systems', 'practice', 'attitude', 'overall')),
    mean DECIMAL(4,2),
    std_dev DECIMAL(4,2),
    count INTEGER,
    percentile_25 DECIMAL(4,2),
    percentile_50 DECIMAL(4,2),
    percentile_75 DECIMAL(4,2),
    distribution JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(cycle, academic_year, element)
);

-- 10. Sync log table (to track sync operations)
CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_processed INTEGER,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);

-- Create indexes for performance
CREATE INDEX idx_vespa_scores_student_cycle ON vespa_scores(student_id, cycle);
CREATE INDEX idx_vespa_scores_establishment ON vespa_scores(student_id);
CREATE INDEX idx_question_responses_student_cycle ON question_responses(student_id, cycle);
CREATE INDEX idx_question_responses_question ON question_responses(question_id);
CREATE INDEX idx_school_stats_lookup ON school_statistics(establishment_id, cycle, academic_year);
CREATE INDEX idx_question_stats_lookup ON question_statistics(establishment_id, cycle, question_id);
CREATE INDEX idx_students_establishment ON students(establishment_id);
CREATE INDEX idx_students_email ON students(email);

-- Create views for common queries

-- View for current academic year school averages
CREATE OR REPLACE VIEW current_school_averages AS
SELECT 
    e.name as establishment_name,
    ss.cycle,
    ss.element,
    ss.mean,
    ss.std_dev,
    ss.count
FROM school_statistics ss
JOIN establishments e ON ss.establishment_id = e.id
WHERE ss.academic_year = (
    SELECT academic_year 
    FROM school_statistics 
    ORDER BY calculated_at DESC 
    LIMIT 1
);

-- View for student VESPA progress
CREATE OR REPLACE VIEW student_vespa_progress AS
SELECT 
    s.id as student_id,
    s.name as student_name,
    s.email,
    e.name as establishment_name,
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date
FROM students s
JOIN establishments e ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs ON s.id = vs.student_id
ORDER BY s.name, vs.cycle;

-- Create functions for statistics calculation

-- Function to calculate standard deviation
CREATE OR REPLACE FUNCTION calculate_std_dev(input_values DECIMAL[])
RETURNS DECIMAL AS $$
DECLARE
    avg_val DECIMAL;
    variance DECIMAL;
    n INTEGER;
BEGIN
    n := array_length(input_values, 1);
    IF n IS NULL OR n < 2 THEN
        RETURN 0;
    END IF;
    
    avg_val := (SELECT AVG(v) FROM unnest(input_values) v);
    variance := (SELECT AVG(POWER(v - avg_val, 2)) FROM unnest(input_values) v);
    
    RETURN SQRT(variance);
END;
$$ LANGUAGE plpgsql;

-- Function to calculate element statistics
CREATE OR REPLACE FUNCTION calculate_element_stats(
    p_establishment_id UUID,
    p_cycle INTEGER,
    p_element TEXT
)
RETURNS TABLE (
    mean DECIMAL,
    std_dev DECIMAL,
    count INTEGER,
    percentile_25 DECIMAL,
    percentile_50 DECIMAL,
    percentile_75 DECIMAL,
    distribution JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH scores AS (
        SELECT 
            CASE p_element
                WHEN 'vision' THEN vs.vision
                WHEN 'effort' THEN vs.effort
                WHEN 'systems' THEN vs.systems
                WHEN 'practice' THEN vs.practice
                WHEN 'attitude' THEN vs.attitude
                WHEN 'overall' THEN vs.overall
            END as score
        FROM vespa_scores vs
        JOIN students s ON vs.student_id = s.id
        WHERE s.establishment_id = p_establishment_id
        AND vs.cycle = p_cycle
        AND CASE p_element
                WHEN 'vision' THEN vs.vision
                WHEN 'effort' THEN vs.effort
                WHEN 'systems' THEN vs.systems
                WHEN 'practice' THEN vs.practice
                WHEN 'attitude' THEN vs.attitude
                WHEN 'overall' THEN vs.overall
            END IS NOT NULL
    ),
    stats AS (
        SELECT 
            AVG(score)::DECIMAL(4,2) as mean,
            STDDEV_POP(score)::DECIMAL(4,2) as std_dev,
            COUNT(*)::INTEGER as count,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY score)::DECIMAL(4,2) as percentile_25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY score)::DECIMAL(4,2) as percentile_50,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY score)::DECIMAL(4,2) as percentile_75
        FROM scores
    ),
    distribution AS (
        SELECT 
            jsonb_build_array(
                COUNT(*) FILTER (WHERE score = 0),
                COUNT(*) FILTER (WHERE score = 1),
                COUNT(*) FILTER (WHERE score = 2),
                COUNT(*) FILTER (WHERE score = 3),
                COUNT(*) FILTER (WHERE score = 4),
                COUNT(*) FILTER (WHERE score = 5),
                COUNT(*) FILTER (WHERE score = 6),
                COUNT(*) FILTER (WHERE score = 7),
                COUNT(*) FILTER (WHERE score = 8),
                COUNT(*) FILTER (WHERE score = 9),
                COUNT(*) FILTER (WHERE score = 10)
            ) as dist
        FROM scores
    )
    SELECT 
        s.mean,
        s.std_dev,
        s.count,
        s.percentile_25,
        s.percentile_50,
        s.percentile_75,
        d.dist as distribution
    FROM stats s, distribution d;
END;
$$ LANGUAGE plpgsql;