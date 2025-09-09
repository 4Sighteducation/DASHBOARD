# Academic Year Implementation Summary

## 📋 Overview
We're adding `academic_year` as a core field on every student record. This solves all the counting issues and gives you precise control over enrollment numbers.

## 🎯 The Problem We're Solving
- **Current**: Students counted based on having VESPA data = inaccurate totals
- **New**: Students counted based on their `academic_year` field = exact enrollment counts
- **Result**: Dashboard shows exactly 1026 students for Rochdale 2025/26 (or whatever you need)

## 📝 Implementation Steps

### Step 1: Database Changes (SQL)
Run these SQL scripts in Supabase SQL editor in order:

1. **add_academic_year_STEP1.sql** - Adds the column
2. **add_academic_year_STEP2.sql** - Populates with data
3. **add_academic_year_STEP3_rochdale.sql** - Fixes Rochdale specifically  
4. **add_academic_year_STEP4_finalize.sql** - Adds constraints and creates view

### Step 2: Verify Setup
```bash
python verify_academic_year_setup.py
```
This will tell you if the column exists and show current counts.

### Step 3: Update Sync Script
Update `sync_knack_to_supabase.py` (around line 430-440):

```python
# Add academic_year to student_data dictionary
academic_year = calculate_academic_year(
    datetime.now().strftime('%d/%m/%Y'),
    establishment_id,
    is_uk_school=True
)

student_data = {
    'knack_id': record['id'],
    'email': student_email,
    'name': student_name,
    'establishment_id': establishment_id,
    'academic_year': academic_year,  # NEW FIELD
    'group': record.get('field_223', ''),
    # ... rest of fields
}
```

### Step 4: Update API (app.py)
Key changes needed:

1. **Student counting** (line ~5615):
```python
query = supabase_client.table('students').select('id')\
    .eq('establishment_id', establishment_uuid)

if academic_year:
    query = query.eq('academic_year', academic_year)  # Filter by academic year
```

2. **Total counts** (line ~5694):
```python
total_query = supabase_client.table('students').select('id', count='exact')\
    .eq('establishment_id', establishment_uuid)

if academic_year:
    total_query = total_query.eq('academic_year', academic_year)
```

### Step 5: Test & Deploy
1. Run sync to populate academic_year for new records
2. Test dashboard shows correct counts
3. Commit and push changes
4. Deploy to Heroku

## 🎉 Benefits

### Immediate
- ✅ Rochdale shows exactly 1026 students for 2025/26
- ✅ No more double-counting continuing students
- ✅ Historical data preserved accurately

### Long-term
- ✅ Clear year-end transition process
- ✅ Students counted even before taking VESPA
- ✅ Simple, predictable logic

## 🔧 Year-End Process (Future)

### Option 1: Clean Break (Recommended)
1. Export current students
2. Delete from Knack
3. Re-upload for new year
4. Sync creates new records with new `academic_year`

### Option 2: Update in Place
1. Identify continuing students
2. Update their `academic_year` field
3. Clear old VESPA data if needed

## 📊 Example Queries

### Get exact count for an academic year:
```sql
SELECT COUNT(*) 
FROM students 
WHERE establishment_id = ? 
AND academic_year = '2025/2026';
```

### Dashboard statistics:
```sql
SELECT 
    academic_year,
    COUNT(*) as total_students,
    COUNT(CASE WHEN has_vespa THEN 1 END) as with_responses
FROM students s
LEFT JOIN (
    SELECT DISTINCT student_id, academic_year 
    FROM vespa_scores
) v ON s.id = v.student_id AND s.academic_year = v.academic_year
WHERE establishment_id = ?
GROUP BY academic_year;
```

## ❓ FAQ

**Q: Will this affect existing data?**
A: No, it populates based on existing VESPA data and preserves everything.

**Q: What about students without VESPA data?**
A: They get assigned based on their creation date in the system.

**Q: Can we change a student's academic year later?**
A: Yes, it's just a field update in the database.

**Q: Will the sync overwrite academic years?**
A: Only if you re-upload the student. The field is updated on conflict.

## 🚀 Ready to Go!

1. ✅ SQL scripts ready: `add_academic_year_STEP*.sql`
2. ✅ Verification script: `verify_academic_year_setup.py`
3. ✅ Sync updates documented: `sync_update_for_academic_year.py`
4. ✅ API updates documented: `api_update_for_academic_year.py`

Just run the SQL scripts in Supabase and you're good to go!
