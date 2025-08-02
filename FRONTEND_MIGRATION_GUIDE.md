# Frontend Migration Guide: Knack to Supabase

## Overview
This guide helps migrate the VESPA Dashboard frontend from direct Knack API calls to the new Supabase-backed endpoints.

## Step 1: Update API Module Import

In `dashboard3y.js` and other files using the API:

```javascript
// OLD
import { API } from './modules/api.js';

// NEW
import { API } from './modules/api_supabase.js';
```

## Step 2: Update Heroku App URL

Make sure your `WorkingBridge.js` or wherever `DASHBOARD_CONFIG` is set includes:

```javascript
window.DASHBOARD_CONFIG = {
    herokuAppUrl: 'https://vespa-dashboard-9a1f84ee5341.herokuapp.com',
    // ... other config
};
```

## Step 3: Key API Changes

### Getting Schools/Establishments
```javascript
// OLD
const establishments = await API.fetchDataFromKnack('object_2');

// NEW
const establishments = await API.getSchools();
```

### Getting School Statistics
```javascript
// OLD - Multiple calls to get VESPA data
const vespaResults = await API.fetchDataFromKnack('object_10', filters);

// NEW - Single call for all statistics
const schoolStats = await API.getSchoolStatistics(establishmentId, cycle);
```

### Getting National Statistics
```javascript
// OLD
const nationalData = await API.fetchDataFromKnack('object_120', filters);

// NEW
const nationalStats = await API.getNationalStatistics(cycle);
```

### Calculating ERI
```javascript
// No change needed - the API method signature stays the same
const eri = await API.calculateSchoolERI(staffAdminId, cycle, filters, establishmentId);
```

## Step 4: Data Structure Changes

### School Statistics Response
```javascript
// NEW structure from Supabase
[
    {
        id: "uuid",
        establishment_id: "uuid",
        cycle: 1,
        academic_year: "2024-25",
        element: "vision",
        mean: 7.5,
        std_dev: 1.2,
        count: 150,
        percentile_25: 6.5,
        percentile_50: 7.5,
        percentile_75: 8.5,
        distribution: [0, 0, 2, 5, 10, 20, 35, 45, 25, 8]  // Counts for scores 1-10
    },
    // ... other elements
]
```

### National Statistics Response
Similar structure but aggregated across all schools.

## Step 5: Update Chart Rendering

The distribution arrays are now standardized to 10 elements (scores 1-10) for ALL VESPA elements:

```javascript
// Update histogram rendering to expect 10-element arrays
function renderDistributionChart(distribution, elementName) {
    const labels = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];
    // ... render with 10 bars
}
```

## Step 6: Remove Old Knack-Specific Code

- Remove direct Knack object key references
- Remove Knack field mappings (field_xxx)
- Update filter logic to use Supabase query parameters

## Step 7: Performance Benefits

With Supabase:
- Single API call gets all statistics (vs multiple Knack calls)
- Pre-calculated statistics (no client-side calculation needed)
- Faster response times
- Better error handling

## Testing Checklist

- [ ] Schools load in dropdown
- [ ] Statistics display correctly for selected school
- [ ] National comparisons work
- [ ] ERI calculations are accurate
- [ ] Distribution charts show 10 bars
- [ ] Trust-level views work
- [ ] QLA data displays correctly
- [ ] All filters function properly

## Rollback Plan

If issues arise, you can quickly rollback by:
1. Change import back to `'./modules/api.js'`
2. The old API module will continue using Knack

## Next Steps

1. Deploy updated frontend files
2. Test in staging environment
3. Monitor console for any errors
4. Check network tab for API response times
5. Verify data accuracy