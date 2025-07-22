# Data Processing Fixes for VESPA Dashboard

## Overview

This document outlines the fixes implemented to resolve data processing issues in the VESPA Dashboard, particularly addressing data health discrepancies, caching problems, and filter inconsistencies.

## Issues Identified

### 1. Data Health Check Logic Problems
- **Original Issue**: Data health check was comparing students by name (case-sensitive), causing false mismatches
- **Impact**: Reported 10 discrepancies when there were actually fewer

### 2. Multiple Caching Layers
- **Backend**: Redis cache with 5-minute TTL
- **Frontend**: In-memory DataCache and localStorage
- **Impact**: Stale data persisted even after Knack updates

### 3. Filter Application Inconsistencies
- Frontend applied filters locally on cached data
- Backend applied different filters for each query
- Cycle changes sometimes cleared cache, sometimes didn't

### 4. Object_29 Cycle Filtering
- Only checked cycle completion fields (field_1953, field_1955, field_1956)
- Missed records that had current cycle field (field_863) set

## Fixes Implemented

### 1. Improved Data Health Check Matching

**File**: `app.py`

The data health check now uses multiple matching methods:
- **Primary**: Object_10 connection field (field_792) in Object_29
- **Fallback**: Email-based matching
- **Added**: Email field (field_2301) to Object_10 fetch for proper matching

```python
# Old: Name-based matching
vespa_students[full_name.lower()] = {...}

# New: ID and email-based matching
vespa_by_id[record['id']] = record
if email: vespa_students[email] = {...}
```

### 2. Cache Bypass Mechanism

**Files**: `app.py`, `dashboard-frontend/src/dashboard3r.js`

Added `forceRefresh` parameter to bypass caching:

```javascript
// Frontend
fetchDashboardInitialData(staffAdminId, establishmentId, cycle, forceRefresh = true)

// Backend
if CACHE_ENABLED and not force_refresh:
    # Check cache
```

### 3. Data Refresh Button

**File**: `dashboard-frontend/src/dashboard3r.js`

Added refresh button to data health indicator:
- Clears all frontend caches
- Forces backend cache bypass
- Reloads all dashboard sections
- Re-checks data health

### 4. Enhanced Cycle Filtering Logic

**File**: `app.py`

Updated cycle filtering to check if actual data exists instead of using "current cycle" fields:

**Object_10 Filtering:**
- Cycle 1: Checks if field_155 (Vision Cycle 1) has data
- Cycle 2: Checks if field_161 (Vision Cycle 2) has data
- Cycle 3: Checks if field_167 (Vision Cycle 3) has data

```python
cycle_vision_fields = {
    1: 'field_155',  # Vision Cycle 1
    2: 'field_161',  # Vision Cycle 2
    3: 'field_167'   # Vision Cycle 3
}

if cycle in cycle_vision_fields:
    cycle_filter_field = cycle_vision_fields[cycle]
    base_filters.append({
        'field': cycle_filter_field,
        'operator': 'is not blank'
    })
```

**Object_29 Filtering:**
- NO CYCLE FILTERING: We fetch ALL psychometric records regardless of cycle

```python
# NO FILTER APPLIED - see comment in code
```

This is because the VESPA automation:
- Stores data in currentCycleFieldId fields (field_794-field_821)
- OVERWRITES previous cycle data when processing a new cycle
- Uses field_863 to indicate which cycle's data is currently stored
- Does NOT preserve historical cycle data

Therefore, filtering by cycle would only show students whose CURRENT data matches that cycle, missing all students who have moved on to later cycles.

This approach is more reliable because:
- It checks actual data presence, not just what the "current cycle" field says
- Avoids issues where "current cycle" field might be incorrect
- Ensures we only show records that have data for the selected cycle

## How to Use the Fixes

### 1. Refresh Data Manually
Click the refresh button (🔄) next to the data health indicator to:
- Clear all caches
- Fetch fresh data from Knack
- Update all dashboard sections

### 2. Monitor Data Health
The data health indicator shows:
- **Green**: All data synchronized
- **Amber**: Minor discrepancies (≤5%)
- **Red**: Significant issues (>5%)
- **Gray**: No data available

### 3. Debugging Tips
- Check backend logs for detailed matching information
- Look for "Missing questionnaire for student" log entries
- Verify email fields are populated in Object_10

## Technical Details

### Cache TTLs
- Dashboard data: 10 minutes (reduced from indefinite)
- Data health check: 30 seconds (reduced from 60)
- QLA insights: 5 minutes
- Comment themes: 5 minutes

### Field Mappings
- Object_10 email: field_197
- Object_29 email: field_2732
- Object_10 → Object_29 connection: field_792
- Current cycle indicator: field_863 (indicates which cycle's data is stored in currentCycleFieldId fields)
- Cycle data check fields:
  - Object_10: field_155 (Cycle 1 Vision), field_161 (Cycle 2 Vision), field_167 (Cycle 3 Vision)
  - Object_29: Uses currentCycleFieldId fields (field_794-field_821) with field_863 indicating which cycle

## Testing with Towers School

Based on your example:
- 26 Year 10 records total
- Missed Cycle 1
- Most completed Cycles 2 & 3
- Some Object_29 records incorrectly show Cycle 1 data

The fixes should now:
1. Properly match students between objects
2. Show accurate discrepancy counts
3. Allow quick data refresh without browser refresh
4. Correctly filter by selected cycle

## Next Steps

1. Test the refresh button functionality
2. Verify data health shows accurate counts
3. Check that cycle filtering works correctly
4. Monitor backend logs for any remaining issues 