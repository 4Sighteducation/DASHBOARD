-- Enable Row Level Security on all tables
-- This prevents unauthorized access via the public API

-- Enable RLS on all tables
ALTER TABLE trusts ENABLE ROW LEVEL SECURITY;
ALTER TABLE establishments ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff_admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE vespa_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE school_statistics ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_statistics ENABLE ROW LEVEL SECURITY;
ALTER TABLE national_statistics ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_logs ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows the service role full access
-- This ensures your backend can still read/write everything

-- For trusts
CREATE POLICY "Service role has full access to trusts" ON trusts
FOR ALL USING (auth.role() = 'service_role');

-- For establishments
CREATE POLICY "Service role has full access to establishments" ON establishments
FOR ALL USING (auth.role() = 'service_role');

-- For staff_admins
CREATE POLICY "Service role has full access to staff_admins" ON staff_admins
FOR ALL USING (auth.role() = 'service_role');

-- For students
CREATE POLICY "Service role has full access to students" ON students
FOR ALL USING (auth.role() = 'service_role');

-- For vespa_scores
CREATE POLICY "Service role has full access to vespa_scores" ON vespa_scores
FOR ALL USING (auth.role() = 'service_role');

-- For question_responses
CREATE POLICY "Service role has full access to question_responses" ON question_responses
FOR ALL USING (auth.role() = 'service_role');

-- For school_statistics
CREATE POLICY "Service role has full access to school_statistics" ON school_statistics
FOR ALL USING (auth.role() = 'service_role');

-- For question_statistics
CREATE POLICY "Service role has full access to question_statistics" ON question_statistics
FOR ALL USING (auth.role() = 'service_role');

-- For national_statistics
CREATE POLICY "Service role has full access to national_statistics" ON national_statistics
FOR ALL USING (auth.role() = 'service_role');

-- For sync_logs
CREATE POLICY "Service role has full access to sync_logs" ON sync_logs
FOR ALL USING (auth.role() = 'service_role');

-- Fix the SECURITY DEFINER views
-- Drop and recreate without SECURITY DEFINER
DROP VIEW IF EXISTS student_vespa_progress;
DROP VIEW IF EXISTS current_school_averages;

-- Recreate the views without SECURITY DEFINER
CREATE VIEW student_vespa_progress AS
SELECT 
    s.id as student_id,
    s.name as student_name,
    s.email,
    s.establishment_id,
    e.name as establishment_name,
    s.year_group,
    s.course,
    s.faculty,
    -- Cycle 1
    vs1.vision as cycle1_vision,
    vs1.effort as cycle1_effort,
    vs1.systems as cycle1_systems,
    vs1.practice as cycle1_practice,
    vs1.attitude as cycle1_attitude,
    vs1.overall as cycle1_overall,
    vs1.completion_date as cycle1_date,
    -- Cycle 2
    vs2.vision as cycle2_vision,
    vs2.effort as cycle2_effort,
    vs2.systems as cycle2_systems,
    vs2.practice as cycle2_practice,
    vs2.attitude as cycle2_attitude,
    vs2.overall as cycle2_overall,
    vs2.completion_date as cycle2_date,
    -- Cycle 3
    vs3.vision as cycle3_vision,
    vs3.effort as cycle3_effort,
    vs3.systems as cycle3_systems,
    vs3.practice as cycle3_practice,
    vs3.attitude as cycle3_attitude,
    vs3.overall as cycle3_overall,
    vs3.completion_date as cycle3_date
FROM students s
LEFT JOIN establishments e ON s.establishment_id = e.id
LEFT JOIN vespa_scores vs1 ON s.id = vs1.student_id AND vs1.cycle = 1
LEFT JOIN vespa_scores vs2 ON s.id = vs2.student_id AND vs2.cycle = 2
LEFT JOIN vespa_scores vs3 ON s.id = vs3.student_id AND vs3.cycle = 3;

CREATE VIEW current_school_averages AS
SELECT 
    e.id as establishment_id,
    e.name as establishment_name,
    ss.cycle,
    ss.element,
    ss.mean,
    ss.std_dev,
    ss.count,
    ss.academic_year
FROM school_statistics ss
JOIN establishments e ON ss.establishment_id = e.id
WHERE ss.academic_year = (
    SELECT MAX(academic_year) 
    FROM school_statistics 
    WHERE establishment_id = ss.establishment_id
);