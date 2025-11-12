-- ============================================================================
-- URGENT SYNC FIXES - Run Immediately
-- ============================================================================
-- Date: November 12, 2025
-- Issue: Sync stopped after Oct 31, multiple critical errors
-- ============================================================================

-- FIX #1: Remove knack_id unique constraint
-- This constraint causes duplicate key errors when students are re-uploaded
-- with new knack_ids each year

ALTER TABLE students 
DROP CONSTRAINT IF EXISTS students_knack_id_key;

-- Keep index for performance (but not unique)
CREATE INDEX IF NOT EXISTS idx_students_knack_id ON students(knack_id);

-- Verify the constraint is gone
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'students'::regclass
AND contype = 'u'
AND conname LIKE '%knack_id%';

-- Expected result: No rows (constraint removed)

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check current constraints on students table
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'students'::regclass
AND contype = 'u'
ORDER BY conname;

-- Should show:
-- students_email_academic_year_key | UNIQUE (email, academic_year)
-- students_pkey | PRIMARY KEY (id)


