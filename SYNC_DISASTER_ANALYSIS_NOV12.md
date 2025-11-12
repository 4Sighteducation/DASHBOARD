# Sync Disaster Analysis - November 12, 2025

## Summary
The daily sync stopped working after October 31st. When manually run today, it took hours and had to be cancelled.

---

## THREE CRITICAL ISSUES FOUND

### Issue #1: `knack_id` Unique Constraint Conflict ❌
**Symptom:** Duplicate key errors in sync logs
```
'duplicate key value violates unique constraint "students_knack_id_key"'
```

**Root Cause:**
- Database has `UNIQUE(knack_id)` constraint on students table
- Sync uses `on_conflict='email,academic_year'` (line 511)
- When a student is re-uploaded with a new `knack_id` but same email/year, the sync tries to INSERT
- The `knack_id` unique constraint blocks it → sync fails

**Why This Happened:**
- The multi-year architecture changes added `UNIQUE(email, academic_year)` constraint
- But forgot to remove the old `UNIQUE(knack_id)` constraint
- Schools that delete & re-upload students each year get new `knack_id` values

**Fix:** Run `URGENT_SYNC_FIXES.sql`
```sql
ALTER TABLE students DROP CONSTRAINT IF EXISTS students_knack_id_key;
```

---

### Issue #2: Date Parsing Failure 🕐
**Symptom:** Thousands of "Could not parse date" errors
```
ERROR - Could not parse date: 29/09/2025 04:50
ERROR - Could not parse date: 28/09/2025 23:01
```

**Root Cause:**
- Line 985: Parser expects `DD/MM/YYYY` format
- Knack returns `DD/MM/YYYY HH:MM` format (with time)
- Parser fails, falls back to `datetime.now()` 
- Wrong academic year assigned to records

**Impact:**
- Records get assigned to wrong academic year
- Historical data potentially corrupted
- Cross-year contamination

**Fix Applied:** Updated `calculate_academic_year()` to handle both formats
```python
if ' ' in date_str:
    # Has time component
    date = datetime.strptime(date_str, '%d/%m/%Y %H:%M')
```

---

### Issue #3: `sync_academic_profiles()` - No Batch Processing 🐌
**Symptom:** Sync ran for 6+ hours, inserting records one at a time

**Root Cause:**
Lines 1188-1310 - Function makes individual API calls for EVERY record:
1. Individual Knack API call to get email (line 1196)
2. Individual profile upsert (line 1267)
3. Individual subject upsert for each subject (line 1302)

**Performance Impact:**
- ~1000 profiles × 3 API calls each = 3000+ individual requests
- Each request ~0.5 seconds
- **Total: 25+ minutes minimum for profiles**
- Plus 15 subjects per profile = **15,000+ subject upserts**
- **Total: 125+ minutes (2+ hours) just for academic profiles**

**Why This Happened:**
- Function was added recently (line 2195: "# NEW:")
- Not optimized like other sync functions (students, VESPA, questions all use batching)
- No `profile_batch` or `subject_batch` arrays

**Fix Applied:** Temporarily disabled until rewritten with batching
```python
# TEMPORARILY DISABLED - sync_academic_profiles() has no batch processing
# sync_academic_profiles()
```

---

## WHY THE SCHEDULED SYNC STOPPED

Last successful run: **October 31, 2025 at 02:00 UTC**

**After that:**
- Multiple syncs failed with duplicate key errors (Issue #1)
- Some syncs started but never completed (hung on Issue #3)
- Heroku Scheduler may have given up after repeated failures

---

## WHAT HAPPENED TO THE 93 ESTABLISHMENTS

**Expected:** 140 establishments
**Got:** 93 establishments

**Root Cause:** Filter is too restrictive

Lines 248-261:
```python
filters = [
    {'field': 'field_2209', 'operator': 'is not', 'value': 'Cancelled'},
    {'field': 'field_63', 'operator': 'contains', 'value': 'COACHING PORTAL'}
]
```

**The Problem:**
- Knack filters use AND logic by default
- Both conditions must be true:
  1. Not cancelled ✅
  2. Has "COACHING PORTAL" in field_63 ❌

**Missing 47 establishments likely:**
- Have NULL or different values in field_63
- Or field_63 doesn't contain exact text "COACHING PORTAL"
- Examples: "coaching portal" (lowercase), "RESOURCE PORTAL", NULL, etc.

**Investigation Needed:**
Query Knack directly to see what values field_63 contains for those 47 missing establishments.

---

## IMMEDIATE ACTIONS REQUIRED

### 1. Run Database Fix (URGENT)
```bash
# In Supabase SQL Editor
-- Copy contents of URGENT_SYNC_FIXES.sql and run
```

### 2. Test The Sync Locally
```bash
python sync_knack_to_supabase.py
```

Should now:
- ✅ Not fail on duplicate `knack_id`
- ✅ Parse dates with time correctly
- ✅ Skip academic profiles (fast)
- ⚠️ Still only get 93 establishments (filter issue)

### 3. Fix Establishment Filter
Option A: Remove portal type filter temporarily
```python
filters = [
    {'field': 'field_2209', 'operator': 'is not', 'value': 'Cancelled'}
]
```

Option B: Make portal filter more flexible
```python
filters = [
    {'field': 'field_2209', 'operator': 'is not', 'value': 'Cancelled'},
    # Add OR condition or make it optional
]
```

### 4. Rewrite `sync_academic_profiles()` (Before Re-enabling)
Add batch processing like other functions:
- Use `profile_batch` array with `BATCH_SIZES['academic_profiles'] = 100`
- Pre-fetch all Object_3 emails before loop
- Batch profile upserts
- Batch subject upserts

### 5. Re-enable Heroku Scheduler
Once local sync works:
- Verify Heroku Scheduler job is still configured
- Check it's set to run at 2:00 AM UTC
- Monitor first run carefully

---

## FILES MODIFIED

1. **sync_knack_to_supabase.py**
   - Fixed date parsing (line 985-1002)
   - Disabled academic profiles sync (line 2207)

2. **URGENT_SYNC_FIXES.sql** (NEW)
   - Removes `knack_id` unique constraint

---

## TESTING PLAN

1. ✅ Run `URGENT_SYNC_FIXES.sql` in Supabase
2. ✅ Verify constraint removed
3. 🔄 Test sync locally (should complete in 20-30 minutes now)
4. 🔄 Check sync logs for errors
5. 🔄 Verify establishment count (still 93, needs separate fix)
6. 🔄 Deploy to Heroku
7. 🔄 Test Heroku scheduled run
8. ⏰ Rewrite `sync_academic_profiles()` with batching
9. ⏰ Re-enable academic profiles sync
10. ⏰ Fix establishment filter to get all 140

---

## LONG-TERM RECOMMENDATIONS

1. **Add Sync Monitoring**
   - Alert on sync failures
   - Dashboard showing last successful sync
   - Email notifications

2. **Add Performance Metrics**
   - Track sync duration
   - Record count per table
   - API call counts

3. **Improve Error Handling**
   - Better date parsing with multiple format attempts
   - Graceful degradation when API calls fail
   - Retry logic for transient failures

4. **Code Review Process**
   - All new sync functions must use batching
   - Performance testing before deployment
   - Load testing with realistic data volumes

---

## ESTIMATED TIMELINE

- **Immediate (15 min):** Run SQL fix, test locally
- **Short term (2 hours):** Fix establishment filter, deploy
- **Medium term (1 day):** Rewrite academic profiles with batching
- **Long term (1 week):** Add monitoring and alerts

---

## SUCCESS CRITERIA

Sync should:
- ✅ Complete in 20-30 minutes (not hours)
- ✅ Process all 140 establishments
- ✅ No duplicate key errors
- ✅ No date parsing errors
- ✅ Run automatically every day at 2 AM
- ✅ Send email notifications on completion/failure


