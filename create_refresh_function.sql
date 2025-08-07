-- ============================================
-- CREATE RPC FUNCTION FOR REFRESHING MATERIALIZED VIEWS
-- ============================================
-- Run this in Supabase SQL Editor to enable automatic refresh during sync

-- Create a function that can refresh materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_view(view_name text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Security check: only allow specific view names to prevent SQL injection
    IF view_name NOT IN ('comparative_metrics') THEN
        RAISE EXCEPTION 'Invalid view name: %', view_name;
    END IF;
    
    -- Refresh the materialized view
    EXECUTE format('REFRESH MATERIALIZED VIEW %I', view_name);
    
    -- Log the refresh (optional - requires a log table)
    -- INSERT INTO refresh_logs (view_name, refreshed_at) VALUES (view_name, NOW());
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION refresh_materialized_view(text) TO authenticated;
GRANT EXECUTE ON FUNCTION refresh_materialized_view(text) TO service_role;

-- Test the function
SELECT refresh_materialized_view('comparative_metrics');

-- Verify it worked
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT establishment_id) as unique_establishments,
    NOW() as checked_at
FROM comparative_metrics;
