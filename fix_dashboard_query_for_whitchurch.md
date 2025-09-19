# Dashboard Fix for Whitchurch School Academic Year Issue

## Problem Summary
Whitchurch High School shows only 2 students when viewing 2024/2025 data because:
1. Students were removed and re-uploaded with new record IDs
2. All re-uploaded students were assigned academic_year = '2025/2026'
3. Only 2 students still have academic_year = '2024/2025' in their records
4. However, 189 students have VESPA scores from 2024/2025

## Root Cause
The dashboard is counting students based on their `academic_year` field in the students table, but it should be counting based on whether they have VESPA data for that academic year.

## Solution

### Option 1: Fix the Data (SQL)
Run the SQL script `create_academic_year_view.sql` to:
1. Update students who ONLY have 2024/2025 data to have academic_year = '2024/2025'
2. Create a view that shows students based on their VESPA data year

### Option 2: Fix the Dashboard Query (Preferred)
Update the dashboard API endpoint to count students based on their VESPA data, not their student record.

#### Current Query (WRONG):
```python
# In app.py around line 5690
total_query = supabase_client.table('students')\
    .select('id', count='exact')\
    .eq('establishment_id', establishment_uuid)\
    .eq('academic_year', academic_year)  # This is the problem
```

#### Fixed Query (CORRECT):
```python
# Get students who have VESPA data for the selected academic year
students_with_vespa = []
offset = 0
limit = 1000

while True:
    batch = supabase_client.table('students')\
        .select('id, name, email, year_group, course, faculty')\
        .eq('establishment_id', establishment_uuid)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    if not batch.data:
        break
    
    # Filter students who have VESPA data for the selected year
    for student in batch.data:
        vespa_check = supabase_client.table('vespa_scores')\
            .select('id')\
            .eq('student_id', student['id'])\
            .eq('academic_year', academic_year)\
            .limit(1)\
            .execute()
        
        if vespa_check.data:
            students_with_vespa.append(student)
    
    if len(batch.data) < limit:
        break
    offset += limit

total_enrolled_students = len(students_with_vespa)
```

### Option 3: Hybrid Approach
Use the student's academic_year field for current year, but check VESPA data for historical years:

```python
from datetime import datetime

current_academic_year = get_current_academic_year()  # Returns '2025/2026'

if academic_year == current_academic_year:
    # For current year, use the student's academic_year field
    total_query = supabase_client.table('students')\
        .select('id', count='exact')\
        .eq('establishment_id', establishment_uuid)\
        .eq('academic_year', academic_year)
else:
    # For historical years, count students with VESPA data
    # Use the logic from Option 2
    pass
```

## Quick Fix for Whitchurch
To immediately fix Whitchurch's data display:

1. Run this SQL in Supabase SQL editor:
```sql
-- Update students who only have 2024/2025 VESPA data
WITH students_only_2024_25 AS (
    SELECT DISTINCT s.id
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2024/2025'
    )
    AND NOT EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2025/2026'
    )
)
UPDATE students
SET academic_year = '2024/2025'
WHERE id IN (SELECT id FROM students_only_2024_25);
```

2. This will reassign students who ONLY have last year's data to 2024/2025
3. Students who have completed assessments this year will remain as 2025/2026

## Testing
After applying the fix:
1. Check Whitchurch School for academic year 2024/2025 - should show ~189 students
2. Check Whitchurch School for academic year 2025/2026 - should show current students
3. Verify Question Level Analysis still works for both years
4. Verify other schools are not affected

## Long-term Solution
The system needs a better way to handle year transitions:
1. Keep historical student records instead of overwriting
2. Use student+academic_year as the unique identifier
3. Or always query based on VESPA data year, not student record year
