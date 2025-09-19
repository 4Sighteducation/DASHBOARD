# Academic Year Architecture Fix - Root Cause Analysis

## The Fundamental Issue

The current system has a critical flaw in how it handles students across academic years during the "delete and re-upload" process that schools go through.

### What's Happening Now (WRONG)

1. **Last Year (2024/2025):**
   - Whitchurch had ~440 students (220 Year 12s + 220 Year 13s)
   - Each student had a record with `academic_year = '2024/2025'`

2. **This Year's Process:**
   - ALL Knack accounts were deleted
   - Old Year 12s were re-uploaded as new Year 13s (same emails, new Knack IDs)
   - New Year 12s were added

3. **The Problem:**
   - The sync process uses `on_conflict='email'` (line 473 in sync_knack_to_supabase.py)
   - When it sees a student with the same email, it UPDATES the existing record
   - This overwrites `academic_year` from '2024/2025' to '2025/2026'
   - Result: Only 447 total students (not ~660 as expected)
   - Historical data is lost from the students table

### Why This Is Breaking

- **Expected:** 2 separate records for continuing students (one per year)
- **Actual:** 1 record per student that gets overwritten each year
- **Impact:** Can't view historical student lists by academic year

## Current Architecture

```
STUDENTS TABLE:
- Primary Key: id (UUID)
- Unique: knack_id 
- Unique (implicit): email (via upsert conflict)
- Fields: academic_year, name, etc.

VESPA_SCORES TABLE:
- Links to students via student_id
- Has its own academic_year field
- Preserves historical data correctly
```

## The Root Problem

The sync process treats email as the primary identifier and UPDATES records rather than creating new ones for each academic year. This is because:

```python
# In sync_knack_to_supabase.py line 471-474
result = supabase.table('students').upsert(
    student_batch,
    on_conflict='email'  # THIS IS THE PROBLEM
).execute()
```

## Solution Options

### Option 1: Multiple Student Records (One per Academic Year)
**Change the unique constraint from email to email+academic_year**

```sql
-- Remove implicit email uniqueness
-- Add composite unique constraint
ALTER TABLE students 
ADD CONSTRAINT students_email_academic_year_unique 
UNIQUE (email, academic_year);

-- Remove knack_id unique constraint (since IDs change each year)
ALTER TABLE students 
DROP CONSTRAINT IF EXISTS students_knack_id_key;
```

**Pros:**
- Clean separation of years
- Historical data preserved
- Easy to query by year

**Cons:**
- Requires significant code changes
- Need to handle student ID references differently

### Option 2: Single Student Record (Current approach, but fixed)
**Keep one record per student, but DON'T overwrite academic_year**

```python
# Modified sync logic
if existing_student:
    # Don't update academic_year if student already exists
    # Only update other fields (year_group, course, etc.)
    student_data.pop('academic_year', None)
```

**Pros:**
- Minimal code changes
- Maintains referential integrity

**Cons:**
- Loses ability to track which year a student was active
- Relies on VESPA scores for year information

### Option 3: Hybrid - Student History Table (RECOMMENDED)
**Create a separate table for student enrollment history**

```sql
-- New table for tracking student enrollments by year
CREATE TABLE student_enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id),
    academic_year VARCHAR(10) NOT NULL,
    knack_id VARCHAR(50),
    year_group VARCHAR(50),
    course VARCHAR(100),
    faculty VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(student_id, academic_year)
);

-- Students table becomes the master record
-- Remove academic_year from students table
ALTER TABLE students DROP COLUMN IF EXISTS academic_year;
```

**Pros:**
- Clean data model
- Preserves all historical data
- One source of truth for student identity
- Tracks year-over-year progression

**Cons:**
- Requires schema changes
- Need to update queries

## Immediate Fix for Whitchurch

Since we need a quick fix while planning the architectural change:

```sql
-- Fix Whitchurch by creating the missing historical records
WITH historical_students AS (
    -- Find students who had data last year but are now marked as current year
    SELECT DISTINCT 
        s.email,
        s.name,
        s.establishment_id,
        '2024/2025' as academic_year,
        s.knack_id || '_2024' as historical_knack_id
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    AND s.academic_year = '2025/2026'
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2024/2025'
    )
)
INSERT INTO students (email, name, establishment_id, academic_year, knack_id)
SELECT email, name, establishment_id, academic_year, historical_knack_id
FROM historical_students
ON CONFLICT (email) DO NOTHING;  -- This won't work due to email conflict!
```

**This won't work because of the email uniqueness!**

## Recommended Immediate Actions

1. **Update the sync process** to not overwrite academic_year:
```python
# In sync_knack_to_supabase.py
# Check if student exists before updating
existing = supabase.table('students').select('id', 'academic_year').eq('email', email).execute()
if existing.data:
    # Don't overwrite academic_year for existing students
    student_data.pop('academic_year', None)
```

2. **For dashboard queries**, use VESPA data to determine which students to show:
```sql
-- Get students for a specific academic year based on VESPA data
SELECT DISTINCT s.*
FROM students s
INNER JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = :establishment_id
AND vs.academic_year = :academic_year
```

3. **Plan for proper architectural fix** using Option 3 (student_enrollments table)

## For Other Schools

This issue affects ALL schools that:
1. Delete and re-upload students each year
2. Have continuing students (e.g., Year 12 → Year 13)
3. Want to view historical data

The fix needs to be applied system-wide, not just for Whitchurch.

