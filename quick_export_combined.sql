-- QUICK EXPORT: Combined VESPA Scores and Response Counts for Schools (Cycles 1 & 2)
-- This single query provides a comprehensive view of all student data
-- Copy and paste this entire query into Supabase SQL Editor and click "Download CSV"

WITH school_data AS (
    SELECT 
        e.name as school_name,
        s.id as student_id,
        s.name as student_name,
        s.email as student_email,
        s.year_group,
        s.course,
        s.faculty,
        vs.cycle,
        vs.vision,
        vs.effort,
        vs.systems,
        vs.practice,
        vs.attitude,
        vs.overall,
        vs.completion_date,
        vs.academic_year,
        COUNT(DISTINCT qr.question_id) as questions_answered
    FROM establishments e
    INNER JOIN students s ON s.establishment_id = e.id
    LEFT JOIN vespa_scores vs ON vs.student_id = s.id
    LEFT JOIN question_responses qr ON qr.student_id = s.id AND qr.cycle = vs.cycle
    WHERE 
        e.id IN (
            '53e70907-bd30-46fb-b870-e4d4a9c1d06b', -- Tonyrefail Community School
            '1a327b33-d924-453c-803e-82671f94a242', -- Whitchurch High School
            '65f4eb79-6f08-4797-83ae-c09b8ae3c194', -- Ysgol Garth Olwg
            '027ede5d-3384-419e-8390-c86d81cc08ab'  -- Llanishen High School
        )
        AND vs.cycle IN (1, 2)
    GROUP BY 
        e.name, s.id, s.name, s.email, s.year_group, s.course, s.faculty,
        vs.cycle, vs.vision, vs.effort, vs.systems, vs.practice, 
        vs.attitude, vs.overall, vs.completion_date, vs.academic_year
)
SELECT 
    school_name,
    student_name,
    student_email,
    year_group,
    course,
    faculty,
    cycle,
    vision,
    effort,
    systems,
    practice,
    attitude,
    overall,
    completion_date,
    academic_year,
    questions_answered,
    -- Calculate VESPA average (excluding null values)
    ROUND(
        (
            COALESCE(vision, 0) + 
            COALESCE(effort, 0) + 
            COALESCE(systems, 0) + 
            COALESCE(practice, 0) + 
            COALESCE(attitude, 0)
        ) / NULLIF(
            (CASE WHEN vision IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN effort IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN systems IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN practice IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN attitude IS NOT NULL THEN 1 ELSE 0 END), 0
        ), 2
    ) as vespa_average
FROM school_data
ORDER BY 
    school_name,
    cycle,
    year_group,
    student_name;
