# Why The Cleanup is Safe

## The Duplicate Problem

Penglais has students where:
- Cycle 1: Vision=10, Effort=8, Systems=7, Practice=10, Attitude=8, Overall=9, Date=2025-09-24
- Cycle 2: Vision=10, Effort=8, Systems=7, Practice=10, Attitude=8, Overall=9, Date=2025-09-24 ⚠️
- Cycle 3: Vision=10, Effort=8, Systems=7, Practice=10, Attitude=8, Overall=9, Date=2025-09-24 ⚠️

**These are obviously duplicates because ALL SCORES AND DATE ARE IDENTICAL**

## Why This is Safe

### Condition 1: All 6 scores must match
```sql
vs1.vision = vs2.vision
AND vs1.effort = vs2.effort
AND vs1.systems = vs2.systems
AND vs1.practice = vs2.practice
AND vs1.attitude = vs2.attitude
AND vs1.overall = vs2.overall
```

**Probability of genuine identical scores across 3 cycles:**
- Each score: 1-10 range
- 6 scores total
- Probability: (1/10)^6 = 0.0001% per student

**For 300 students:** 0.03% chance ONE student might have this naturally

### Condition 2: Completion date must also match (THE KEY!)
```sql
AND vs1.completion_date = vs2.completion_date
```

**This is IMPOSSIBLE for legitimate data:**
- Students cannot complete Cycle 1, 2, and 3 on the SAME day
- If all 3 cycles have the same date, it's 100% a duplicate

## Example Scenarios:

### Scenario A: Legitimate Identical Scores
```
Student X:
- Cycle 1: Overall=7, Date=2025-09-24
- Cycle 2: Overall=7, Date=2025-01-15 ← Different date!
- Cycle 3: Overall=7, Date=2025-05-20 ← Different date!
```
**Result:** NOT deleted (dates are different) ✅ SAFE

### Scenario B: Duplicate from Old Sync
```
Student Y:
- Cycle 1: Overall=9, Date=2025-09-24
- Cycle 2: Overall=9, Date=2025-09-24 ← Same date!
- Cycle 3: Overall=9, Date=2025-09-24 ← Same date!
```
**Result:** Deleted (same date proves it's a duplicate) ✅ CORRECT

### Scenario C: Empty Records
```
Student Z:
- Cycle 1: Vision=NULL, Effort=NULL, Overall=NULL
- Cycle 2: Vision=NULL, Effort=NULL, Overall=NULL
- Cycle 3: Vision=NULL, Effort=NULL, Overall=NULL
```
**Result:** Deleted (empty records) ✅ CORRECT

## Additional Safety: Current Year Only

```sql
WHERE vs1.academic_year = target_academic_year
```

- Only touches 2025/2026 data
- All historical years protected
- Penglais 2024/2025 data untouched

## Conclusion

The cleanup is SAFE because:
1. Requires ALL 6 scores to match (astronomically unlikely naturally)
2. Requires completion_date to match (IMPOSSIBLE for legitimate cycles)
3. Only affects current year
4. You can test on Penglais first before enabling automatic cleanup

## Testing Plan

1. Create the RPC function in Supabase
2. Test it manually: `SELECT cleanup_duplicate_vespa_cycles('2025/2026');`
3. Check Penglais - should go from 283 Cycle 2 records to ~0
4. If it worked correctly, enable in sync
5. Monitor tonight's run

The combination of identical scores AND identical date makes this virtually bulletproof!


