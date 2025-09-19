-- Student Enrollment History Architecture
-- Supports both workflows: 
-- 1. Small schools: Keep accounts, update Year Group
-- 2. Large schools: Delete and re-upload

-- ============================================================================
-- STEP 1: Create the enrollment history table
-- ============================================================================
CREATE TABLE IF NOT EXISTS student_enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    academic_year VARCHAR(10) NOT NULL,
    knack_id VARCHAR(50),  -- The Knack ID used this year (may change)
    year_group VARCHAR(50),  -- Year 12, Year 13, etc.
    previous_year_group VARCHAR(50),  -- To track progression
    course VARCHAR(100),
    faculty VARCHAR(100),
    enrollment_status VARCHAR(20) DEFAULT 'active',  -- active, graduated, left
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(student_id, academic_year)
);

-- Index for quick lookups
CREATE INDEX idx_student_enrollments_year ON student_enrollments(academic_year);
CREATE INDEX idx_student_enrollments_student ON student_enrollments(student_id);
CREATE INDEX idx_student_enrollments_status ON student_enrollments(enrollment_status);

-- ============================================================================
-- STEP 2: Create trigger to track Year Group changes (leading indicator)
-- ============================================================================
CREATE OR REPLACE FUNCTION track_year_group_changes()
RETURNS TRIGGER AS $$
DECLARE
    current_academic_year VARCHAR(10);
    previous_enrollment RECORD;
BEGIN
    -- Calculate current academic year
    current_academic_year := CASE 
        WHEN EXTRACT(MONTH FROM NOW()) >= 8 THEN 
            EXTRACT(YEAR FROM NOW())::TEXT || '/' || (EXTRACT(YEAR FROM NOW()) + 1)::TEXT
        ELSE 
            (EXTRACT(YEAR FROM NOW()) - 1)::TEXT || '/' || EXTRACT(YEAR FROM NOW())::TEXT
    END;
    
    -- Check if Year Group has changed
    IF OLD.year_group IS DISTINCT FROM NEW.year_group THEN
        -- Year Group changed - this might indicate a new academic year
        
        -- Get the most recent enrollment for this student
        SELECT * INTO previous_enrollment
        FROM student_enrollments
        WHERE student_id = NEW.id
        ORDER BY academic_year DESC
        LIMIT 1;
        
        -- If no enrollment exists or it's a different year, create new enrollment
        IF previous_enrollment IS NULL OR previous_enrollment.academic_year != current_academic_year THEN
            INSERT INTO student_enrollments (
                student_id,
                academic_year,
                knack_id,
                year_group,
                previous_year_group,
                course,
                faculty,
                enrollment_status
            ) VALUES (
                NEW.id,
                current_academic_year,
                NEW.knack_id,
                NEW.year_group,
                OLD.year_group,  -- Track what they progressed from
                NEW.course,
                NEW.faculty,
                'active'
            )
            ON CONFLICT (student_id, academic_year) 
            DO UPDATE SET
                year_group = EXCLUDED.year_group,
                previous_year_group = EXCLUDED.previous_year_group,
                course = EXCLUDED.course,
                faculty = EXCLUDED.faculty,
                updated_at = NOW();
                
            RAISE NOTICE 'Student % progressed from % to % in academic year %', 
                NEW.email, OLD.year_group, NEW.year_group, current_academic_year;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
CREATE TRIGGER track_student_year_changes
AFTER UPDATE ON students
FOR EACH ROW
EXECUTE FUNCTION track_year_group_changes();

-- ============================================================================
-- STEP 3: Function to handle both workflows
-- ============================================================================
CREATE OR REPLACE FUNCTION sync_student_enrollment(
    p_email VARCHAR,
    p_knack_id VARCHAR,
    p_year_group VARCHAR,
    p_course VARCHAR,
    p_faculty VARCHAR,
    p_establishment_id UUID,
    p_name VARCHAR DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_student_id UUID;
    v_current_year VARCHAR(10);
    v_existing_year_group VARCHAR(50);
    v_is_year_progression BOOLEAN := FALSE;
BEGIN
    -- Calculate current academic year
    v_current_year := CASE 
        WHEN EXTRACT(MONTH FROM NOW()) >= 8 THEN 
            EXTRACT(YEAR FROM NOW())::TEXT || '/' || (EXTRACT(YEAR FROM NOW()) + 1)::TEXT
        ELSE 
            (EXTRACT(YEAR FROM NOW()) - 1)::TEXT || '/' || EXTRACT(YEAR FROM NOW())::TEXT
    END;
    
    -- Check if student exists by email
    SELECT id, year_group INTO v_student_id, v_existing_year_group
    FROM students
    WHERE email = p_email;
    
    IF v_student_id IS NOT NULL THEN
        -- Student exists
        
        -- Check if Year Group changed (progression indicator)
        IF v_existing_year_group IS DISTINCT FROM p_year_group THEN
            v_is_year_progression := TRUE;
            RAISE NOTICE 'Year progression detected for %: % -> %', 
                p_email, v_existing_year_group, p_year_group;
        END IF;
        
        -- Update student record (but preserve the core ID)
        UPDATE students SET
            knack_id = p_knack_id,  -- May have changed if re-uploaded
            year_group = p_year_group,
            course = p_course,
            faculty = p_faculty,
            updated_at = NOW()
        WHERE id = v_student_id;
        
    ELSE
        -- New student - create record
        INSERT INTO students (
            email,
            knack_id,
            name,
            establishment_id,
            year_group,
            course,
            faculty,
            academic_year
        ) VALUES (
            p_email,
            p_knack_id,
            p_name,
            p_establishment_id,
            p_year_group,
            p_course,
            p_faculty,
            v_current_year
        )
        RETURNING id INTO v_student_id;
        
        RAISE NOTICE 'Created new student: %', p_email;
    END IF;
    
    -- Always create/update enrollment history
    INSERT INTO student_enrollments (
        student_id,
        academic_year,
        knack_id,
        year_group,
        previous_year_group,
        course,
        faculty,
        enrollment_status
    ) VALUES (
        v_student_id,
        v_current_year,
        p_knack_id,
        p_year_group,
        CASE WHEN v_is_year_progression THEN v_existing_year_group ELSE NULL END,
        p_course,
        p_faculty,
        'active'
    )
    ON CONFLICT (student_id, academic_year) 
    DO UPDATE SET
        knack_id = EXCLUDED.knack_id,  -- Update if Knack ID changed
        year_group = EXCLUDED.year_group,
        course = EXCLUDED.course,
        faculty = EXCLUDED.faculty,
        updated_at = NOW();
    
    RETURN v_student_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 4: Populate history from existing data
-- ============================================================================
-- For Whitchurch, create historical enrollments based on VESPA data
INSERT INTO student_enrollments (
    student_id,
    academic_year,
    knack_id,
    year_group,
    course,
    faculty,
    enrollment_status
)
SELECT DISTINCT
    s.id,
    vs.academic_year,
    s.knack_id,
    s.year_group,
    s.course,
    s.faculty,
    CASE 
        WHEN vs.academic_year = '2025/2026' THEN 'active'
        ELSE 'completed'
    END
FROM students s
INNER JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'  -- Whitchurch
ON CONFLICT (student_id, academic_year) DO NOTHING;

-- ============================================================================
-- STEP 5: Create views for easy querying
-- ============================================================================

-- View: Students by academic year (based on enrollment history)
CREATE OR REPLACE VIEW students_by_academic_year AS
SELECT 
    s.*,
    se.academic_year as enrolled_year,
    se.year_group as enrolled_year_group,
    se.previous_year_group,
    se.enrollment_status
FROM students s
INNER JOIN student_enrollments se ON s.id = se.student_id;

-- View: Student progression tracking
CREATE OR REPLACE VIEW student_progression AS
SELECT 
    s.email,
    s.name,
    e.name as school_name,
    se1.academic_year as from_year,
    se1.year_group as from_year_group,
    se2.academic_year as to_year,
    se2.year_group as to_year_group
FROM students s
INNER JOIN establishments e ON s.establishment_id = e.id
INNER JOIN student_enrollments se1 ON s.id = se1.student_id
LEFT JOIN student_enrollments se2 ON s.id = se2.student_id 
    AND se2.academic_year > se1.academic_year
WHERE se2.previous_year_group IS NOT NULL
ORDER BY s.name, se1.academic_year;

-- ============================================================================
-- STEP 6: Dashboard query helper
-- ============================================================================
CREATE OR REPLACE FUNCTION get_students_for_dashboard(
    p_establishment_id UUID,
    p_academic_year VARCHAR
) RETURNS TABLE (
    id UUID,
    email VARCHAR,
    name VARCHAR,
    year_group VARCHAR,
    course VARCHAR,
    faculty VARCHAR,
    has_vespa_data BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        s.id,
        s.email,
        s.name,
        COALESCE(se.year_group, s.year_group) as year_group,
        COALESCE(se.course, s.course) as course,
        COALESCE(se.faculty, s.faculty) as faculty,
        EXISTS(
            SELECT 1 FROM vespa_scores vs 
            WHERE vs.student_id = s.id 
            AND vs.academic_year = p_academic_year
        ) as has_vespa_data
    FROM students s
    LEFT JOIN student_enrollments se ON s.id = se.student_id 
        AND se.academic_year = p_academic_year
    WHERE s.establishment_id = p_establishment_id
    AND (
        -- Include if they have enrollment for this year
        se.academic_year = p_academic_year
        OR 
        -- OR if they have VESPA data for this year
        EXISTS(
            SELECT 1 FROM vespa_scores vs 
            WHERE vs.student_id = s.id 
            AND vs.academic_year = p_academic_year
        )
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================
/*
-- Get all students for Whitchurch 2024/2025:
SELECT * FROM get_students_for_dashboard(
    '1a327b33-d924-453c-803e-82671f94a242'::UUID, 
    '2024/2025'
);

-- Track year progressions:
SELECT * FROM student_progression
WHERE school_name = 'Whitchurch High School';

-- Find students who progressed from Year 12 to Year 13:
SELECT * FROM student_enrollments
WHERE previous_year_group = 'Year 12' 
AND year_group = 'Year 13';
*/

