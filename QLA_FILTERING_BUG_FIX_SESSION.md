# QLA Filtering Bug Fix - Complete Session Documentation

**Date**: October 30, 2025  
**Duration**: Extended debugging session  
**Status**: Partially fixed, requires full re-sync to complete

---

## 🎯 Executive Summary

### Problem Discovered
The Question Level Analysis (QLA) tab was showing **incorrect n (student count) values** that didn't match the Overview tab's completion rates. This was caused by multiple layers of filtering and data calculation issues.

### Root Causes Found
1. **Backend API bug**: QLA endpoint wasn't filtering question_responses by academic_year
2. **Supabase stored procedure bug**: Calculated academic_year from CURRENT_DATE instead of using actual data
3. **Sync script issue**: Question_responses calculated academic_year independently from VESPA scores
4. **Data corruption**: Oct 29 sync created duplicate question_responses with wrong academic_year tags

---

## 📊 The Data Issue - Coffs Harbour Example

### Expected Numbers (from Overview tab)
- **2025/2026 Cohort**: 76 total students, 51 completed Cycle 1
- **2024/2025 Cohort**: 99 total students, 79 completed Cycle 1

### What QLA Was Showing (WRONG)
- **2025/2026 Cycle 1**: n = 135 (should be ~51)
- **2024/2025 Cycle 1**: n = 60 (should be ~79)

### The Math That Revealed the Problem
135 ≈ 79 + 51 (mixing both cohorts!)
This proved data from multiple academic years was being combined.

---

## 🏗️ Architecture Overview

### Data Flow
```
Knack (Object_10 + Object_29)
    ↓ sync_knack_to_supabase.py
Supabase (students, vespa_scores, question_responses)
    ↓ calculate_question_statistics_enhanced() SQL procedure
Supabase (question_statistics table - pre-aggregated)
    ↓ app.py /api/qla endpoint
Frontend (Vue Dashboard)
```

### The Problem Areas
1. **Sync**: Creates question_responses with academic_year
2. **Stored Procedure**: Aggregates into question_statistics
3. **Backend API**: Fetches and filters question_statistics
4. **Frontend**: Displays whatever backend sends

---

## 🔧 Fixes Applied

### 1. Backend API Fix (`app.py`)

#### Location: Lines 6524-6525, 6679, 6704
```python
# Convert academic_year format ONCE at the start
formatted_year = convert_academic_year_format(academic_year, to_database=True) if academic_year else None

# Use formatted_year consistently in all queries
vespa_check = supabase_client.table('vespa_scores')\
    .eq('academic_year', formatted_year)\  # Was using raw format
    
responses_query = supabase_client.table('question_responses')\
    .eq('academic_year', formatted_year)  # Added this filter
```

**What This Fixes**:
- QLA endpoint now filters question_responses by academic_year (was missing)
- Uses consistent database format (2025/2026 not 2025-26)
- Variable scope issue fixed (formatted_year available throughout function)

#### Location: Lines 382-402, 2872-2874, 3066-3074
```python
def strip_html_tags(text):
    """Remove HTML tags from comment text"""
    import re
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text.strip()

# Applied to word cloud and comment themes endpoints
clean_text = strip_html_tags(comment['comment_text'])
```

**What This Fixes**:
- Student comments no longer show `<p>`, `</p>` tags in UI
- Word cloud extracts words properly without HTML artifacts

**Status**: ✅ Deployed to Heroku (v286)

---

### 2. Supabase Stored Procedure Fix

#### File: `fix_question_statistics_correct.sql`

**Original Bug** (lines 68-77 of old SQL):
```sql
CASE 
    WHEN e.is_australian AND EXTRACT(MONTH FROM CURRENT_DATE) >= 7 
        THEN EXTRACT(YEAR FROM CURRENT_DATE)::TEXT || '/' || ...
```
Used CURRENT_DATE to calculate academic_year, mixing all data together!

**Fix Applied**:
```sql
SELECT 
    s.establishment_id,
    qr.question_id,
    qr.cycle,
    qr.academic_year,  -- ✅ Use actual academic_year from question_responses
    qr.response_value
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE qr.response_value IS NOT NULL
  AND qr.academic_year IS NOT NULL
```

**What This Fixes**:
- Statistics now group by actual academic_year from data
- Separate stats for 2024/2025 and 2025/2026
- No longer assumes all data is "current year"

**Status**: ✅ Updated in Supabase

---

### 3. Sync Script Fix (`sync_knack_to_supabase.py`)

#### Change A: Load VESPA Academic Year Map (Lines 771-791)
```python
# NEW: Pre-load all VESPA academic_years
vespa_academic_year_map = {}  # Key: (student_id, cycle) -> academic_year
# ... loads all VESPA scores to determine correct academic_year for each student/cycle
```

#### Change B: Use VESPA Map Instead of Calculating (Lines 840-846)
```python
for cycle in [1, 2, 3]:
    # Look up academic_year from matching VESPA score
    vespa_key = (student_id, cycle)
    academic_year_for_cycle = vespa_academic_year_map.get(vespa_key)
    
    if not academic_year_for_cycle:
        continue  # Skip if no VESPA for this cycle
    
    # Use academic_year_for_cycle instead of calculating from Object_29
```

#### Change C: Fixed Python Fallback Grouping (Lines 1441-1475)
```python
# Group by question AND academic_year
question_groups = {}  # Key: (question_id, academic_year)
for resp in responses.data:
    qid = resp['question_id']
    year = resp.get('academic_year')
    key = (qid, year)
    # ... groups properly by year
```

**What This Fixes**:
- Question responses inherit academic_year from VESPA scores
- Respects the "Cycle 1 determines cohort" logic
- Handles Coffs Harbour edge case correctly
- Prevents future mismatches

**Status**: ⚠️ Ready to commit, needs testing with full sync

---

## 🎓 The Coffs Harbour Edge Case

### Background
Coffs Harbour is an Australian school that switched to UK academic calendar mid-year.

### Field Configuration
- **field_3573** (`is_australian`): `true`
- **field_3752** (`use_standard_year`): `true` (NEW field added today)

### The Logic
```
Normal Australian: is_australian=true, use_standard_year=false → Calendar year (2025/2025)
Normal UK: is_australian=false, use_standard_year=true → Aug-Jul (2025/2026)
Coffs Harbour: is_australian=true, use_standard_year=true → Aug-Jul (2025/2026) ✅
```

### Timeline
- **Before August 2025**: Students in 2024/2025 cohort
- **August 2025**: Some students completed Cycle 3 (still 2024/2025 cohort)
- **September 2025**: School switched to UK calendar
- **October 2025**: New students started (2025/2026 cohort)

### The "Cycle 1 Determines Cohort" Rule
**Critical Principle**: A student's academic_year is determined by when they completed **Cycle 1**, and ALL their cycles (1, 2, 3) belong to that same academic year.

**Example**:
- Student completes C1 in March 2025 → 2024/2025 cohort
- Same student completes C3 in August 2025 → Still 2024/2025 cohort (not 2025/2026!)

---

## 🐛 Bugs Discovered During Session

### Bug 1: Backend API Not Filtering
**File**: `app.py` line 6669-6704  
**Issue**: QLA endpoint fetched question_responses but only filtered by cycle, not academic_year  
**Impact**: Mixed responses from all years  
**Fix**: Added academic_year filter to responses query  
**Status**: ✅ Fixed and deployed

### Bug 2: Variable Scope Issue
**File**: `app.py` line 6524  
**Issue**: `formatted_year` only defined inside conditional blocks  
**Impact**: Undefined variable when filters applied  
**Fix**: Convert academic_year at function start, use throughout  
**Status**: ✅ Fixed and deployed

### Bug 3: Stored Procedure Wrong Calculation
**File**: Supabase SQL procedure  
**Issue**: Used CURRENT_DATE to calculate academic_year instead of using qr.academic_year  
**Impact**: All data assigned to "current year", mixed together  
**Fix**: Use actual academic_year field from question_responses  
**Status**: ✅ Fixed in Supabase

### Bug 4: Question Responses Wrong Academic Year
**File**: `sync_knack_to_supabase.py` lines 796-814 (OLD)  
**Issue**: Calculated academic_year from Object_29 completion date, not matching VESPA  
**Impact**: Responses tagged with different year than their VESPA score  
**Fix**: Load VESPA academic_year map, use that for responses  
**Status**: ⚠️ Fixed in code, needs full re-sync to apply

### Bug 5: Oct 29 Sync Created Duplicates
**Issue**: Recent sync created duplicate question_responses with wrong academic_year  
**Impact**: Same responses exist in both 2024/2025 and 2025/2026  
**Fix**: Manual deletion of Oct 29 duplicates (see SQL below)  
**Status**: ⚠️ Partially cleaned, full re-sync recommended

---

## 📝 SQL Fixes Applied

### Fix 1: Updated Stored Procedure
```sql
CREATE OR REPLACE FUNCTION calculate_question_statistics_enhanced()
RETURNS void AS $$
BEGIN
    DELETE FROM question_statistics WHERE true;
    
    INSERT INTO question_statistics (...)
    WITH question_data AS (
        SELECT 
            s.establishment_id,
            qr.question_id,
            qr.cycle,
            qr.academic_year,  -- ✅ Use actual from data
            qr.response_value
        FROM question_responses qr
        JOIN students s ON qr.student_id = s.id
        WHERE qr.response_value IS NOT NULL
          AND qr.academic_year IS NOT NULL
    )
    -- Groups by actual academic_year
    GROUP BY establishment_id, question_id, cycle, academic_year
END;
$$ LANGUAGE plpgsql;
```

### Fix 2: Deleted Oct 29 Duplicates
```sql
-- CAUTION: This was run on WRONG school first!
-- Then corrected for Coffs Harbour
DELETE FROM question_responses
WHERE created_at >= '2025-10-29 00:00:00'
  AND student_id IN (
    SELECT id FROM students 
    WHERE establishment_id = 'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
  );
-- Deleted too much, needs re-sync to restore
```

---

## 🚨 Current State & Issues

### What's Working ✅
- Overview tab shows correct completion rates (79/99 for 2024-25, 51/76 for 2025-26)
- VESPA scores have correct academic_year values
- Backend API filtering logic is correct
- Stored procedure logic is correct
- HTML tags stripped from comments

### What's Broken ❌
- QLA showing n=0 for Coffs Harbour (deleted too much data)
- Some responses still have wrong academic_year tags
- question_statistics needs recalculation after data cleanup

### Remaining Mismatches in question_responses
From investigation SQL:
```
response_year: "2025/2026", vespa_year: "2024/2025", cycle 3: 320 responses, 10 students
```

These are responses tagged as 2025/2026 but their VESPA says 2024/2025 (from Aug 1 sync with old logic).

---

## 🚀 Recommended Next Steps

### Tonight (Before Sync)
1. **Delete old records from Knack** (as you planned)
   - This will trigger full re-sync tomorrow
   - Clean slate approach

### Tomorrow (After Sync)
2. **Let sync run with new logic**
   - Will use VESPA academic_year map
   - Should create all question_responses correctly

3. **Verify in Supabase**
```sql
-- Check for any mismatches
SELECT 
  qr.academic_year as response_year,
  vs.academic_year as vespa_year,
  qr.cycle,
  COUNT(*) as mismatched
FROM question_responses qr
JOIN vespa_scores vs ON qr.student_id = vs.student_id AND qr.cycle = vs.cycle
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = 'caa446f7-c1ad-47cd-acf1-771cacf10d3a'
  AND qr.academic_year != vs.academic_year
GROUP BY qr.academic_year, vs.academic_year, qr.cycle;
```
Expected: ZERO rows

4. **Recalculate statistics**
```sql
SELECT calculate_question_statistics_enhanced();
SELECT calculate_national_question_statistics();
```

5. **Test Dashboard**
   - 2025-26 C1: n should be ~51
   - 2024-25 C1: n should be ~79

---

## 🔍 Key SQL Queries for Investigation

### Get Establishment UUID
```sql
SELECT id, knack_id, name, is_australian, use_standard_year
FROM establishments
WHERE name ILIKE '%coffs%';
```

### Check Question Response Alignment
```sql
SELECT 
  qr.academic_year as response_academic_year,
  qr.cycle,
  COUNT(DISTINCT qr.student_id) as unique_students,
  COUNT(*) as total_responses,
  MIN(s.academic_year) as min_student_year,
  MAX(s.academic_year) as max_student_year
FROM question_responses qr
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = 'YOUR-UUID-HERE'
GROUP BY qr.academic_year, qr.cycle
ORDER BY qr.academic_year DESC, qr.cycle;
```

### Check for Mismatches with VESPA
```sql
SELECT 
  qr.academic_year as response_year,
  vs.academic_year as vespa_year,
  qr.cycle,
  COUNT(*) as mismatched_responses,
  COUNT(DISTINCT qr.student_id) as students
FROM question_responses qr
JOIN vespa_scores vs ON qr.student_id = vs.student_id AND qr.cycle = vs.cycle
JOIN students s ON qr.student_id = s.id
WHERE s.establishment_id = 'YOUR-UUID-HERE'
  AND qr.academic_year != vs.academic_year
GROUP BY qr.academic_year, vs.academic_year, qr.cycle;
```

### Verify question_statistics
```sql
SELECT 
  academic_year,
  cycle,
  question_id,
  count,
  mean,
  calculated_at
FROM question_statistics
WHERE establishment_id = 'YOUR-UUID-HERE'
  AND cycle = 1
ORDER BY academic_year DESC, question_id
LIMIT 10;
```

---

## 💡 Technical Details

### Academic Year Calculation Logic

The `calculate_academic_year()` function in `sync_knack_to_supabase.py` (lines 984-1036):

```python
def calculate_academic_year(date_str, establishment_id=None, is_australian=None, use_standard_year=None):
    # Priority:
    # 1. If use_standard_year is YES or NULL: Use UK August cutoff
    # 2. If use_standard_year is NO and is_australian: Use calendar year
    # 3. Otherwise: UK August cutoff
    
    if use_standard_year is None or use_standard_year == True:
        # UK academic year (Aug-Jul)
        if date.month >= 8:
            return f"{date.year}/{date.year + 1}"
        else:
            return f"{date.year - 1}/{date.year}"
    elif is_australian:
        # Australian calendar year (Jan-Dec)
        return f"{date.year}/{date.year}"
    # ... etc
```

### VESPA Score Academic Year (Correct)
- Uses field_855 (completion date) from Object_10
- Calls `calculate_academic_year()` with establishment settings
- Respects `use_standard_year` flag
- **Works correctly** ✅

### Question Response Academic Year (WAS WRONG, NOW FIXED)

**Old Logic (Bug)**:
```python
# Used Object_29's field_856 (completion date)
completion_date_obj29 = record.get('field_856')
academic_year_obj29 = calculate_academic_year(completion_date_obj29)
# Problem: Object_29 date might differ from Object_10 date!
```

**New Logic (Fix)**:
```python
# Load VESPA academic_year map
vespa_academic_year_map = {}  # (student_id, cycle) -> academic_year
# ... load from vespa_scores ...

# Use VESPA's academic_year for question responses
vespa_key = (student_id, cycle)
academic_year_for_cycle = vespa_academic_year_map.get(vespa_key)
# Ensures question_responses always match their VESPA score
```

---

## 📋 Files Modified

### Backend
- ✅ `app.py` - API endpoints fixed
  - strip_html_tags() function added
  - QLA endpoint academic_year filtering fixed
  - Variable scope fixed

### Sync Script  
- ⚠️ `sync_knack_to_supabase.py` - Question response logic changed
  - VESPA map loading added
  - Object_29 date calculation removed
  - Now inherits academic_year from VESPA scores
  - Python fallback grouping fixed

### SQL
- ✅ `fix_question_statistics_correct.sql` - Stored procedure corrected
  - Uses actual academic_year from data
  - Groups properly by year

### Frontend
- ✅ **NO CHANGES NEEDED** - Frontend was always correct!
  - Already sends academic_year parameter
  - Just displays what backend sends

---

## ⚠️ Lessons Learned

### 1. The Cycle 1 Cohort Rule
**Critical Principle**: A student's academic_year is determined by when they completed Cycle 1, and ALL their cycles belong to that cohort.

**Why This Matters**:
- Prevents students from being split across years
- Maintains cohort integrity
- Handles edge cases like August completions

### 2. VESPA is Source of Truth
Question responses should **ALWAYS** inherit academic_year from their matching VESPA score, not calculate independently.

**Reason**: VESPA score uses Object_10's completion date with proper establishment settings. Question responses from Object_29 might have different completion dates.

### 3. Pre-Aggregated Data Can Hide Bugs
The `question_statistics` table made debugging harder because:
- Backend used pre-calculated data when no filters applied
- Bugs in calculation weren't visible in API
- Need to check both the table AND the live calculation path

### 4. Always Get Correct Establishment UUID!
We wasted time (and deleted data!) by investigating the wrong school. Always verify the UUID matches the school name.

---

## 🔧 Troubleshooting Guide

### QLA Shows Wrong n Values

**Check 1: Are question_responses aligned with VESPA?**
```sql
-- Should return ZERO rows
SELECT COUNT(*) FROM question_responses qr
JOIN vespa_scores vs ON qr.student_id = vs.student_id AND qr.cycle = vs.cycle
WHERE qr.academic_year != vs.academic_year;
```

**Check 2: Is question_statistics up to date?**
```sql
-- Check calculated_at timestamp
SELECT MAX(calculated_at) FROM question_statistics;
-- Should be recent (after last sync)
```

**Check 3: Is backend filtering correctly?**
- Check Heroku logs for QLA API calls
- Look for "formatted_year" in logs
- Verify it's using the filter

### Overview Shows Correct Data But QLA Doesn't

This indicates:
- VESPA scores are correct ✅
- question_statistics is wrong ❌
- Run `SELECT calculate_question_statistics_enhanced();`

### Frontend Shows HTML Tags

This indicates:
- Backend strip_html_tags() not working
- Check app.py deployment version
- Verify Heroku deployed correctly

---

## 📊 Data Quality Checks

### After Every Sync, Run These:

```sql
-- 1. Check for mismatches
SELECT 
  COUNT(*) as total_mismatches,
  COUNT(DISTINCT qr.student_id) as affected_students
FROM question_responses qr
JOIN vespa_scores vs ON qr.student_id = vs.student_id AND qr.cycle = vs.cycle
WHERE qr.academic_year != vs.academic_year;
-- Expected: 0

-- 2. Verify academic_year distribution
SELECT 
  academic_year,
  cycle,
  COUNT(DISTINCT student_id) as students,
  COUNT(*) as responses
FROM question_responses
GROUP BY academic_year, cycle
ORDER BY academic_year DESC, cycle;
-- Should match VESPA completion counts

-- 3. Check question_statistics freshness
SELECT 
  academic_year,
  cycle,
  COUNT(DISTINCT question_id) as questions_calculated,
  MAX(calculated_at) as last_calculated
FROM question_statistics
GROUP BY academic_year, cycle
ORDER BY academic_year DESC, cycle;
-- calculated_at should be recent
```

---

## 🎯 Success Criteria

### When Everything is Working:

1. **Overview Tab**
   - Shows correct completion rates
   - Academic year filter works
   - Cycle selector works

2. **QLA Tab**  
   - n values match Overview completion counts
   - 2025-26 C1: n ≈ 51
   - 2024-25 C1: n ≈ 79
   - Top/Bottom questions shown
   - Insights show percentages

3. **Insights Tab**
   - Word cloud displays without HTML tags
   - Comments show clean text
   - Academic year filter works

4. **Database**
   - Zero mismatches between question_responses and vespa_scores
   - question_statistics grouped by academic_year
   - No duplicate responses

---

## 🔄 Recovery Plan

### If Data Gets Corrupted

1. **Backup Current State**
```sql
-- Export question_responses to CSV
COPY (SELECT * FROM question_responses) TO '/tmp/question_responses_backup.csv' CSV HEADER;
```

2. **Clear Corrupted Table**
```sql
DELETE FROM question_responses WHERE true;
DELETE FROM question_statistics WHERE true;
```

3. **Re-run Sync**
```bash
python sync_knack_to_supabase.py
```

4. **Verify & Recalculate**
```sql
-- Check alignment
SELECT COUNT(*) FROM question_responses qr
JOIN vespa_scores vs ON qr.student_id = vs.student_id AND qr.cycle = vs.cycle
WHERE qr.academic_year != vs.academic_year;
-- Should be 0

-- Recalculate
SELECT calculate_question_statistics_enhanced();
SELECT calculate_national_question_statistics();
```

---

## 📚 Reference: Database Schema

### question_responses
```
Columns:
- id (UUID, PK)
- student_id (UUID, FK to students)
- cycle (INTEGER, 1-3)
- academic_year (VARCHAR, e.g., "2025/2026")
- question_id (VARCHAR, e.g., "q1", "outcome_q_confident")
- response_value (INTEGER, 1-5)
- created_at (TIMESTAMP)

Unique Constraint:
UNIQUE(student_id, cycle, academic_year, question_id)
```

### question_statistics (Pre-aggregated)
```
Columns:
- id (UUID, PK)
- establishment_id (UUID, FK)
- question_id (VARCHAR)
- cycle (INTEGER)
- academic_year (VARCHAR)
- mean (DECIMAL)
- std_dev (DECIMAL)
- count (INTEGER)  ← This is what shows as "n" in QLA
- mode (INTEGER)
- distribution (JSONB array)
- calculated_at (TIMESTAMP)

Unique Constraint:
UNIQUE(establishment_id, question_id, cycle, academic_year)
```

---

## 🔗 Related Files

- `sync_knack_to_supabase.py` - Main sync script
- `app.py` - Backend API endpoints
- `fix_question_statistics_correct.sql` - Stored procedure fix
- `DASHBOARD-Vue/src/services/api.js` - Frontend API calls
- `DASHBOARD-Vue/src/components/QLA/QLASection.vue` - QLA display

---

## 📞 Quick Reference Commands

### Deploy Backend
```bash
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"
git add app.py
git commit -m "Fix message"
git push origin main
git push heroku main
```

### Run Sync Manually
```bash
python sync_knack_to_supabase.py
```

### Check Heroku Logs
```bash
heroku logs --tail --app vespa-dashboard
```

### Recalculate Statistics in Supabase
```sql
SELECT calculate_question_statistics_enhanced();
SELECT calculate_national_question_statistics();
```

---

## 🎓 Key Insights

### Architecture Complexity
The QLA data flows through 4 layers:
1. **Knack** (source data)
2. **Sync Script** (transforms and loads)
3. **Supabase** (stores and pre-calculates)
4. **Backend API** (filters and serves)
5. **Frontend** (displays)

A bug in ANY layer causes incorrect display.

### The Pre-Aggregation Trade-off
- **Benefit**: Fast queries, no real-time calculation
- **Cost**: Bugs in calculation persist until recalculated
- **Solution**: Always recalculate after data changes

### Multi-Year Support is Complex
Supporting students across multiple academic years requires:
- Careful constraint design
- Consistent academic_year calculation
- Cohort-based logic (Cycle 1 determines year)
- Edge case handling (Australian schools, mid-year switches)

---

## 🚨 Warning Signs to Watch For

1. **n values don't match completion rates** → Check question_statistics alignment
2. **Same n across all years** → Data being mixed, not grouped by academic_year
3. **HTML tags in comments** → Backend not deployed or strip_html_tags() broken
4. **0% insights** → No data in question_statistics for that year/cycle
5. **Duplicate key errors in sync** → question_responses have conflicts

---

## ✅ What to Commit Now

```bash
git add app.py sync_knack_to_supabase.py fix_question_statistics_correct.sql
git commit -m "Fix QLA filtering and question_responses academic_year logic

COMPREHENSIVE FIX:
1. Backend API: Added academic_year filter to question_responses queries
2. Backend API: Added strip_html_tags() for clean comment display
3. Stored Procedure: Use actual academic_year from data, not CURRENT_DATE
4. Sync Script: Question responses inherit academic_year from VESPA scores
5. Sync Script: Fixed Python fallback to group by academic_year

Impact:
- QLA will show correct n values after re-sync
- Comments display without HTML tags
- Respects 'Cycle 1 determines cohort' logic
- Handles Coffs Harbour edge case correctly

Note: Requires full re-sync to rebuild question_responses with correct academic_year"

git push origin main
```

---

## 📅 Timeline of This Session

1. **Initial Problem**: QLA showing n=135 instead of 51
2. **First Investigation**: Found backend wasn't filtering by academic_year
3. **First Fix**: Added academic_year filter to backend API
4. **Deployed**: No change in frontend
5. **Deeper Investigation**: Found stored procedure using CURRENT_DATE
6. **Second Fix**: Updated stored procedure SQL
7. **Still No Change**: Found question_responses had wrong academic_year values
8. **Discovery**: Oct 29 sync created duplicates with wrong tags
9. **Mistake**: Deleted data from WRONG school (UUID confusion)
10. **Correct Investigation**: Found Coffs Harbour has 6,016+ mismatched responses
11. **Cleanup Attempt**: Deleted Oct 29 data, but removed too much
12. **Current State**: Waiting for full re-sync to rebuild correctly

---

## 🎯 Final Recommendation

**DO NOT** attempt further manual SQL fixes. The data is too complex and intertwined.

**BEST PATH FORWARD**:
1. ✅ Commit the code fixes (sync script + backend)
2. ✅ Delete old Knack records tonight (as planned)
3. ✅ Let full sync run tomorrow with new logic
4. ✅ Verify with investigation SQL
5. ✅ Test dashboard shows correct n values

The code fixes are solid. The data just needs a clean rebuild.

---

## 🆘 Emergency Rollback

If sync fails tomorrow, revert sync_knack_to_supabase.py:

```bash
git log --oneline -10  # Find commit before changes
git revert <commit-hash>  # Revert to working version
git push origin main
```

Then investigate why the new logic failed before trying again.

---

**END OF DOCUMENT**

Last Updated: October 30, 2025
Session Duration: ~3 hours
Status: Code fixed, awaiting re-sync for data cleanup



