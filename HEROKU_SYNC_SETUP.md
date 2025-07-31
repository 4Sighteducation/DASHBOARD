# Heroku Backend Sync Setup Guide

## Overview

This guide sets up automated Knack → Supabase sync on Heroku, running every 6 hours.

## Setup Steps

### 1. Add the Backend Sync Script

The `sync_knack_to_supabase_backend.py` is optimized for Heroku:
- Handles 30-minute timeout limit
- No checkpoint files (stateless)
- Memory-efficient batch processing
- Graceful partial syncs

### 2. Update Procfile

Add a new process type for the sync:

```procfile
web: gunicorn app:app
sync: python sync_knack_to_supabase_backend.py
```

### 3. Deploy to Heroku

```bash
# Add and commit the new files
git add sync_knack_to_supabase_backend.py
git add HEROKU_SYNC_SETUP.md
git commit -m "Add backend sync script for Heroku scheduler"

# Push to Heroku
git push heroku main
```

### 4. Set Up Heroku Scheduler

```bash
# Add Heroku Scheduler addon (free)
heroku addons:create scheduler:standard

# Open scheduler dashboard
heroku addons:open scheduler
```

In the scheduler dashboard:
1. Click "Add Job"
2. Command: `python sync_knack_to_supabase_backend.py`
3. Frequency: Every 6 hours
4. Dyno Size: Standard-1X (or higher if needed)

### 5. Manual Testing

#### Option A: Run via Heroku CLI
```bash
# Test the sync manually
heroku run python sync_knack_to_supabase_backend.py

# Watch the logs
heroku logs --tail
```

#### Option B: Add Test Endpoint to Flask App

Add this to your `app.py`:

```python
@app.route('/api/trigger-sync', methods=['POST'])
def trigger_sync():
    """Manually trigger sync (admin only)"""
    # Add authentication check here
    auth_token = request.headers.get('Authorization')
    if auth_token != f"Bearer {os.getenv('ADMIN_SYNC_TOKEN')}":
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Run sync in subprocess to avoid blocking
        import subprocess
        subprocess.Popen(['python', 'sync_knack_to_supabase_backend.py'])
        
        return jsonify({
            'status': 'started',
            'message': 'Sync started in background. Check logs for progress.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

Set the admin token:
```bash
heroku config:set ADMIN_SYNC_TOKEN=your-secret-token-here
```

### 6. Monitor Sync Status

Check sync logs from your app:

```python
@app.route('/api/sync-status', methods=['GET'])
def get_sync_status():
    """Get recent sync status"""
    try:
        # Get last 5 sync logs
        logs = supabase.table('sync_logs')\
            .select('*')\
            .order('started_at', desc=True)\
            .limit(5)\
            .execute()
        
        # Get current data counts
        counts = {
            'establishments': supabase.table('establishments').select('id', count='exact', head=True).execute().count,
            'students': supabase.table('students').select('id', count='exact', head=True).execute().count,
            'vespa_scores': supabase.table('vespa_scores').select('id', count='exact', head=True).execute().count
        }
        
        return jsonify({
            'recent_syncs': logs.data,
            'data_counts': counts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Expected Behavior

### Full Sync (Empty Database)
- Takes 20-28 minutes
- Syncs all establishments, students, and VESPA scores
- May skip question responses if timeout approached

### Incremental Sync (Existing Data)
- Takes 5-15 minutes
- Updates new/changed records only
- Recalculates statistics

### Partial Sync (Timeout)
- Saves what it completed
- Next run continues with remaining data
- Logs show "partial" status

## Monitoring

### Heroku Logs
```bash
# View recent logs
heroku logs --tail --dyno=scheduler

# View specific sync run
heroku logs --source app --dyno=scheduler.1
```

### Supabase Dashboard
1. Check `sync_logs` table for run history
2. Monitor data counts in each table
3. Look for failed or partial syncs

### Alerts (Optional)
Set up Heroku alerts for failed jobs:
```bash
heroku addons:create sendgrid:starter
```

Then add error notification to sync script.

## Troubleshooting

### "Timeout reached"
**Normal** - Heroku limits jobs to 30 minutes. The script handles this gracefully.

### "Memory quota exceeded"
Reduce batch sizes in the script:
```python
BATCH_SIZES = {
    'students': 50,  # Reduced from 100
    'vespa_scores': 150,  # Reduced from 300
}
```

### "No data syncing"
1. Check Knack API credentials
2. Verify Supabase connection
3. Look for specific errors in logs

### "Duplicate key errors"
Run this in Supabase SQL editor:
```sql
-- Clear duplicate students
DELETE FROM students a USING students b
WHERE a.id < b.id AND a.knack_id = b.knack_id;

-- Clear duplicate scores
DELETE FROM vespa_scores a USING vespa_scores b
WHERE a.id < b.id 
AND a.student_id = b.student_id 
AND a.cycle = b.cycle;
```

## Best Practices

1. **Monitor First Few Runs** - Watch logs closely initially
2. **Check Data Integrity** - Verify counts match Knack
3. **Set Up Alerts** - Get notified of failures
4. **Regular Backups** - Backup Supabase data weekly
5. **Resource Monitoring** - Watch dyno memory usage

## Cost Considerations

- Scheduler: Free (included)
- Dyno Hours: ~12 hours/day (within free tier)
- Supabase: Check row count limits
- Consider upgrading if:
  - Sync takes > 30 minutes consistently
  - Memory errors occur
  - Need more frequent syncs

## Next Steps

1. Complete one local sync first to verify data
2. Deploy backend sync script
3. Run manual test via Heroku CLI
4. Set up scheduler for every 6 hours
5. Monitor for 24 hours
6. Adjust settings as needed