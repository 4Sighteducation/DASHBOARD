# VESPA Dashboard Supabase Integration Testing Guide

## Pre-Test Setup

### 1. Verify Environment Variables
Ensure these are set in your `.env` file:
```env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key
KNACK_API_KEY=your-knack-api-key
KNACK_APP_ID=your-knack-app-id
```

### 2. Run Initial Sync
```bash
python sync_knack_to_supabase.py
```
Expected: ~19 minutes for full sync, check `sync_report_*.txt` for results

## Backend API Testing

### Test 1: Schools Endpoint
```bash
curl http://localhost:5001/api/schools
```
Expected: JSON array of all schools with id, name, is_australian fields

### Test 2: School Statistics
```bash
# Replace with actual school ID from Test 1
curl "http://localhost:5001/api/statistics/YOUR-SCHOOL-ID?cycle=1"
```
Expected: Array of statistics for each VESPA element with 10-element distributions

### Test 3: National Statistics
```bash
curl "http://localhost:5001/api/national-statistics?cycle=1"
```
Expected: National aggregated statistics for all elements

### Test 4: Questions Endpoint
```bash
curl http://localhost:5001/api/questions
```
Expected: 32 questions with categories and field mappings

### Test 5: QLA Data
```bash
curl -X POST http://localhost:5001/api/qla-data \
  -H "Content-Type: application/json" \
  -d '{"establishment_id": "YOUR-SCHOOL-ID", "cycle": 1}'
```
Expected: Question-level analysis data

## Frontend Testing

### Test 1: Update API Module
1. In your dashboard HTML/JS, update the API import:
```javascript
// Change from
import { API } from './modules/api.js';
// To
import { API } from './modules/api_supabase.js';
```

### Test 2: School Selection
1. Load dashboard
2. School dropdown should populate from Supabase
3. Select a school
4. Statistics should load immediately (faster than Knack)

### Test 3: VESPA Score Display
1. Verify all 6 VESPA elements show (Vision, Effort, Systems, Practice, Attitude, Overall)
2. Each should display:
   - School average (1-10 scale)
   - National comparison
   - Distribution histogram with 10 bars

### Test 4: Distribution Charts
1. Click on any VESPA element
2. Histogram should show 10 bars (scores 1-10)
3. Verify counts match the statistics

### Test 5: Trust View
1. Select "Trust Analysis" if available
2. Choose a trust
3. Verify aggregated statistics across all trust schools

### Test 6: Question Level Analysis
1. Navigate to QLA section
2. Verify top/bottom performing questions load
3. Check that question text displays correctly

## Performance Testing

### Baseline Metrics (Knack)
- Initial load: ~8-12 seconds
- Cycle change: ~5-8 seconds
- Filter apply: ~3-5 seconds

### Expected Improvements (Supabase)
- Initial load: ~2-3 seconds
- Cycle change: <1 second
- Filter apply: <1 second

### Test Load Times
```javascript
// Add to console for timing
console.time('loadDashboard');
await loadDashboardData();
console.timeEnd('loadDashboard');
```

## Data Validation

### 1. Compare VESPA Averages
- School X, Cycle 1, Vision: Should match between old and new system
- National averages should be consistent

### 2. Check Distribution Arrays
- All VESPA elements: 10 elements [score1_count, ..., score10_count]
- Sum of distribution should equal total responses

### 3. Verify Student Counts
```sql
-- In Supabase SQL editor
SELECT 
    e.name,
    COUNT(DISTINCT s.id) as student_count
FROM establishments e
JOIN students s ON s.establishment_id = e.id
GROUP BY e.id, e.name
ORDER BY e.name;
```

## Scheduled Sync Testing

### 1. Manual Test
```bash
.\run_sync.bat
```
Check `sync_logs\` folder for output

### 2. Schedule Test
```powershell
# Run as Administrator
Start-ScheduledTask -TaskName "VESPA Dashboard Sync"
```

### 3. Verify Sync Results
- Check `sync_logs\latest_sync_report.txt`
- Verify new data appears in Supabase tables
- Confirm statistics recalculated

## Troubleshooting

### Issue: No data displaying
1. Check browser console for errors
2. Verify API endpoints returning data
3. Check CORS settings in app.py

### Issue: Wrong statistics
1. Verify sync completed successfully
2. Check academic year calculation
3. Ensure VESPA scores in 1-10 range

### Issue: Slow performance
1. Check Supabase dashboard for slow queries
2. Verify indexes exist on key fields
3. Check network latency

## Removing Old Systems

### 1. Disable Knack National Stats Schedule
Since Supabase sync now includes national statistics calculation:

```powershell
# Find the task
Get-ScheduledTask | Where-Object {$_.TaskName -like "*national*"}

# Disable it
Disable-ScheduledTask -TaskName "VESPA National Statistics Update"
```

### 2. Archive Old Scripts
```bash
mkdir archive
move calculate_national_averages.py archive/
move heroku_backend\calculate_national_averages.py archive/
```

## Success Criteria

✅ All schools load in dropdown  
✅ Statistics display within 3 seconds  
✅ VESPA scores show 1-10 scale  
✅ Distributions have 10 bars  
✅ National comparisons work  
✅ Trust aggregations calculate correctly  
✅ QLA data displays  
✅ Sync completes in ~20 minutes  
✅ No console errors  
✅ Performance improved by >50%

## Next Steps

1. Monitor first production sync
2. Gather user feedback on speed improvements
3. Consider adding real-time updates via Supabase subscriptions
4. Implement incremental sync for faster updates