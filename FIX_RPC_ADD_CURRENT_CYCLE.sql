-- Fix RPC to include current_cycle field
-- The get_connected_students_for_staff RPC doesn't return current_cycle!

-- Drop and recreate with current_cycle added
DROP FUNCTION IF EXISTS get_connected_students_for_staff(text, uuid, text);

CREATE OR REPLACE FUNCTION get_connected_students_for_staff(
  staff_email_param text,
  school_id_param uuid,
  connection_type_filter text DEFAULT 'tutor'
)
RETURNS TABLE (
  id uuid,
  email text,
  first_name text,
  last_name text,
  full_name text,
  current_year_group text,
  current_cycle integer,  -- ← ADDED THIS!
  student_group text,
  gender text,
  connection_type text,
  school_id uuid,
  school_name text,
  account_id uuid,
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
    vs.email,
    vs.first_name,
    vs.last_name,
    vs.full_name,
    vs.current_year_group,
    vs.current_cycle,  -- ← ADDED THIS!
    vs.student_group,
    vs.gender,
    ssc.connection_type,
    vs.school_id,
    s.school_name,
    vs.account_id,
    
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
  LEFT JOIN establishments e ON e.id = vs.school_id
  LEFT JOIN activity_responses ar ON ar.student_email = vs.email
  LEFT JOIN activities a ON a.id = ar.activity_id
  
  WHERE ssc.staff_email = staff_email_param
    AND vs.school_id = school_id_param
    AND ssc.connection_type = connection_type_filter
  
  GROUP BY 
    vs.id,
    vs.email,
    vs.first_name,
    vs.last_name,
    vs.full_name,
    vs.current_year_group,
    vs.current_cycle,  -- ← ADDED THIS!
    vs.student_group,
    vs.gender,
    ssc.connection_type,
    vs.school_id,
    COALESCE(e.name, e.school_name, vs.school_name, 'Unknown School') as school_name,
    vs.account_id
  
  ORDER BY vs.last_name, vs.first_name;
END;
$$;

-- Test it
SELECT 
  email,
  full_name,
  current_cycle,  -- ← Should now be included!
  total_activities
FROM get_connected_students_for_staff(
  'tut7@vespa.academy',
  'b4bbffc9-7fb6-415a-9a8a-49648995f6b3'::uuid,
  'tutor'
)
WHERE email = 'aramsey@vespa.academy';

COMMENT ON FUNCTION get_connected_students_for_staff IS 'Returns connected students for staff member - UPDATED to include current_cycle field';

