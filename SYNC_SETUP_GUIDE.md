# Knack to Supabase Sync Setup Guide

## Current Status ✅
1. ✅ Supabase database created with all tables
2. ✅ Supabase connected to Heroku app
3. ✅ Sync script created
4. ✅ Test scripts ready

## Next Steps

### 1. Test the Setup (Recommended First)

Run the test script locally to verify everything is configured:

```bash
python test_sync.py
```

Or test via the API endpoint:
```bash
curl -X POST https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/sync/test
```

### 2. Run Your First Sync

#### Option A: Run Locally (Good for Testing)
```bash
python sync_knack_to_supabase.py
```

This will:
- Sync all establishments
- Sync all students and VESPA scores
- Sync all question responses
- Calculate statistics

**Note:** For large schools (3000+ students), this may take 15-30 minutes.

#### Option B: Run on Heroku (One-time)
```bash
heroku run python sync_knack_to_supabase.py -a vespa-dashboard
```

### 3. Set Up Scheduled Syncs (Recommended)

Add Heroku Scheduler to run syncs automatically:

```bash
# Add the scheduler addon (free)
heroku addons:create scheduler:standard -a vespa-dashboard

# Open scheduler dashboard
heroku addons:open scheduler -a vespa-dashboard
```

In the scheduler dashboard, add a new job:
- **Command**: `python sync_knack_to_supabase.py`
- **Schedule**: Every 6 hours (or your preference)

### 4. Monitor Sync Status

Check sync logs in Supabase:
```sql
SELECT * FROM sync_logs ORDER BY started_at DESC LIMIT 10;
```

Or check the log file:
```bash
heroku logs --tail -a vespa-dashboard | grep sync
```

## What Happens During Sync

1. **Establishments**: All schools are synced first
2. **Students**: Student records are created/updated
3. **VESPA Scores**: All cycles (1, 2, 3) are synced
4. **Question Responses**: All 29 questions + outcome questions
5. **Statistics**: Pre-calculated for each school/cycle/element

## Benefits

- **No more 1000 record limit** - Sync handles all students
- **Pre-calculated statistics** - Including proper standard deviation
- **Fast queries** - Dashboard loads instantly
- **Automatic updates** - Set it and forget it

## Troubleshooting

### If sync fails:
1. Check logs: `heroku logs --tail -a vespa-dashboard`
2. Check sync_logs table in Supabase
3. Verify credentials are set correctly

### If data seems incomplete:
1. Check academic year filtering - it only syncs current year
2. Verify all cycles have been completed
3. Check field mappings in sync script

## Next: Update Dashboard API

Once sync is successful, we'll update the dashboard API endpoints to read from Supabase instead of Knack for:
- Much faster performance
- No pagination issues
- Real statistics calculation

Ready to run your first sync? 🚀