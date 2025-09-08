# Year-End Data Migration Guide

## Critical Database Change Required

### The Problem
The current database constraint `UNIQUE(student_id, cycle)` means each student can only have ONE Cycle 1, ONE Cycle 2, and ONE Cycle 3 EVER - not one set per academic year.

### The Solution
Run `fix_vespa_scores_constraint.sql` in Supabase to change the constraint to `UNIQUE(student_id, cycle, academic_year)`.

## Year-End Process (After Database Fix)

### Option A: Clean Deletion (RECOMMENDED)
1. **Export current year data** from Supabase as backup
2. **DELETE student records** from Knack (don't just blank them)
3. **Upload new students** as fresh records
4. **Run sync** - new students will be added, old remain in Supabase as archive

**Advantages:**
- Clean separation between years
- No risk of overwriting historical data
- Students can have multiple years of Cycle 1, 2, 3 data

### Option B: Blank and Protect
1. **Export current year data** from Supabase as backup
2. **Blank student data** in Knack (keeping record structure)
3. **Run sync with protection** (already implemented)
4. **Upload new data** when ready

**Advantages:**
- Maintains record IDs
- Protection prevents null overwrites

**Disadvantages:**
- More complex
- Risk if protection fails

## How Multi-Year Data Works (After Fix)

### Example Student Journey:
```
Year 1 (2024-25):
- Sept 2024: Cycle 1 → vespa_scores(student_123, cycle_1, 2024-25)
- Jan 2025: Cycle 2 → vespa_scores(student_123, cycle_2, 2024-25)
- May 2025: Cycle 3 → vespa_scores(student_123, cycle_3, 2024-25)

Year 2 (2025-26):
- Sept 2025: Cycle 1 → vespa_scores(student_123, cycle_1, 2025-26) ✅ NEW RECORD
- Jan 2026: Cycle 2 → vespa_scores(student_123, cycle_2, 2025-26) ✅ NEW RECORD
- May 2026: Cycle 3 → vespa_scores(student_123, cycle_3, 2025-26) ✅ NEW RECORD
```

## Implementation Steps

### 1. Fix Database Constraint (ONE TIME ONLY)
```sql
-- Run fix_vespa_scores_constraint.sql in Supabase SQL Editor
```

### 2. Update Sync Code (ALREADY DONE)
- ✅ Changed upsert conflict to `student_id,cycle,academic_year`
- ✅ Added protection against null overwrites
- ✅ Fixed deduplication logic

### 3. For Each School Year-End
1. **Backup Supabase data**
2. **Choose migration method** (A or B above)
3. **Test with one school first**
4. **Run full migration**

## Special Cases

### British School Al Khubairat
- Data already lost for 2024-25
- Needs restoration from backup
- Then follow standard process

### Rochdale Sixth Form College
- Fix completion dates for proper academic year assignment
- Re-sync after dates corrected

## Protection Features

### Already Implemented:
- **Null protection**: Won't overwrite existing data with nulls
- **Academic year tracking**: Each record tagged with correct year
- **Logging**: Warnings when preservation occurs

### After Database Fix:
- **Multi-year support**: Students can have multiple years of cycles
- **Clean separation**: Each academic year is independent
- **Historical preservation**: Old data remains untouched

## Testing Checklist

Before going live:
- [ ] Database constraint updated
- [ ] Test sync with sample data
- [ ] Verify multi-year records work
- [ ] Check dashboard shows correct years
- [ ] Confirm no data loss

## Emergency Recovery

If data is accidentally overwritten:
1. Stop the sync immediately
2. Check `sync_report_*.txt` for what was changed
3. Restore from backup if needed
4. Implement protection before re-syncing
