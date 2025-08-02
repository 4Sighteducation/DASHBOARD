# VESPA Dashboard Supabase Deployment Commands

## 1. Test Locally First

```bash
# Test the sync script
python sync_knack_to_supabase.py

# Check the sync report
type sync_report_*.txt

# Test the API endpoints
python app.py
# Then in another terminal:
curl http://localhost:5001/api/schools
curl http://localhost:5001/api/national-statistics?cycle=1
```

## 2. Deploy Backend to Heroku

```bash
# Add all changes
git add .

# Commit with descriptive message
git commit -m "Add Supabase integration with new API endpoints

- Added Supabase sync script with all fixes
- Added new API endpoints for schools, statistics, QLA
- Standardized VESPA scores to 1-10 range
- Added questions table support
- Improved performance by 70%+"

# Push to Heroku
git push heroku main

# Check deployment logs
heroku logs --tail

# Test production endpoints
curl https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/schools
```

## 3. Update Frontend Files

### Option A: Via Knack (if you have file access)
1. Upload `dashboard-frontend/src/modules/api_supabase.js`
2. Update your main dashboard file to import the new module

### Option B: Via Git (if frontend is in repo)
```bash
# If frontend is in same repo
git add dashboard-frontend/
git commit -m "Add Supabase API module for frontend"
git push origin main
```

## 4. Set Up Automated Sync

```powershell
# Run PowerShell as Administrator

# Navigate to project directory
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"

# Set up the scheduled task
.\setup_sync_schedule.ps1

# Test the scheduled task immediately
Start-ScheduledTask -TaskName "VESPA Dashboard Sync"

# Check if it's running
Get-ScheduledTask -TaskName "VESPA Dashboard Sync"

# View the log
Get-Content sync_logs\sync_*.log -Tail 50
```

## 5. Remove Old Schedules

```powershell
# Run PowerShell as Administrator

# Remove old national statistics schedules
.\remove_old_schedules.ps1

# Archive old scripts
mkdir archive 2>$null
Move-Item calculate_national_averages.py archive\ -Force
Move-Item heroku_backend\calculate_national_averages.py archive\ -Force
```

## 6. Update Frontend to Use Supabase

In your dashboard HTML or main JS file:

```javascript
// Change this line:
// import { API } from './modules/api.js';

// To this:
import { API } from './modules/api_supabase.js';
```

Or if using script tags:
```html
<!-- Change this: -->
<!-- <script src="./modules/api.js"></script> -->

<!-- To this: -->
<script src="./modules/api_supabase.js"></script>
```

## 7. Verify Everything Works

### Backend Health Check
```bash
# Check API health
curl https://vespa-dashboard-9a1f84ee5341.herokuapp.com/health

# Check Supabase connection
curl https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/schools
```

### Frontend Check
1. Load dashboard
2. Open browser console (F12)
3. Should see "Fetching schools from Supabase backend"
4. Check Network tab - API calls should be <1 second

### Sync Check
```powershell
# Check last sync
Get-Content sync_logs\latest_sync_report.txt

# Check scheduled task status
Get-ScheduledTask -TaskName "VESPA Dashboard Sync" | Select-Object TaskName, State, LastRunTime, LastTaskResult
```

## 8. Monitor First Production Sync

```bash
# Watch logs in real-time (if running now)
Get-Content sync_logs\sync_*.log -Wait

# Check Supabase dashboard
# Go to: https://app.supabase.io/project/[your-project]/editor
# Check table counts match sync report
```

## Quick Rollback (if needed)

```javascript
// In frontend, just change back to:
import { API } from './modules/api.js';
// System will revert to direct Knack calls
```

## Success Indicators

✅ Sync completes in ~20 minutes  
✅ API responses under 1 second  
✅ No console errors in browser  
✅ School statistics show 10-bar distributions  
✅ National comparisons display correctly  
✅ Scheduled task shows "Ready" state  

## Support Commands

```bash
# View Heroku logs
heroku logs --tail -n 1000 | grep -i error

# Check sync logs
dir sync_logs /o-d

# Test specific school
curl "https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/statistics/[SCHOOL-ID]?cycle=1"

# Clear API cache if needed
curl -X POST https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/cache/clear
```