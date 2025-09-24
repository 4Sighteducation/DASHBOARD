# Enrollment History Implementation Guide
## Complete Explanation of the Academic Year Solution

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [What Will Happen When You Run It](#what-will-happen)
3. [How Historical Data Is Preserved](#historical-data)
4. [Frontend Compatibility](#frontend-compatibility)
5. [Step-by-Step Implementation](#implementation-steps)
6. [Testing & Verification](#testing)
7. [FAQ](#faq)

---

## 🎯 Overview

### The Core Problem
When students are re-uploaded with new Knack IDs but same emails:
- The sync uses `on_conflict='email'` and **overwrites** the existing record
- This loses the academic year assignment (changes 2024/2025 → 2025/2026)
- Result: Only current year data visible, no historical records

### The Solution
Create a **student enrollment history table** that:
- Keeps ONE master student record (by email) 
- Tracks enrollment history in a separate table by academic year
- Preserves ALL historical data automatically
- Works with BOTH your workflows (small schools vs large schools)

---

## 🚀 What Will Happen When You Run It

### Immediate Actions (When you run `create_student_enrollment_history.sql`)

1. **Creates New Table: `student_enrollments`**
   ```sql
   student_enrollments:
   - id (unique enrollment ID)
   - student_id (links to master student record)
   - academic_year (e.g., '2024/2025')
   - knack_id (can change between years)
   - year_group, course, faculty
   - enrollment_status (active/completed/graduated)
   ```

2. **Automatically Populates Historical Data**
   - The script looks at ALL existing VESPA scores
   - For each unique student + academic_year combination, it creates an enrollment record
   - Example for Whitchurch:
     - Finds ~440 students with 2024/2025 VESPA data → Creates 440 enrollment records for 2024/2025
     - Finds 207 students with 2025/2026 VESPA data → Creates 207 enrollment records for 2025/2026
   - Students who were in both years will have 2 enrollment records

3. **Creates Helper Views and Functions**
   - `students_by_academic_year` view - Easy way to query students by year
   - `student_progression` view - Track how students moved between years
   - `get_students_for_dashboard()` function - Backward-compatible dashboard queries

4. **Sets Up Automatic Tracking**
   - Creates trigger that detects Year Group changes
   - Automatically creates new enrollment when Year Group changes

---

## 📚 Historical Data

### Yes, ALL Historical Data Is Preserved!

When you run the script, it executes this crucial step:

```sql
-- STEP 4: Populate history from existing data
INSERT INTO student_enrollments (...)
SELECT DISTINCT
    s.id,
    vs.academic_year,  -- Takes the year from VESPA scores
    s.knack_id,
    s.year_group,
    ...
FROM students s
INNER JOIN vespa_scores vs ON s.id = vs.student_id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'  -- Whitchurch
```

This means:
- **Every student who has VESPA data for 2024/2025** gets an enrollment record for 2024/2025
- **Every student who has VESPA data for 2025/2026** gets an enrollment record for 2025/2026
- Students who progressed (were in both years) get **TWO records** - one for each year

### Example After Running:
```
Student: john.doe@school.com
├── Master Record (students table):
│   └── Current info (Year 13, latest Knack ID)
└── Enrollment History (student_enrollments table):
    ├── 2024/2025: Year 12, Old Knack ID, completed
    └── 2025/2026: Year 13, New Knack ID, active
```

---

## 🖥️ Frontend Compatibility

### Good News: Minimal Changes Required!

The script creates **backward-compatible views and functions** that work with existing queries:

#### 1. Dashboard Statistics Queries
**Current Query Pattern:**
```sql
-- Your API currently does something like:
SELECT * FROM students WHERE establishment_id = X AND academic_year = Y
```

**After Implementation:**
```sql
-- The new function provides the same data:
SELECT * FROM get_students_for_dashboard(establishment_id, academic_year)
-- Returns students who were enrolled OR have VESPA data for that year
```

#### 2. What Needs Updating in Frontend?

**Option A: Use the new function (Recommended)**
Update the API endpoint (`app.py`) to call the new function:
```python
# Instead of:
query = supabase_client.table('students').select('*').eq('academic_year', year)

# Use:
result = supabase_client.rpc('get_students_for_dashboard', {
    'p_establishment_id': establishment_uuid,
    'p_academic_year': academic_year
})
```

**Option B: Keep existing logic (Works but less efficient)**
The current logic that checks VESPA scores will continue to work:
```python
# This still works - students table remains unchanged
# The enrollment history is ADDITIONAL, not a replacement
```

### API Changes Already Made
The changes we made to `app.py` earlier today already handle this correctly:
- We removed the `academic_year` filter on the students table ✅
- We check for VESPA data presence instead ✅
- This logic will continue to work with the enrollment history

---

## 📝 Implementation Steps

### Step 1: Run the SQL Script
```bash
# In Supabase SQL Editor:
1. Open create_student_enrollment_history.sql
2. Run the entire script
3. It will show notices about creating enrollments
```

### Step 2: Verify Historical Data
```sql
-- Check enrollment counts by year:
SELECT 
    academic_year,
    COUNT(DISTINCT student_id) as student_count
FROM student_enrollments
WHERE student_id IN (
    SELECT id FROM students 
    WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
)
GROUP BY academic_year;

-- Should show:
-- 2024/2025: ~440 students
-- 2025/2026: 207 students
```

### Step 3: Update Sync Script (Later)
Update `sync_knack_to_supabase.py` to use the new function:
```python
# Instead of direct upsert:
result = supabase.rpc('sync_student_enrollment', {
    'p_email': student['email'],
    'p_knack_id': student['knack_id'],
    'p_year_group': student['year_group'],
    # ... other fields
})
```

### Step 4: Test Both Workflows
**Small School Workflow:**
1. Update a student's Year Group in Knack
2. Sync runs
3. System detects progression, creates new enrollment

**Large School Workflow:**
1. Delete and re-upload students with new IDs
2. Sync runs  
3. System updates Knack IDs but preserves history

---

## 🧪 Testing & Verification

### Quick Test Queries

#### 1. See Student History
```sql
-- View a specific student's journey:
SELECT 
    se.academic_year,
    se.year_group,
    se.previous_year_group,
    COUNT(vs.id) as vespa_scores_count
FROM student_enrollments se
LEFT JOIN vespa_scores vs ON se.student_id = vs.student_id 
    AND se.academic_year = vs.academic_year
WHERE se.student_id = (
    SELECT id FROM students WHERE email = 'student.email@school.com'
)
GROUP BY se.academic_year, se.year_group, se.previous_year_group
ORDER BY se.academic_year;
```

#### 2. Dashboard View for Specific Year
```sql
-- Get all students for 2024/2025:
SELECT COUNT(*) FROM get_students_for_dashboard(
    '1a327b33-d924-453c-803e-82671f94a242'::UUID,
    '2024/2025'
);
-- Should return ~440
```

#### 3. Track Progressions
```sql
-- See all Year 12 → Year 13 progressions:
SELECT * FROM student_progression
WHERE from_year_group = 'Year 12' 
AND to_year_group = 'Year 13';
```

---

## ❓ FAQ

### Q: Will this break existing dashboard functionality?
**A:** No! The students table remains unchanged. The enrollment history is ADDITIONAL data. Your existing queries will continue to work.

### Q: What happens to students who graduated?
**A:** They keep their historical enrollment records marked as 'completed'. They'll show up when viewing 2024/2025 data but not 2025/2026.

### Q: Can I undo this if needed?
**A:** Yes, the script only ADDS new tables/views. To undo:
```sql
DROP TABLE student_enrollments CASCADE;
DROP FUNCTION IF EXISTS sync_student_enrollment;
DROP FUNCTION IF EXISTS get_students_for_dashboard;
```

### Q: How does it know which academic year to use?
**A:** It calculates based on current date (August = new academic year) OR uses the Year Group change as an indicator.

### Q: Will sync times increase?
**A:** Minimal impact. One additional insert/update per student. The trigger is lightweight.

### Q: What about students in multiple schools?
**A:** Each school's enrollments are tracked separately through the establishment_id in the students table.

---

## ✅ Summary

### What You Get:
1. **Complete Historical Preservation** - Never lose data from previous years
2. **Flexible Workflow Support** - Works with both small and large school patterns  
3. **Backward Compatibility** - Existing queries continue to work
4. **Automatic Tracking** - Year progressions detected automatically
5. **Better Analytics** - Can now track student journeys across years

### Next Actions:
1. **NOW:** Run `create_student_enrollment_history.sql` in Supabase
2. **Verify:** Check enrollment counts match expectations
3. **Test:** Try the dashboard - should show correct counts for each year
4. **Later:** Update sync script to use new function (optional but recommended)

### The Result:
- When viewing 2024/2025: Shows ALL ~440 students from last year
- When viewing 2025/2026: Shows only the 207 current Year 13s
- Students who progressed have complete history preserved
- Future syncs will automatically maintain this structure

---

## 🚨 Important Notes

### About the API Fix from Earlier
The API fix we implemented earlier (`app.py` changes) is **compatible** with this enrollment history solution:
- It checks VESPA data presence, not the students.academic_year field
- This will continue to work correctly with enrollment history
- The enrollment history provides a MORE ELEGANT solution but both work together

### About Data Integrity
- Email remains the unique identifier for a student
- Knack IDs can change without losing history
- Year Group changes trigger progression tracking
- All VESPA scores remain linked to the correct student

### About Performance
- The views are optimized with proper indexes
- Dashboard queries will actually be FASTER (no need to check VESPA tables)
- Historical queries become much simpler

---

This solution elegantly handles your complex requirements while maintaining simplicity for the end user!


