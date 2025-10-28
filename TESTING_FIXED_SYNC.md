# Testing the Fixed Sync Script
**Version:** 2.0 - FIXED  
**Date:** October 28, 2025

---

## ✅ **What Was Fixed**

All 5 critical issues have been resolved in `sync_knack_to_supabase.py`:

1. ✅ Students upsert constraint (2 locations)
2. ✅ Question responses academic_year field added
3. ✅ Question responses upsert constraint (2 locations)
4. ✅ Fallback to 'created' date instead of current date
5. ✅ Proper type handling

---

## 🧪 **How to Test Locally**

### **Step 1: Backup Current Database State** (Safety First!)

Run this SQL in Supabase to count current records:
```sql
-- Record these numbers BEFORE testing
SELECT 'students' as table_name, COUNT(*) as count FROM students
UNION ALL
SELECT 'vespa_scores', COUNT(*) FROM vespa_scores
UNION ALL
SELECT 'question_responses', COUNT(*) FROM question_responses;
```

**Save these numbers!** You'll compare after testing.

---

### **Step 2: Test Run the Fixed Sync**

```bash
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"

python sync_knack_to_supabase.py
```

---

### **Step 3: Watch for Success Indicators**

**Good Signs:**
```
✅ Using new constraint: student_id,cycle,academic_year
✅ Processing batch of XXX students...
✅ Processing batch of XXX question responses...
✅ Syncing question responses...
✅ Synced XXX students and XXX VESPA scores
```

**Bad Signs:**
```
❌ Error: constraint violation
❌ Error: invalid input syntax
❌ Many records skipped
```

---

## 📊 **Expected Results**

### **For Students:**
```
Before: 999 students total
After:  Similar or slightly more (NOT 20K jump - that was from CSV)
        Should see multi-year records now

Check: Same email should exist for different academic_years
```

### **For Question Responses:**
```
Before: ~750K responses, 13K skipped daily
After:  MORE responses synced, FEWER skipped

Check: Skipped count should be much lower (under 1,000)
```

---

## 🔍 **Verification Queries**

### **After Sync Completes - Run These in Supabase:**

**Query 1: Check Multi-Year Students**
```sql
-- Find students that exist in multiple years
SELECT 
    email,
    COUNT(DISTINCT academic_year) as year_count,
    STRING_AGG(DISTINCT academic_year, ', ') as years
FROM students
GROUP BY email
HAVING COUNT(DISTINCT academic_year) > 1
LIMIT 20;
```
**Expected:** Should see students in both 2024/2025 and 2025/2026

---

**Query 2: Check Question Responses Have Academic Year**
```sql
-- Verify academic_year is populated
SELECT 
    academic_year,
    cycle,
    COUNT(*) as response_count
FROM question_responses
GROUP BY academic_year, cycle
ORDER BY academic_year DESC, cycle;
```
**Expected:** All responses should have academic_year (no NULLs)

---

**Query 3: Check VESPA Scores by Year**
```sql
SELECT 
    academic_year,
    cycle,
    COUNT(*) as score_count
FROM vespa_scores
GROUP BY academic_year, cycle
ORDER BY academic_year DESC, cycle;
```
**Expected:** Scores distributed across years properly

---

**Query 4: Verify No Duplicates**
```sql
-- Check for duplicate students in same year
SELECT 
    email,
    academic_year,
    COUNT(*) as count
FROM students
GROUP BY email, academic_year
HAVING COUNT(*) > 1;
```
**Expected:** ZERO results (no duplicates)

---

## ⏱️ **How Long Will It Take?**

**Full sync typically:**
- Establishments: 1-2 minutes
- Students + VESPA: 10-20 minutes
- Question responses: 15-30 minutes
- Statistics calculation: 5-10 minutes
- **Total: 30-60 minutes**

---

## 📋 **What to Check in the Report**

The sync will create: `sync_report_YYYYMMDD_HHMMSS.txt`

**Look for:**
```
STUDENTS:
  Records before: 999
  Records after: XXXX
  New records: XXXX
  Errors: 0  ← Should be ZERO

VESPA_SCORES:
  New records: XXXX
  Errors: 0  ← Should be ZERO

QUESTION_RESPONSES:
  New records: XXXX
  Skipped: < 1000  ← Should be MUCH LOWER than 13K
  Duplicates handled: XXX
  Errors: 0  ← Should be ZERO
```

---

## ⚠️ **If Something Goes Wrong**

### **Constraint Errors:**
```
Error: duplicate key value violates unique constraint
```
**Action:** Check which table/constraint in error message - might need SQL adjustment

### **Type Errors:**
```
Error: invalid input syntax for type integer
```
**Action:** Check which field - might need more type conversion

### **Many Skipped:**
```
WARNING: XXXX question responses skipped
```
**Action:** Check if students exist for those responses - might be timing issue

---

## 🎯 **Rollback Plan** (If Needed)

If testing shows problems:

**Option A: Revert in Git**
```bash
git revert HEAD
git push origin main
```

**Option B: Restore from Backup**
- Use Supabase point-in-time recovery
- Or re-run previous version

---

## 📝 **After Successful Test**

### **Checklist:**
- [ ] Sync completed without errors
- [ ] Student counts make sense
- [ ] Question responses skipped is low
- [ ] Multi-year students exist (verification query #1)
- [ ] Academic year populated (verification query #2)
- [ ] No duplicates (verification query #4)
- [ ] Dashboard still works

### **Then:**
- [ ] Deploy to Heroku (it's already in GitHub!)
- [ ] Monitor first scheduled run (2AM tomorrow)
- [ ] Verify email report looks good
- [ ] Celebrate! 🎉

---

## 🚀 **Ready to Test?**

When you're ready:
```bash
python sync_knack_to_supabase.py
```

**Grab a coffee ☕ - this will take 30-60 minutes!**

All output goes to: `sync_knack_to_supabase.log`

---

*All fixes committed and pushed to GitHub!* ✅

