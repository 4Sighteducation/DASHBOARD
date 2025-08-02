# VESPA Dashboard Sync - Final Handover Document
Date: August 2, 2025

## Latest Sync Results (August 2, 2025)

### Summary
- **Total Duration**: 19 minutes 6 seconds
- **Status**: ✅ All tables synced successfully
- **School Statistics**: 954 records created (fresh calculation)
- **National Statistics**: 18 records created (fresh calculation)

### Table-by-Table Results:
| Table | Records Before | Records After | New Records | Duration | Status |
|-------|---------------|---------------|-------------|----------|---------|
| ESTABLISHMENTS | 109 | 109 | 0 | 0:00:11 | ✓ OK |
| STUDENTS | 24,971 | 24,971 | 0 | 0:05:40 | ✓ OK |
| VESPA_SCORES | 74,913 | 74,913 | 0 | 0:05:40 | ✓ OK |
| STAFF_ADMINS | 423 | 423 | 0 | 0:00:41 | ✓ OK |
| SUPER_USERS | 9 | 9 | 0 | 0:00:01 | ✓ OK |
| QUESTION_RESPONSES | 750,641 | 750,641 | 0 | 0:10:12 | ✓ OK |
| SCHOOL_STATISTICS | 0 | 954 | 954 | 0:02:09 | ✓ OK |
| QUESTION_STATISTICS | 5,974 | 5,974 | 0 | 0:00:02 | ✓ OK |
| NATIONAL_STATISTICS | 0 | 18 | 18 | 0:00:03 | ✓ OK |

### Known Issues (Handled Gracefully):
- 15,379 question responses skipped due to missing student links
- 253 duplicate Object_29 records removed (multiple VESPA responses for same student)

## Key Fixes Implemented

### 1. VESPA Score Standardization ✅
- ALL VESPA elements (vision, effort, systems, practice, attitude, overall) now use 10-element distribution arrays
- Scores range from 1-10 (not 0-based)
- Distribution format: `[count_of_1s, count_of_2s, ..., count_of_10s]`

### 2. Statistics Calculations ✅
- School statistics properly calculate mean, std_dev, percentiles, and distribution
- National statistics aggregate from school statistics
- Added `average` column (mirrors `mean` for compatibility)

### 3. Data Integrity ✅
- Fixed duplicate Object_29 handling
- Added proper Unicode/UTF-8 encoding
- Fixed trust relationships (E-ACT trust created and linked)
- Super users table properly synced

### 4. Database Views Ready ✅
- `current_school_averages` - Real-time school statistics
- `question_level_analysis` - QLA data

## Production Deployment Steps

### 1. Backend Deployment (Heroku)
```bash
# In DASHBOARD directory
git add .
git commit -m "Final sync fixes - standardized VESPA distributions"
git push heroku main
```

### 2. Frontend Configuration
Update `dashboard-frontend/src/modules/api.js`:
```javascript
const API_BASE_URL = 'https://your-heroku-app.herokuapp.com/api';
```

### 3. Windows Task Scheduler Setup

Create `run_sync.bat`:
```batch
@echo off
cd /d "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"
echo Starting sync at %date% %time% >> sync_log.txt
python sync_knack_to_supabase.py >> sync_log.txt 2>&1
echo Sync completed at %date% %time% >> sync_log.txt
```

Task Scheduler Configuration:
- **Trigger**: Daily at 2:00 AM
- **Action**: Run `run_sync.bat`
- **Settings**: Run whether user logged in or not
- **Credentials**: Use account with file access permissions

## API Endpoints Available

- `GET /api/schools` - List all schools
- `GET /api/statistics/<school_id>` - School statistics
- `GET /api/national-statistics` - National benchmarks
- `GET /api/qla-data` - Question Level Analysis
- `GET /api/current-averages` - Current school averages
- `GET /api/trust/<trust_id>/statistics` - Trust-level statistics

## Environment Variables Required

```env
# Knack API
KNACK_API_KEY=your-knack-api-key
KNACK_APP_ID=your-knack-app-id

# Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key

# Database (for Heroku)
DATABASE_URL=your-postgres-connection-string
```

## Monitoring

1. Check `sync_report_YYYYMMDD_HHMMSS.txt` files for sync results
2. Monitor Supabase dashboard for data integrity
3. Check Heroku logs for API errors
4. Verify statistics calculations match expected values

## Support Contacts

For issues with:
- Sync script: Check error logs in sync_report files
- Database: Supabase dashboard → SQL Editor
- API: Heroku logs → `heroku logs --tail`
- Frontend: Browser console for API errors

## New Questions Table

### Overview
A `questions` table has been added to Supabase to provide a single source of truth for all psychometric questions.

### Table Structure
- **32 questions total**: 28 VESPA questions + 3 outcome questions + 1 vision grades question
- **Categories**: VISION, EFFORT, SYSTEMS, PRACTICE, ATTITUDE, NA_OUTCOME
- **Fields**: question_id, question_text, vespa_category, field mappings for cycles 1-3

### Setup Process
1. Run `create_questions_table.sql` in Supabase
2. Temporarily disable RLS: `ALTER TABLE questions DISABLE ROW LEVEL SECURITY;`
3. Run `python load_questions_to_supabase.py`
4. Re-enable RLS with read policy

### New API Endpoint
```
GET /api/questions
GET /api/questions?category=VISION
GET /api/questions?active=true
```

### Benefits
- Complete relational model (questions ↔ question_responses ↔ question_statistics)
- Dynamic question loading for frontend
- Single source of truth instead of JSON files
- Better JOIN capabilities for analysis

## Success Metrics

✅ All VESPA distributions are 10 elements
✅ School statistics calculate correctly
✅ National statistics aggregate properly
✅ No duplicate Object_29 records
✅ Super users can access all establishments
✅ Trust relationships work correctly
✅ Questions table provides complete question metadata
✅ All question_responses properly link to questions table

The system is production-ready with standardized VESPA scoring (1-10) across all elements!