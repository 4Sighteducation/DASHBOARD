-- Update RPC functions to include VESPA scores for Staff Dashboard
-- Run this in Supabase SQL Editor

-- 1. Update get_connected_students_for_staff to include vespa_scores
DROP FUNCTION IF EXISTS get_connected_students_for_staff(text, uuid, text);

CREATE OR REPLACE FUNCTION get_connected_students_for_staff(
  connection_type_filter text,
  school_id_param uuid,
  staff_email_param text
)
RETURNS TABLE (
  id uuid,
  email text,
  first_name text,
  last_name text,
  full_name text,
  current_year_group text,
  current_cycle integer,
  student_group text,
  gender text,
  connection_type text,
  school_id uuid,
  school_name text,
  account_id uuid,
  vespa_scores jsonb,  -- NEW: Add VESPA scores!
  total_activities bigint,
  completed_activities bigint,
  in_progress_activities bigint,
  vision_total bigint,
  vision_completed bigint,
  effort_total bigint,
  effort_completed bigint,
  systems_total bigint,
  systems_completed bigint,
  practice_total bigint,
  practice_completed bigint,
  attitude_total bigint,
  attitude_completed bigint
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    vs.id,
    vs.email::text,
    vs.first_name::text,
    vs.last_name::text,
    vs.full_name::text,
    vs.current_year_group::text,
    vs.current_cycle,
    vs.student_group::text,
    vs.gender::text,
    ssc.staff_role::text as connection_type,
    vs.school_id,
    COALESCE(vs.school_name, 'Unknown')::text,
    vs.account_id,
    vs.latest_vespa_scores as vespa_scores,  -- NEW: Return VESPA scores
    
    -- Activity counts
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status != 'removed') as total_activities,
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status = 'completed') as completed_activities,
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status = 'in_progress') as in_progress_activities,
    
    -- Category breakdowns
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Vision' AND ar.status != 'removed') as vision_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Vision' AND ar.status = 'completed') as vision_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Effort' AND ar.status != 'removed') as effort_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Effort' AND ar.status = 'completed') as effort_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Systems' AND ar.status != 'removed') as systems_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Systems' AND ar.status = 'completed') as systems_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Practice' AND ar.status != 'removed') as practice_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Practice' AND ar.status = 'completed') as practice_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Attitude' AND ar.status != 'removed') as attitude_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Attitude' AND ar.status = 'completed') as attitude_completed
    
  FROM vespa_students vs
  INNER JOIN staff_student_connections ssc ON ssc.student_email = vs.email
  LEFT JOIN activity_responses ar ON ar.student_email = vs.email
  LEFT JOIN activities a ON a.id = ar.activity_id
  
  WHERE ssc.staff_email = staff_email_param
    AND vs.school_id = school_id_param
    AND (connection_type_filter IS NULL OR ssc.staff_role = connection_type_filter)
  
  GROUP BY 
    vs.id,
    vs.email,
    vs.first_name,
    vs.last_name,
    vs.full_name,
    vs.current_year_group,
    vs.current_cycle,
    vs.student_group,
    vs.gender,
    ssc.staff_role,
    vs.school_id,
    vs.school_name,
    vs.account_id,
    vs.latest_vespa_scores  -- NEW: Include in GROUP BY
  
  ORDER BY vs.last_name, vs.first_name;
END;
$$;


-- 2. Update get_students_for_staff (admin version) to include vespa_scores
DROP FUNCTION IF EXISTS get_students_for_staff(text, uuid);

CREATE OR REPLACE FUNCTION get_students_for_staff(
  staff_email_param text,
  school_id_param uuid
)
RETURNS TABLE (
  id uuid,
  email text,
  first_name text,
  last_name text,
  full_name text,
  current_year_group text,
  current_cycle integer,
  student_group text,
  gender text,
  school_id uuid,
  school_name text,
  account_id uuid,
  vespa_scores jsonb,  -- NEW: Add VESPA scores!
  total_activities bigint,
  completed_activities bigint,
  in_progress_activities bigint,
  vision_total bigint,
  vision_completed bigint,
  effort_total bigint,
  effort_completed bigint,
  systems_total bigint,
  systems_completed bigint,
  practice_total bigint,
  practice_completed bigint,
  attitude_total bigint,
  attitude_completed bigint
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    vs.id,
    vs.email::text,
    vs.first_name::text,
    vs.last_name::text,
    vs.full_name::text,
    vs.current_year_group::text,
    vs.current_cycle,
    vs.student_group::text,
    vs.gender::text,
    vs.school_id,
    COALESCE(vs.school_name, 'Unknown')::text,
    vs.account_id,
    vs.latest_vespa_scores as vespa_scores,  -- NEW: Return VESPA scores
    
    -- Activity counts
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status != 'removed') as total_activities,
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status = 'completed') as completed_activities,
    COUNT(DISTINCT ar.id) FILTER (WHERE ar.status = 'in_progress') as in_progress_activities,
    
    -- Category breakdowns
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Vision' AND ar.status != 'removed') as vision_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Vision' AND ar.status = 'completed') as vision_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Effort' AND ar.status != 'removed') as effort_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Effort' AND ar.status = 'completed') as effort_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Systems' AND ar.status != 'removed') as systems_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Systems' AND ar.status = 'completed') as systems_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Practice' AND ar.status != 'removed') as practice_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Practice' AND ar.status = 'completed') as practice_completed,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Attitude' AND ar.status != 'removed') as attitude_total,
    COUNT(DISTINCT ar.id) FILTER (WHERE a.vespa_category = 'Attitude' AND ar.status = 'completed') as attitude_completed
    
  FROM vespa_students vs
  LEFT JOIN activity_responses ar ON ar.student_email = vs.email
  LEFT JOIN activities a ON a.id = ar.activity_id
  
  WHERE vs.school_id = school_id_param
  
  GROUP BY 
    vs.id,
    vs.email,
    vs.first_name,
    vs.last_name,
    vs.full_name,
    vs.current_year_group,
    vs.current_cycle,
    vs.student_group,
    vs.gender,
    vs.school_id,
    vs.school_name,
    vs.account_id,
    vs.latest_vespa_scores  -- NEW: Include in GROUP BY
  
  ORDER BY vs.last_name, vs.first_name;
END;
$$;


-- Test to verify it works
SELECT 
  email,
  full_name,
  vespa_scores->>'vision' as vision,
  vespa_scores->>'effort' as effort,
  vespa_scores->>'systems' as systems,
  vespa_scores->>'practice' as practice,
  vespa_scores->>'attitude' as attitude
FROM get_connected_students_for_staff(
  null,                                          -- connection_type (null = all)
  'b4bbffc9-7fb6-415a-9a8a-49648995f6b3'::uuid, -- school_id
  'cali@vespa.academy'                           -- staff_email
)
WHERE email = 'aramsey@vespa.academy';

