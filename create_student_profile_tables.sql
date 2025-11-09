-- Create complete student profile tables in Supabase
-- Includes responses, goals, and coaching notes for each cycle

-- ===== TABLE 1: student_responses =====
-- Student's reflection/comments on their VESPA scores

CREATE TABLE IF NOT EXISTS student_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    academic_year VARCHAR(10) NOT NULL,
    response_text TEXT,  -- Student's reflection on their scores
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One response per student per cycle per year
    UNIQUE (student_id, cycle, academic_year)
);

CREATE INDEX IF NOT EXISTS idx_student_responses_lookup 
ON student_responses (student_id, cycle, academic_year);

COMMENT ON TABLE student_responses IS 'Student reflections on their VESPA scores by cycle';
COMMENT ON COLUMN student_responses.response_text IS 'Maps to Knack Object_10: C1=field_2302, C2=field_2303, C3=field_2304';

-- ===== TABLE 2: student_goals =====
-- Student's study goals for each cycle

CREATE TABLE IF NOT EXISTS student_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    academic_year VARCHAR(10) NOT NULL,
    goal_text TEXT,  -- Combined goals or single goal text
    goal_set_date DATE,  -- When goal was set
    goal_due_date DATE,  -- When goal should be achieved by
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One set of goals per student per cycle per year
    UNIQUE (student_id, cycle, academic_year)
);

CREATE INDEX IF NOT EXISTS idx_student_goals_lookup 
ON student_goals (student_id, cycle, academic_year);

COMMENT ON TABLE student_goals IS 'Student study goals by cycle';
COMMENT ON COLUMN student_goals.goal_text IS 'Maps to Knack Object_10: C1=field_2499, C2=field_2493, C3=field_2494';
COMMENT ON COLUMN student_goals.goal_set_date IS 'Maps to Knack Object_10: C1=field_2321, C2=field_2496, C3=field_2497';
COMMENT ON COLUMN student_goals.goal_due_date IS 'Maps to Knack Object_10: C1=field_2500, C2=field_2497, C3=field_2498';

-- ===== TABLE 3: staff_coaching_notes =====
-- Confidential staff observations and coaching records

CREATE TABLE IF NOT EXISTS staff_coaching_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    staff_id UUID REFERENCES staff_admins(id) ON DELETE SET NULL,  -- Who wrote it (nullable if staff deleted)
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    academic_year VARCHAR(10) NOT NULL,
    coaching_text TEXT,  -- Staff's coaching observations
    coaching_date DATE,  -- Date of coaching conversation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One coaching note per student per cycle per year
    UNIQUE (student_id, cycle, academic_year)
);

CREATE INDEX IF NOT EXISTS idx_staff_coaching_notes_lookup 
ON staff_coaching_notes (student_id, cycle, academic_year);

CREATE INDEX IF NOT EXISTS idx_staff_coaching_notes_staff
ON staff_coaching_notes (staff_id);

COMMENT ON TABLE staff_coaching_notes IS 'Staff coaching observations and notes by cycle';
COMMENT ON COLUMN staff_coaching_notes.coaching_text IS 'Maps to Knack Object_10: C1=field_2488, C2=field_2490, C3=field_2491';
COMMENT ON COLUMN staff_coaching_notes.coaching_date IS 'Maps to Knack Object_10: C1=field_2485, C2=field_2486, C3=field_2487';

-- ===== VIEWS FOR EASY QUERYING =====

-- Complete student profile view
CREATE OR REPLACE VIEW student_profile_complete AS
SELECT 
    s.id as student_id,
    s.email,
    s.name,
    s.academic_year,
    vs.cycle,
    vs.vision,
    vs.effort,
    vs.systems,
    vs.practice,
    vs.attitude,
    vs.overall,
    vs.completion_date,
    sr.response_text as student_response,
    sr.submitted_at as response_date,
    sg.goal_text,
    sg.goal_set_date,
    sg.goal_due_date,
    scn.coaching_text as staff_notes,
    scn.coaching_date,
    scn.staff_id as coach_id
FROM students s
LEFT JOIN vespa_scores vs ON s.id = vs.student_id AND s.academic_year = vs.academic_year
LEFT JOIN student_responses sr ON s.id = sr.student_id AND vs.cycle = sr.cycle AND s.academic_year = sr.academic_year
LEFT JOIN student_goals sg ON s.id = sg.student_id AND vs.cycle = sg.cycle AND s.academic_year = sg.academic_year
LEFT JOIN staff_coaching_notes scn ON s.id = scn.student_id AND vs.cycle = scn.cycle AND s.academic_year = scn.academic_year
ORDER BY s.email, vs.cycle;

COMMENT ON VIEW student_profile_complete IS 'Complete student VESPA profile with scores, responses, goals, and coaching notes';

-- Grant permissions (adjust as needed)
-- ALTER TABLE student_responses ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE student_goals ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE staff_coaching_notes ENABLE ROW LEVEL SECURITY;

