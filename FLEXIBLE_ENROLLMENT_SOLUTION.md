# Flexible Student Enrollment Solution

## Overview

This solution handles both of your workflows while maintaining accurate historical data:

1. **Small Schools Workflow**: Keep student accounts, update Year Group field
2. **Large Schools Workflow**: Delete all accounts and re-upload fresh data

## The Architecture

### Core Principle: One Master Student Record
- Each student has **ONE record** in the `students` table (identified by email)
- This record persists across years
- The `knack_id` can change (when re-uploaded), but the student ID remains constant

### Enrollment History Tracking
- A separate `student_enrollments` table tracks which years a student was active
- Each enrollment record includes:
  - Academic year
  - Year group (Year 12, Year 13, etc.)
  - Previous year group (for progression tracking)
  - Knack ID used that year
  - Course, faculty, status

## How It Works

### Small Schools (Year Group Changes)

When you update a student from Year 12 to Year 13:
```
1. Student record stays the same (same email, same Knack ID)
2. Year Group field changes from "Year 12" to "Year 13"
3. System detects this change as a progression
4. Creates new enrollment record for 2025/2026 with:
   - year_group = "Year 13"
   - previous_year_group = "Year 12"
5. Historical data preserved in enrollment history
```

### Large Schools (Delete & Re-upload)

When you delete all accounts and re-upload:
```
1. Student with same email is found
2. Knack ID is different (new upload = new ID)
3. System updates the Knack ID in student record
4. Creates new enrollment record for 2025/2026
5. Previous years' data remains in enrollment history
```

## Implementation Steps

### Step 1: Create the Enrollment History Table
Run `create_student_enrollment_history.sql` in Supabase SQL editor:
```bash
# This creates:
- student_enrollments table
- Trigger to detect Year Group changes
- Helper functions for dashboard queries
- Views for easy data access
```

### Step 2: Migrate Existing Data
```bash
python migrate_to_enrollment_history.py
```
This will:
- Create enrollment records from existing VESPA data
- Properly assign students to academic years

### Step 3: Update Sync Process
Replace your sync function with the one in `update_sync_for_enrollment_history.py`

### Step 4: Fix Whitchurch Immediately
```sql
-- Run this NOW to fix Whitchurch's display issue
SELECT * FROM get_students_for_dashboard(
    '1a327b33-d924-453c-803e-82671f94a242'::UUID, 
    '2024/2025'
);
```

## Dashboard Integration

### Getting Students for a Specific Year
Instead of:
```sql
SELECT * FROM students 
WHERE establishment_id = ? 
AND academic_year = ?
```

Use:
```sql
SELECT * FROM get_students_for_dashboard(establishment_id, academic_year)
```

This function automatically:
- Checks enrollment history
- Includes students with VESPA data for that year
- Returns the correct Year Group for that specific year

### Python API Update
```python
def get_students_for_year(establishment_id, academic_year):
    # Use the new function that checks enrollment history
    result = supabase.rpc('get_students_for_dashboard', {
        'p_establishment_id': establishment_id,
        'p_academic_year': academic_year
    }).execute()
    
    return result.data
```

## Benefits of This Approach

### 1. Flexibility
- Works with both your workflows
- No need to choose one approach for all schools

### 2. Data Integrity
- Never lose historical data
- Track student progression through years
- Maintain accurate counts for each academic year

### 3. Leading Indicators
- Year Group changes automatically trigger enrollment updates
- System learns from your data patterns

### 4. Simplified Queries
- Dashboard doesn't need to know which workflow was used
- One query works for all scenarios

## Example Scenarios

### Scenario 1: Continuing Student (Small School)
```
2024/2025: 
- John Smith, Year 12, john@school.com, Knack ID: abc123

[Summer: Update Year Group to Year 13]

2025/2026:
- John Smith, Year 13, john@school.com, Knack ID: abc123 (same)
- Enrollment history shows progression from Year 12 to Year 13
```

### Scenario 2: Continuing Student (Large School)
```
2024/2025:
- Jane Doe, Year 12, jane@school.com, Knack ID: xyz789

[Summer: Delete all, re-upload]

2025/2026:
- Jane Doe, Year 13, jane@school.com, Knack ID: def456 (different)
- System recognizes same email, updates Knack ID
- Enrollment history maintained
```

### Scenario 3: Whitchurch Fix
```
Current State:
- 445 students with academic_year = 2025/2026
- 189 of these have 2024/2025 VESPA data

After Fix:
- Dashboard shows 189 students for 2024/2025
- Dashboard shows 445 students for 2025/2026
- Each year shows correct student list
```

## Testing the Solution

1. **Check Whitchurch 2024/2025**:
   - Should show ~189 students (those with 2024/2025 VESPA data)
   
2. **Check Whitchurch 2025/2026**:
   - Should show 445 current students
   
3. **Verify Year Progressions**:
   ```sql
   SELECT * FROM student_progression
   WHERE school_name = 'Whitchurch High School';
   ```
   
4. **Verify Question Level Analysis**:
   - Should work for both years (already does)

## Rollback Plan

If anything goes wrong:
```sql
-- Remove enrollment history (data stays intact)
DROP TABLE IF EXISTS student_enrollments CASCADE;
DROP FUNCTION IF EXISTS get_students_for_dashboard CASCADE;

-- Revert to checking VESPA scores for student lists
```

## Next Steps

1. **Immediate**: Run the SQL to create enrollment history table
2. **Today**: Fix Whitchurch using the new function
3. **This Week**: Update sync process to use enrollment tracking
4. **Future**: Consider adding UI to manage student progressions

## Questions Answered

**Q: Do we need 2 records per continuing student?**
A: No, we keep one master record but track their enrollment history separately.

**Q: How do we know which year to show them in?**
A: The enrollment history table tracks this, plus we check VESPA data.

**Q: What about schools with different workflows?**
A: Both are supported automatically - the system detects which is being used.

**Q: Will this affect other schools?**
A: No, it's backwards compatible. Schools without enrollment history will work as before.


