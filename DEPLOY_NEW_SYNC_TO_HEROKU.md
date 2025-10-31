# Deploying New Sync Script to Heroku

## 🎯 Overview

The new `sync_current_year_only.py` (v3.0) is **dramatically faster and better** than the old sync:

| Metric | Old Sync | New Sync | Improvement |
|--------|----------|----------|-------------|
| **Duration** | 4 hours | 6 minutes | **40x faster** |
| **Records Processed** | 27,000+ | ~10,000 | Targeted |
| **Skip Rate** | 81.4% | 0.08% | **99.9% better** |
| **Data Protection** | ⚠️ Risky | ✅ Safe | Never touches historical data |
| **Email Report** | ❌ None | ✅ Beautiful HTML | New feature! |
| **Comment Sync** | ❌ Missing | ✅ Included | Fixed today! |

---

## 📋 Pre-Deployment Checklist

### ✅ **Completed Today:**
- [x] QLA pagination bug fixed (n=396 working)
- [x] Comment syncing re-added to script
- [x] HTML email reporting added
- [x] Backend deployed to Heroku v313

### 🧪 **Test Locally First:**
```bash
# 1. Test the new sync script
python sync_current_year_only.py

# Expected output:
#   Students synced: ~9,879
#   VESPA scores synced: ~29,632
#   Student comments synced: ~50-100
#   Duration: ~6 minutes
```

### 📊 **Verify Results in Supabase:**
```sql
-- Check Ashlyns 2025/2026 data
SELECT 
    (SELECT COUNT(*) FROM students WHERE establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec' AND academic_year = '2025/2026') as students,
    (SELECT COUNT(*) FROM vespa_scores vs JOIN students s ON vs.student_id = s.id 
     WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec' AND vs.academic_year = '2025/2026') as vespa,
    (SELECT COUNT(*) FROM student_comments sc JOIN students s ON sc.student_id = s.id 
     WHERE s.establishment_id = '308cc905-c1c9-4b71-b976-dfe4d8c7d7ec' AND sc.cycle = 1) as comments;
```

**Expected Results:**
- Students: 465
- VESPA: 465
- Comments: ~10-15 (Ashlyns has limited comments)

---

## 🚀 Deployment Steps

### **Step 1: Update Heroku Scheduler**

1. Go to Heroku Dashboard: https://dashboard.heroku.com/apps/vespa-dashboard
2. Navigate to **Resources** → **Heroku Scheduler**
3. Find the existing daily sync job
4. Click **Edit**
5. Change command from:
   ```bash
   python sync_knack_to_supabase.py
   ```
   To:
   ```bash
   python sync_current_year_only.py
   ```
6. **Save changes**

---

### **Step 2: Configure Email Notifications**

Add email environment variables in Heroku:

```bash
# Option A: SendGrid (Recommended - already have SendGrid add-on?)
heroku config:set SYNC_REPORT_EMAIL="tony@vespa.academy" --app vespa-dashboard
heroku config:set SENDGRID_API_KEY="your_sendgrid_api_key_here" --app vespa-dashboard

# Option B: Gmail SMTP (Alternative)
heroku config:set SYNC_REPORT_EMAIL="tony@vespa.academy" --app vespa-dashboard
heroku config:set GMAIL_USER="your-email@gmail.com" --app vespa-dashboard
heroku config:set GMAIL_APP_PASSWORD="your_app_password_here" --app vespa-dashboard
```

**Note:** For Gmail, you need an App Password (not your regular password):
1. Go to https://myaccount.google.com/apppasswords
2. Create new app password for "VESPA Sync"
3. Use that 16-character password

---

### **Step 3: Push Updated Sync Script to Heroku**

```bash
# The sync script is already in your repo, just push
git push heroku main
```

---

### **Step 4: Test the Scheduled Job Manually**

Run immediately to test:

```bash
heroku run python sync_current_year_only.py --app vespa-dashboard
```

Watch the output - you should see:
- ✅ Students synced
- ✅ VESPA scores synced  
- ✅ Comments synced (NEW!)
- ✅ Email sent (if configured)

---

## 📧 What the Email Report Looks Like

You'll receive a beautiful HTML email with:

### **Header Section:**
- 🔄 VESPA Sync Report
- Version 3.0 badge
- Academic year and timestamp

### **Status Banner:**
- ✅ Green for success
- ⚠️ Yellow for warnings
- ❌ Red for errors

### **Visual Stats Cards:**
```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   9,879     │ │   29,632    │ │     124     │
│  Students   │ │ VESPA Scores│ │  Comments   │
└─────────────┘ └─────────────┘ └─────────────┘
```

### **Details Section:**
- Academic years (UK & AUS)
- Records skipped
- Duration

### **Footer:**
- Link to full text report
- Timestamp

---

## 🔧 Environment Variables Summary

Add these to Heroku for full functionality:

```bash
# Required (already set):
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
KNACK_APP_ID=your_app_id
KNACK_API_KEY=your_api_key

# NEW - Email Notifications:
SYNC_REPORT_EMAIL=tony@vespa.academy
SENDGRID_API_KEY=SG.xxxxx  # OR use Gmail below
GMAIL_USER=your-email@gmail.com  # Alternative to SendGrid
GMAIL_APP_PASSWORD=16-char-password  # Alternative to SendGrid
EMAIL_FROM=noreply@vespa.academy  # Optional (for SendGrid)
```

---

## 📅 Recommended Schedule

Keep the existing schedule:
- **Frequency:** Daily at 2:00 AM UTC
- **Why:** Low traffic time, data fresh for morning users

---

## 🎯 Testing Checklist

Before going live:

- [ ] Run sync locally and verify counts
- [ ] Check Supabase for correct data
- [ ] Test dashboard shows new comments
- [ ] Verify email arrives (test with `heroku run python sync_current_year_only.py`)
- [ ] Check email formatting looks good
- [ ] Monitor first scheduled run

---

## 🆘 Rollback Plan

If issues arise:

```bash
# Heroku Scheduler → Edit job → Change command back to:
python sync_knack_to_supabase.py
```

---

## 🎉 Benefits of New Sync

1. **40x Faster** - 6 minutes vs 4 hours
2. **99.9% Better Skip Rate** - 0.08% vs 81.4%
3. **Safer** - Never touches historical data
4. **Comments Included** - Student feedback synced automatically
5. **Beautiful Email Reports** - Know immediately if sync succeeds
6. **Email-Based Matching** - More reliable than field_792 connections
7. **Easier to Debug** - Clear logging and error messages

---

## 📝 Notes

- First run will take ~6 minutes
- Subsequent runs should be faster (less new data)
- Email notifications work even if sync fails
- Text file report always saved locally
- Safe to run multiple times (idempotent with upserts)

---

**Ready to deploy when you've tested locally!** 🚀

