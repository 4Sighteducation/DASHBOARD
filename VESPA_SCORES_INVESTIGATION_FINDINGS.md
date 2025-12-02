# 🔍 VESPA Scores for Activities App - Investigation Findings

**Date**: December 2, 2025  
**Context**: Preparing Student Activities page for production  
**Status**: Investigation Complete - Ready for Action Plan

---

## 📊 CURRENT SYSTEM ARCHITECTURE

### The Two-Table System:

#### 1. **`vespa_scores`** (Source of Truth - Legacy)
- **Purpose**: Stores every VESPA questionnaire completion
- **Key fields**:
  - `student_id` (UUID) - Links to `students.id`
  - `student_email` (TEXT) - Added recently for multi-year students
  - `cycle` (INT) - 1, 2, or 3
  - `vision`, `effort`, `systems`, `practice`, `attitude`, `overall` (INT) - Scores out of 10
  - `completion_date` (DATE)
  - `academic_year` (TEXT) - e.g., "2025/2026"
- **Data**: Contains all historical VESPA scores (Cycle 1, 2, 3 for all years)
- **Updated**: When questionnaire is submitted (`submit_questionnaire()` in app.py line 9476)

#### 2. **`vespa_students`** (Cache for Activities App)
- **Purpose**: Fast lookup table for activities app (avoids complex queries)
- **Key field**: `latest_vespa_scores` (JSONB)
- **Structure**:
```json
{
  "vision": 7,
  "effort": 8,
  "systems": 6,
  "practice": 9,
  "attitude": 5,
  "overall": 7,
  "cycle_number": 2,
  "completion_date": "2025-12-02",
  "level": "Level 3"
}
```
- **Data**: Currently **NULL for most/all students** (as per handover doc line 468-473)
- **Should be updated**: Via RPC `sync_latest_vespa_scores_to_student()`

---

## 🔄 DATA FLOW

### When Student Completes Questionnaire:

1. **Frontend** (questionnaire1Q.js) calculates scores
2. **Submits** to `/api/questionnaire/submit` (app.py line 9276)
3. **Backend writes** to `vespa_scores` table (line 9476)
4. **Backend calls** RPC `sync_latest_vespa_scores_to_student()` (line 9486)
5. **RPC populates** `vespa_students.latest_vespa_scores` JSONB field

### When Student Views Activities Page:

1. **Frontend** calls `/api/activities/recommended?email=...&cycle=...`
2. **Backend** (activities_api.py line 47-64):
   - **First**: Tries `vespa_students.latest_vespa_scores` (FAST)
   - **Fallback**: Queries `vespa_scores` table by student_id (SLOW)
3. **Returns** scores + recommended activities

---

## ⚠️ THE PROBLEM

### Issue 1: Cache is Empty
- `vespa_students.latest_vespa_scores` is **NULL** for most students
- Activities page can't display scores
- Recommendations don't work properly

### Issue 2: Questionnaire Uses Different Field Names
- **Questionnaire sends**: `VISION`, `EFFORT`, `SYSTEMS`, etc. (UPPERCASE)
- **Activities expects**: `vision`, `effort`, `systems`, etc. (lowercase)
- **Current code**: Handles this correctly (line 9466: `vespa_scores.get('VISION')`)

### Issue 3: RPC May Not Exist or Is Broken
- RPC `sync_latest_vespa_scores_to_student()` is called (line 9486)
- Errors are logged but don't stop the process (line 9491)
- Need to verify RPC exists and works

---

## 🎯 SOLUTION PLAN

### Option A: **One-Time Backfill + Fix RPC** (RECOMMENDED)

**Steps**:
1. Run SQL investigation (INVESTIGATE_VESPA_SCORES_FOR_ACTIVITIES.sql)
2. Check if RPC exists and works
3. Create/fix RPC if needed
4. Run backfill script to populate cache for ALL existing students
5. Test activities page

**Advantages**:
- ✅ Fast performance (cache lookup)
- ✅ Maintains architecture
- ✅ Future questionnaires will auto-sync

### Option B: **Remove Cache, Always Query vespa_scores**

**Steps**:
1. Modify activities_api.py to always query `vespa_scores` by `student_email`
2. Remove cache lookup logic
3. Test performance

**Advantages**:
- ✅ Simpler (no cache sync)
- ✅ Always accurate

**Disadvantages**:
- ❌ Slower (joins, sorting)
- ❌ More complex queries

---

## 🔧 RPC FUNCTION NEEDED

```sql
CREATE OR REPLACE FUNCTION sync_latest_vespa_scores_to_student(p_student_email TEXT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_latest_scores JSONB;
    v_level TEXT;
BEGIN
    -- Get the most recent VESPA score for this student
    SELECT 
        jsonb_build_object(
            'vision', vision,
            'effort', effort,
            'systems', systems,
            'practice', practice,
            'attitude', attitude,
            'overall', overall,
            'cycle_number', cycle,
            'completion_date', completion_date,
            'level', 'Level 3'  -- TODO: Get from students table or calculate
        )
    INTO v_latest_scores
    FROM vespa_scores
    WHERE student_email = p_student_email
    ORDER BY completion_date DESC, cycle DESC
    LIMIT 1;
    
    -- Update vespa_students cache (upsert)
    INSERT INTO vespa_students (email, latest_vespa_scores, updated_at)
    VALUES (p_student_email, v_latest_scores, NOW())
    ON CONFLICT (email) 
    DO UPDATE SET 
        latest_vespa_scores = v_latest_scores,
        updated_at = NOW();
    
END;
$$;
```

---

## 📋 KNACK FIELD MAPPINGS (For Reference)

From your description, here are the Knack Object_10 fields:

### Current Cycle Scores (Conditional Display):
- Vision: `field_147` (shows based on current cycle)
- Effort: `field_148`
- Systems: `field_149`
- Practice: `field_150`
- Attitude: `field_151`
- Overall: `field_146`

### Cycle 1 Historical:
- Vision C1: `field_XXX` (need exact field IDs)
- Effort C1: `field_XXX`
- ... (6 fields)

### Cycle 2 Historical:
- Vision C2: `field_XXX`
- Effort C2: `field_XXX`
- ... (6 fields)

### Cycle 3 Historical:
- Vision C3: `field_XXX`
- Effort C3: `field_XXX`
- ... (6 fields)

**Total**: 18 historical fields + 6 current = 24 VESPA score fields in Knack

---

## 🎬 NEXT STEPS

### Immediate Actions:

1. **Run Investigation SQL** (INVESTIGATE_VESPA_SCORES_FOR_ACTIVITIES.sql)
   - Tells us: How many scores exist, cache status, RPC existence

2. **Check RPC Function**:
   - Query #8 in investigation will show if it exists
   - Test manually: `SELECT sync_latest_vespa_scores_to_student('test@example.com')`

3. **Based on Results**:
   - If RPC missing → Create it
   - If RPC exists → Test it works
   - If RPC broken → Fix it

4. **Backfill Cache**:
   - Run RPC for all students with scores
   - Script to loop through `vespa_scores.student_email` (DISTINCT)

5. **Test Activities Page**:
   - Check Cash's scores display
   - Check recommendations work
   - Check "Assign by Problem" modal

---

## 📝 KEY INSIGHTS

### What's Already Working:
✅ Questionnaire submission writes to `vespa_scores` (line 9476)  
✅ Multi-year student fix (student_email now populated)  
✅ Fallback logic exists (queries vespa_scores if cache empty)  

### What Needs Fixing:
❌ Cache (`vespa_students.latest_vespa_scores`) is empty  
❌ RPC may not exist or isn't working  
❌ No backfill has been run for existing data  

### Why This Matters:
- Activities page shows placeholder scores (5/10 for everything)
- Recommendations are generic (not personalized)
- "Assign by Problem" relies on accurate scores
- Student sees incorrect progress

---

## 🎨 ONCE VESPA SCORES ARE FIXED

The student activities page should show:
1. **Actual scores** in radar chart (not 5/5/5/5/5)
2. **Personalized recommendations** (activities matched to low scores)
3. **Accurate "Assign by Problem"** (problems matched to actual weaknesses)
4. **Progress tracking** (baseline vs current scores)

---

## 🚀 ESTIMATED TIMELINE

- Investigation SQL: 5 minutes
- Check/Create RPC: 10-15 minutes
- Backfill script: 10 minutes to write, 1-2 minutes to run
- Testing: 15-20 minutes

**Total**: ~45-60 minutes to complete VESPA scores accuracy

---

## 📞 QUESTIONS FOR YOU

Before I proceed, please confirm:

1. **Do you want me to run the investigation SQL?** (I can do this)

2. **Should I check if the RPC exists** and create/fix it if needed?

3. **Do you have the exact Knack field IDs** for historical cycle scores? (field_XXX for C1_Vision, C2_Vision, etc.) - Or should I find them in the code?

4. **Do you want Option A** (fix cache + RPC) or **Option B** (remove cache, always query)?
   - I recommend **Option A** for performance

5. **Are there any students currently testing the activities page** that I should prioritize (like Cash)?

---

**Ready to proceed when you give the go-ahead!** 🚀

