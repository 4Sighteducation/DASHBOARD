# VESPA Dashboard Sync Status and Next Steps Plan

## Current Status Overview

### ✅ What's Working
1. **Basic data sync is partially functional:**
   - ✅ Establishments (schools) - synced
   - ✅ Students - synced
   - ✅ VESPA scores (Object_10) - synced
   - ✅ Question responses (Object_29) - synced

### ❌ What's Not Working
1. **Missing Data:**
   - ❌ Staff admins (Object_5) - empty
   - ❌ Super users (Object_21) - empty
   - ❌ School statistics - empty
   - ❌ Question statistics - empty
   - ❌ National statistics - empty

2. **Missing Database Components:**
   - Missing `group` column in students table
   - Missing `calculate_all_statistics()` stored procedure
   - Views (`current_school_averages`) return no data because statistics tables are empty

3. **Sync Script Issues:**
   - Main `sync_knack_to_supabase.py` doesn't call staff/super user sync functions
   - Statistics calculation is failing because stored procedure doesn't exist
   - Academic year format mismatch (`2024/2025` vs `2024-25`)

## Root Cause Analysis

1. **Incomplete Database Setup:**
   - The `add_group_column.sql` script exists but hasn't been run
   - The `create_statistics_function_fixed.sql` exists but hasn't been deployed to Supabase

2. **Code Mismatch:**
   - `sync_knack_to_supabase.py` (main) is missing functions that exist in `sync_knack_to_supabase_optimized.py`
   - `quick_sync_questions_and_stats.py` imports from the optimized version, not the main script

3. **Statistics Calculation:**
   - The sync tries to call `calculate_all_statistics()` via RPC, but this function doesn't exist in Supabase
   - Fallback manual calculation has bugs (uses 'average' instead of 'mean')

## Next Steps Plan

### Phase 1: Fix Database Schema (Immediate)

1. **Run missing SQL scripts in Supabase SQL Editor:**
   ```sql
   -- 1. Add group column
   ALTER TABLE students 
   ADD COLUMN IF NOT EXISTS "group" VARCHAR(100);
   
   -- 2. Create statistics function (from create_statistics_function_fixed.sql)
   -- Copy entire content of create_statistics_function_fixed.sql
   
   -- 3. Add unique constraint for question_responses (from add_unique_constraint_question_responses.sql)
   -- Copy entire content of add_unique_constraint_question_responses.sql
   ```

2. **Verify all tables and functions exist:**
   ```sql
   -- Check if function exists
   SELECT proname FROM pg_proc WHERE proname = 'calculate_all_statistics';
   
   -- Check if group column exists
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'students' AND column_name = 'group';
   ```

### Phase 2: Update Sync Script (Today)

✅ **Already Completed!**
   - Added `sync_staff_admins()` function to main script
   - Added `sync_super_users()` function to main script
   - Updated main() to call both functions
   - Fixed calculate_statistics() to handle missing stored procedure



### Phase 3: Run Complete Sync (After Phase 1 & 2)

1. **Clear existing partial data:**
   ```bash
   python
   >>> from sync_knack_to_supabase import supabase
   >>> # Clear sync logs to start fresh
   >>> supabase.table('sync_logs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
   ```

2. **Run full sync:**
   ```bash
   python sync_knack_to_supabase.py
   ```

### Phase 4: Calculate National Statistics (After Phase 3)

✅ **Script Created!** Run the national statistics calculator:
```bash
python calculate_national_stats_supabase.py
```

This script will:
- Calculate weighted national averages from all school statistics
- Generate percentiles and distributions
- Store results in the national_statistics table

### Phase 5: Verify Data Integrity

1. **Check all tables have data:**
   ```sql
   SELECT 'establishments' as table_name, COUNT(*) as count FROM establishments
   UNION ALL
   SELECT 'students', COUNT(*) FROM students
   UNION ALL
   SELECT 'vespa_scores', COUNT(*) FROM vespa_scores
   UNION ALL
   SELECT 'question_responses', COUNT(*) FROM question_responses
   UNION ALL
   SELECT 'staff_admins', COUNT(*) FROM staff_admins
   UNION ALL
   SELECT 'super_users', COUNT(*) FROM super_users
   UNION ALL
   SELECT 'school_statistics', COUNT(*) FROM school_statistics
   UNION ALL
   SELECT 'question_statistics', COUNT(*) FROM question_statistics
   UNION ALL
   SELECT 'national_statistics', COUNT(*) FROM national_statistics;
   ```

2. **Test views are working:**
   ```sql
   -- Should return data after statistics are calculated
   SELECT * FROM current_school_averages LIMIT 10;
   ```

### Phase 6: Update Flask Backend (Next Week)

1. **Update API endpoints to use Supabase instead of Knack**
2. **Test all dashboard functionality**
3. **Deploy to Heroku**

## Quick Fix Commands

Run these commands in order to get everything working:

```bash
# 1. First, run the SQL scripts in Supabase
# Go to Supabase SQL Editor and run:
# - add_super_users_table.sql
# - add_group_column.sql
# - create_statistics_function_fixed.sql
# - add_unique_constraint_question_responses.sql

# 2. Run the complete sync (sync script already updated!)
python sync_knack_to_supabase.py

# 3. Calculate national statistics
python calculate_national_stats_supabase.py

# 4. Verify data
python check_sync_status.py
```

## Expected Timeline

- **Today**: Fix database schema and update sync scripts (2-3 hours)
- **Tomorrow**: Run full sync and verify data (4-6 hours for large schools)
- **This Week**: Calculate national statistics and test everything
- **Next Week**: Update Flask backend to use Supabase

## Success Criteria

1. All tables have appropriate data
2. Statistics are calculated for all schools/cycles/elements
3. Views return data correctly
4. No errors in sync logs
5. Dashboard loads data successfully from Supabase

## Monitoring

After sync completion, monitor:
1. `sync_logs` table for any errors
2. Row counts in all tables
3. Statistics calculation completeness
4. API endpoint response times

## Contact for Issues

If you encounter any issues:
1. Check sync logs first: `SELECT * FROM sync_logs ORDER BY started_at DESC`
2. Review error messages in `sync_knack_to_supabase.log`
3. Verify all environment variables are set correctly