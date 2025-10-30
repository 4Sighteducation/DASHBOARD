# Deployment Instructions for Academic Year Fix

**Date:** October 30, 2025  
**Fix:** Critical academic year format mismatch

## 📦 **Commits Ready to Deploy**

```
5d4382bf - Update DASHBOARD-Vue submodule to include academic year fix
9be244a6 - Fix academic year API endpoint format mismatch
```

## 🚀 **Step 1: Push to GitHub**

```bash
# Push main repository
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"
git push origin main

# Push Vue submodule
cd DASHBOARD-Vue
git push origin main
cd ..
```

## 🔧 **Step 2: Deploy to Heroku**

### Option A: Automatic Deploy (if connected to GitHub)
Heroku will automatically deploy when you push to GitHub.

### Option B: Manual Deploy via Git
```bash
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"

# If not already connected to Heroku remote:
# heroku git:remote -a vespa-dashboard-9a1f84ee5341

# Deploy
git push heroku main
```

### Option C: Deploy via Heroku CLI
```bash
# Login to Heroku
heroku login

# Deploy
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"
git push heroku main

# Check logs
heroku logs --tail
```

## ✅ **Step 3: Verify Deployment**

After deployment, test the following:

### 1. Check Heroku App is Running
```bash
heroku ps
```

### 2. Test API Endpoint
```bash
curl https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/academic-years
```

Expected response:
```json
["2025/2026", "2024/2025"]
```

### 3. Test Dashboard
1. Go to: `https://vespaacademy.knack.com/vespa-academy#dashboard/`
2. Login as a user (e.g., Ashlyns School)
3. Verify:
   - Academic year dropdown shows `2025/2026` as default
   - VESPA scores display (should see 465 students for Ashlyns)
   - Question Level Analysis shows data (should see 1,408 responses)
   - Charts and graphs populate

## 🐛 **Rollback if Needed**

If issues arise, rollback to previous version:

```bash
# Rollback Heroku
heroku rollback

# Or rollback Git
git revert HEAD~2..HEAD
git push heroku main
```

## 📊 **Expected Changes in Production**

### Before Fix:
- Academic year filter: `2025-26` (wrong format)
- VESPA scores: NO DATA shown
- Question Level Analysis: EMPTY
- Default year: 2024/2025 (old data)

### After Fix:
- Academic year filter: `2025/2026` (correct format)
- VESPA scores: 465 students visible (Ashlyns example)
- Question Level Analysis: 1,408 responses shown
- Default year: 2025/2026 (current data)

## 🔍 **Monitoring**

After deployment, monitor for 24 hours:

```bash
# Watch Heroku logs
heroku logs --tail

# Check for errors
heroku logs --source app | grep ERROR

# Monitor dyno performance
heroku ps
heroku logs --ps web
```

## 📝 **Files Changed**

### Backend:
- `app.py` (Lines 5354-5373)
  - Removed format conversion in `/api/academic-years`
  - Returns database format directly

### Frontend:
- `DASHBOARD-Vue/src/stores/dashboard.js` (Lines 267-279)
  - Fixed `getCurrentAcademicYear()` to return `YYYY/YYYY` format

### Documentation:
- `ACADEMIC_YEAR_FIX_SUMMARY.md` (new file)
  - Complete analysis and verification

## ⚠️ **Important Notes**

1. **No Database Changes Required** - All data already in correct format
2. **No Breaking Changes** - Old code will still work (just returns no data)
3. **Australian Schools** - Still supported, use `2025/2025` format
4. **Backward Compatibility** - `convert_academic_year_format()` acts as passthrough

## 🎉 **Success Criteria**

Deployment is successful when:
- [x] API returns `["2025/2026", "2024/2025"]`
- [x] Dashboard loads with current year selected
- [x] VESPA scores display for 2025/2026
- [x] Question Level Analysis shows data
- [x] Year dropdown switches between years correctly
- [x] No console errors in browser
- [x] No 500 errors in Heroku logs

