-- ============================================================================
-- Create Supabase RPC Function for Bulk Duplicate Cleanup
-- ============================================================================
-- This function deletes duplicate Cycle 2 & 3 records in ONE fast SQL operation
-- Run this ONCE in Supabase SQL Editor
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_duplicate_vespa_cycles(target_academic_year TEXT)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- SAFE DELETE: Only delete Cycle 2 & 3 where:
    -- 1. ALL scores are identical to Cycle 1 AND
    -- 2. Completion date is the same (impossible for legitimate data!)
    -- This ensures we ONLY delete sync-created duplicates, not real data
    WITH deleted AS (
        DELETE FROM vespa_scores
        WHERE id IN (
            SELECT vs2.id
            FROM vespa_scores vs1
            JOIN vespa_scores vs2 ON vs1.student_id = vs2.student_id 
                AND vs1.academic_year = vs2.academic_year
                AND vs2.cycle IN (2, 3)
            WHERE vs1.cycle = 1
            AND vs1.academic_year = target_academic_year
            -- Scores must be identical
            AND vs1.vision = vs2.vision
            AND vs1.effort = vs2.effort
            AND vs1.systems = vs2.systems
            AND vs1.practice = vs2.practice
            AND vs1.attitude = vs2.attitude
            AND vs1.overall = vs2.overall
            -- CRITICAL: Completion date must also be identical (proves it's a duplicate!)
            AND vs1.completion_date = vs2.completion_date
        )
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    -- Also delete empty records (all NULLs) for Cycle 2 & 3
    WITH deleted_empty AS (
        DELETE FROM vespa_scores
        WHERE academic_year = target_academic_year
        AND cycle IN (2, 3)
        AND vision IS NULL
        AND effort IS NULL
        AND systems IS NULL
        AND practice IS NULL
        AND attitude IS NULL
        AND overall IS NULL
        RETURNING id
    )
    SELECT deleted_count + COUNT(*) INTO deleted_count FROM deleted_empty;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION cleanup_duplicate_vespa_cycles(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_duplicate_vespa_cycles(TEXT) TO service_role;

-- Test the function
SELECT cleanup_duplicate_vespa_cycles('2025/2026');

-- Expected output: Number of records deleted (probably 500-1000+)

-- ============================================================================
-- Usage in Python:
-- ============================================================================
/*
result = supabase.rpc('cleanup_duplicate_vespa_cycles', {
    'target_academic_year': '2025/2026'
}).execute()

deleted_count = result.data
logging.info(f"Deleted {deleted_count} duplicate cycles")
*/


