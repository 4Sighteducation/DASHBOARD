# Cycle Filtering Fix Summary

## The Problem

The VESPA Dashboard was incorrectly filtering Object_29 (psychometric questionnaire) data, causing:
- Incorrect "n" numbers for Cycles 2 and 3
- Data health check reporting false discrepancies
- Filters not working properly across cycles

## Root Cause

The VESPA automation script and the dashboard were using different approaches for storing/reading cycle data:

### How the VESPA Automation Works:
1. Stores all statement scores in **currentCycleFieldId** fields (field_794 through field_821)
2. Uses **field_863** to indicate which cycle's data is currently stored
3. Does NOT use cycle-specific fields (field_1953, field_1955, field_1956, etc.)

### What the Dashboard Was Doing Wrong:
1. Looking for data in cycle-specific fields that were never populated
2. Checking if field_1953 had data for Cycle 1, field_1955 for Cycle 2, etc.
3. These fields were empty, causing the dashboard to think there was no data

## The Fix (Updated)

After further investigation, we discovered that the VESPA automation **overwrites** previous cycle data. This means:

### 1. Object_29 (Psychometric) Filtering - REMOVED COMPLETELY

**Final Solution:**
```python
# NO CYCLE FILTER APPLIED
# The automation overwrites data, so we fetch ALL records
```

**Why:** 
- The automation stores only the CURRENT cycle's data
- When Cycle 2 is processed, Cycle 1 data is overwritten
- When Cycle 3 is processed, Cycle 2 data is overwritten
- Filtering by cycle would miss students who have moved to later cycles

### 2. Object_10 (VESPA) Filtering
This was already correct - checking if Vision score exists for the cycle:
- Cycle 1: field_155 (Vision score) is not blank
- Cycle 2: field_161 (Vision score) is not blank  
- Cycle 3: field_167 (Vision score) is not blank

## Impact

### What Works Now:
1. ✅ The "n" number shows ALL students with psychometric data (regardless of stored cycle)
2. ✅ QLA displays data from whatever cycle is currently stored for each student
3. ✅ Object_10 filtering still works correctly for VESPA scores by cycle

### Limitations Due to Automation Design:
1. ❌ Cannot filter psychometric data by specific cycles
2. ❌ Data health will show many "missing" records (expected behavior)
3. ❌ QLA shows mixed-cycle data (Cycle 1, 2, and 3 responses mixed together)
4. ❌ Historical psychometric data is lost when new cycles are processed

## Testing Recommendations

1. Clear all caches (use the refresh button)
2. Check each cycle (1, 2, 3) separately
3. Verify the "n" number matches expectations
4. Run data health check for each cycle
5. Test filters to ensure they work correctly

## Technical Details

The confusion arose because:
- The JSON mapping files show cycle-specific fields (for historical data storage)
- But the automation uses a "current cycle" approach (updating the same fields)
- The dashboard was looking for the historical fields instead of the current approach

This fix aligns the dashboard with how the automation actually stores data. 