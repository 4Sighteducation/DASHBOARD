# Quick Sync Command Reference

## 🚀 Option 1: Complete Local Sync First (RECOMMENDED)

```bash
# 1. Check current status
python check_sync_status.py

# 2. Run optimized sync (will resume if interrupted)
python sync_knack_to_supabase_optimized.py

# 3. If it stops, just run again - it resumes!
python sync_knack_to_supabase_optimized.py

# 4. Check final status
python check_sync_status.py
```

## 🤖 Option 2: Deploy Backend First

```bash
# 1. Add and commit files
git add sync_knack_to_supabase_backend.py sync_knack_to_supabase_optimized.py
git add check_sync_status.py supabase_sync_helpers.sql
git add HEROKU_SYNC_SETUP.md SYNC_OPTIMIZATION_GUIDE.md QUICK_SYNC_COMMANDS.md
git add Procfile
git commit -m "Add optimized sync with backend support"

# 2. Push to Heroku
git push heroku main

# 3. Test sync manually
heroku run python sync_knack_to_supabase_backend.py

# 4. Watch logs
heroku logs --tail
```

## 📊 Monitoring Commands

```bash
# Check sync status locally
python check_sync_status.py

# View Heroku logs
heroku logs --tail --dyno=scheduler

# Run SQL in Supabase to check counts
SELECT COUNT(*) as students FROM students;
SELECT COUNT(*) as scores FROM vespa_scores;
SELECT COUNT(*) as establishments FROM establishments;
```

## 🔧 Troubleshooting

```bash
# Clear checkpoint to start fresh
rm sync_checkpoint.pkl

# Check what's in checkpoint
python -c "import pickle; print(pickle.load(open('sync_checkpoint.pkl', 'rb')).__dict__)"

# Test Supabase connection
python test_supabase_connection.py
```

## ⏱️ Expected Times

- First full sync: 15-25 minutes
- Resume from 30%: 10-15 minutes  
- Backend sync: 20-28 minutes
- Incremental sync: 5-10 minutes

## 🎯 My Recommendation

Run this NOW while you read the docs:

```bash
python sync_knack_to_supabase_optimized.py
```

It will:
✅ Keep your PC awake
✅ Save progress every minute
✅ Resume if interrupted
✅ Show detailed progress

Then check the results and deploy to backend!