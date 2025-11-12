# Duplicate Cycles Fix - November 12, 2025

## Issue Found
Penglais School (and potentially others) had Cycle 1 data incorrectly duplicated to Cycles 2 & 3.

## Root Cause
The sync was checking `if record.get(vision_field) is not None:` which would pass even if the field had no actual data. This created VESPA score records for cycles that didn't have real data in Knack.

## Fixes Applied

### 1. SQL Cleanup (Run Immediately)
**File:** `FIX_DUPLICATE_CYCLES_PENGLAIS.sql`

Steps:
1. Find Penglais establishment_id
2. Check for duplicates
3. Delete duplicate Cycle 2 & 3 records (only where identical to Cycle 1)
4. Verify cleanup

### 2. Sync Logic Fixed
**File:** `sync_knack_to_supabase.py` (lines 538-625)

**Changes:**
- Check if cycle has ACTUAL data: `cycle_has_data = any(v is not None for v in [vision, effort, systems, practice, attitude, overall])`
- Track which cycles have data in Knack
- **DELETE cycles from Supabase that don't exist in Knack (current year only)**

**Key improvement:**
```python
# CRITICAL: Delete cycles from Supabase that don't exist in Knack
# Only for CURRENT academic year to avoid touching historical data
current_year = calculate_academic_year(datetime.now().strftime('%d/%m/%Y'), establishment_id)
if academic_year == current_year:
    # Delete cycles that Knack doesn't have
    cycles_to_delete = [c for c in [1, 2, 3] if c not in knack_cycles_with_data]
    for cycle_to_delete in cycles_to_delete:
        supabase.table('vespa_scores')\
            .delete()\
            .eq('student_id', student_id)\
            .eq('cycle', cycle_to_delete)\
            .eq('academic_year', academic_year)\
            .execute()
```

## How It Works Now

### Scenario 1: School completes only Cycle 1
**Knack:** Has Cycle 1 data  
**Sync behavior:**
- ✅ Sync Cycle 1 to Supabase
- ✅ DELETE Cycle 2 & 3 from Supabase (if they exist)
- **Result:** Supabase matches Knack (only Cycle 1)

### Scenario 2: School completes Cycles 1 & 2
**Knack:** Has Cycles 1 & 2 data  
**Sync behavior:**
- ✅ Sync Cycles 1 & 2 to Supabase
- ✅ DELETE Cycle 3 from Supabase (if it exists)
- **Result:** Supabase matches Knack (Cycles 1 & 2)

### Scenario 3: School completes all 3 cycles
**Knack:** Has Cycles 1, 2 & 3 data  
**Sync behavior:**
- ✅ Sync all 3 cycles to Supabase
- ✅ No deletions needed
- **Result:** Supabase matches Knack (all cycles)

## Important Safeguards

1. **Historical Data Protected:**
   - Only deletes cycles for CURRENT academic year
   - Historical years (2024/2025, etc.) are never touched
   - Ensures archived data is preserved

2. **Knack is Source of Truth:**
   - If Knack doesn't have it, Supabase won't have it
   - Sync now enforces this rule

3. **No False Positives:**
   - Only creates records when cycle has ACTUAL data (at least one non-null score)
   - Won't create empty/duplicate records

## Testing Steps

### 1. Run cleanup SQL for Penglais
```sql
-- In Supabase SQL Editor, run FIX_DUPLICATE_CYCLES_PENGLAIS.sql
-- Replace {establishment_id} with actual ID from Step 1
```

### 2. Verify cleanup
Should show:
- Cycle 1: X students (unchanged)
- Cycle 2: 0 students (deleted if duplicates)
- Cycle 3: 0 students (deleted if duplicates)

### 3. Run sync
```bash
python sync_knack_to_supabase.py
```

### 4. Check Penglais again
Should still show only Cycle 1 (sync won't recreate deleted cycles)

## Deployment

### Files Modified
1. `sync_knack_to_supabase.py` - Fixed VESPA sync logic
2. `FIX_DUPLICATE_CYCLES_PENGLAIS.sql` - Cleanup script
3. `INVESTIGATE_DUPLICATE_CYCLES.sql` - Investigation queries

### Commit Message
```bash
git add sync_knack_to_supabase.py FIX_DUPLICATE_CYCLES_PENGLAIS.sql INVESTIGATE_DUPLICATE_CYCLES.sql SYNC_FIX_DUPLICATE_CYCLES_SUMMARY.md

git commit -m "Fix duplicate cycle data issue

- Only sync cycles that have actual data in Knack
- Delete Supabase cycles that don't exist in Knack (current year only)
- Treat Knack as single source of truth for VESPA scores
- Protect historical data (only affects current academic year)
- Prevent false positives from empty cycle fields"

git push origin main
```

## Success Criteria

After fix:
- ✅ Schools with only Cycle 1 show only Cycle 1 in Supabase
- ✅ No duplicate cycle data
- ✅ Knack and Supabase match exactly for current year
- ✅ Historical data unchanged
- ✅ Future syncs maintain consistency


