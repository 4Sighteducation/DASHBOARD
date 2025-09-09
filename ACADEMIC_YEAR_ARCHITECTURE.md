# Academic Year Architecture Update

## Overview
The academic year is now a **fundamental property** of each student record, not just inferred from VESPA data. This provides precise control over enrollment counts and dashboard displays.

## Database Changes

### Students Table
- **New Column**: `academic_year` (TEXT, NOT NULL)
- **Format**: `YYYY/YYYY` (e.g., "2025/2026")
- **Purpose**: Explicitly defines which academic year a student belongs to

### Key Benefits
1. **Precise Enrollment Counts**: Students are counted exactly once per academic year
2. **Clear Data Ownership**: Each student record belongs to a specific academic year
3. **Historical Accuracy**: Past years' data remains intact and accurate
4. **Simplified Queries**: No need to infer academic year from VESPA data

## How It Works

### Student Assignment Logic
```sql
-- A student belongs to an academic year based on:
1. Their enrollment/creation date in the system
2. Manual assignment during year-end transitions
3. NOT based on when they complete VESPA assessments
```

### Dashboard Display
- **Total Students**: Count of students where `academic_year = selected_year`
- **Response Rate**: Students with VESPA data for that academic year
- **Averages**: Calculated only from students in that academic year

### Example Scenarios

#### Continuing Student (Year 12 → Year 13)
```
2024/2025: Student record with academic_year = '2024/2025'
           - Shows in 2024/25 dashboard counts
           - Has VESPA data for cycles in 2024/25

2025/2026: NEW student record with academic_year = '2025/2026'
           - Shows in 2025/26 dashboard counts
           - Has VESPA data for cycles in 2025/26
           - Same email, different record
```

#### New Student
```
2025/2026: Student record with academic_year = '2025/2026'
           - Only appears in 2025/26 counts
```

#### Departed Student
```
2024/2025: Student record with academic_year = '2024/2025'
           - Only appears in 2024/25 counts (archive)
           - Never appears in 2025/26
```

## Year-End Transition Process

### Option 1: Delete and Re-add (Recommended)
1. Export current year's student data
2. Delete continuing students from Knack
3. Re-import as new records for next year
4. Sync will create new records with new academic_year

### Option 2: Update Academic Year
1. Identify continuing students
2. Update their `academic_year` field
3. Clear previous VESPA data if needed
4. Note: This keeps the same student ID

## Sync Script Updates

### Required Changes to `sync_knack_to_supabase.py`

```python
# When syncing students, include academic_year:
student_data = {
    'id': student_id,
    'email': email,
    'name': name,
    'establishment_id': establishment_id,
    'academic_year': calculate_academic_year(datetime.now()),
    'created_at': datetime.now().isoformat()
}

# Upsert with academic year consideration
supabase.table('students').upsert(
    students_batch,
    on_conflict='email'
).execute()
```

## API Updates

### Required Changes to `app.py`

```python
# Count students by their academic_year field
@app.route('/api/dashboard-stats')
def get_stats():
    academic_year = request.args.get('academic_year')
    establishment_id = request.args.get('establishment_id')
    
    # Get students for this academic year
    students = supabase.table('students')\
        .select('*')\
        .eq('establishment_id', establishment_id)\
        .eq('academic_year', academic_year)\
        .execute()
    
    return {
        'total_students': len(students.data),
        'academic_year': academic_year
    }
```

## Migration Steps

1. **Run SQL Migration**
   ```bash
   # Apply the academic year column
   psql -d your_database < add_academic_year_to_students.sql
   ```

2. **Update Sync Script**
   - Add academic_year calculation
   - Include in student upserts
   - Test with a small batch

3. **Update API Endpoints**
   - Modify student counting logic
   - Use academic_year field instead of inferring
   - Test all dashboard views

4. **Verify Data**
   - Check student counts per year
   - Ensure no duplicates
   - Confirm historical data intact

## Troubleshooting

### Issue: Students appearing in wrong year
**Solution**: Check their `academic_year` field and update if needed

### Issue: Duplicate counts
**Solution**: Ensure each student has only one record per academic_year

### Issue: Missing students
**Solution**: Verify all students have academic_year assigned

## Best Practices

1. **Always set academic_year** when creating student records
2. **Use consistent format** (YYYY/YYYY)
3. **Plan year-end transitions** in advance
4. **Keep archives separate** - don't mix years
5. **Document any manual changes** to academic years

## Query Examples

### Get exact student count for an academic year
```sql
SELECT COUNT(*) 
FROM students 
WHERE establishment_id = ? 
AND academic_year = '2025/2026';
```

### Find students with VESPA data
```sql
SELECT s.*, 
       EXISTS(SELECT 1 FROM vespa_scores v 
              WHERE v.student_id = s.id 
              AND v.academic_year = s.academic_year) as has_vespa
FROM students s
WHERE s.academic_year = '2025/2026';
```

### Year-over-year comparison
```sql
SELECT academic_year, 
       COUNT(*) as total_students,
       COUNT(DISTINCT v.student_id) as with_vespa
FROM students s
LEFT JOIN vespa_scores v ON s.id = v.student_id 
                         AND s.academic_year = v.academic_year
GROUP BY academic_year
ORDER BY academic_year DESC;
```
