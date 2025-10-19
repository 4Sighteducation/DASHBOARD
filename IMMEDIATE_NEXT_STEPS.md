# Immediate Next Steps - Archive Fix Project
**Created:** October 19, 2025  
**Status:** Ready for execution pending your approval

---

## 📋 What Has Been Done

### 1. Deep Dive Analysis Completed ✅
- **File:** `ARCHIVE_FIX_DEEP_DIVE_ANALYSIS.md`
- Comprehensive analysis of the situation
- Root cause identification
- Proposed solution architecture
- Implementation plan outlined

### 2. Audit Scripts Created ✅
- **File:** `audit_current_database_state.py`
- Will analyze current database before any changes
- Checks students, VESPA scores, statistics
- Tests constraints and table structures
- Exports audit report to JSON

### 3. CSV Analysis Script Created ✅
- **File:** `analyze_csv_snapshot.py`
- Will analyze the 3 CSV files in detail
- Identifies key fields and mappings
- Calculates academic year distributions
- Creates field mapping documentation

---

## 🎯 Critical Findings from Analysis

### Issue 1: Wrong Data File?
- **Object_6** = Student user accounts (23,458 records)
- **Object_10** = VESPA results records (2.5M records) ← **THIS IS WHAT WE NEED**
- You mentioned "Object_6 (student data)" but we actually need Object_10 for VESPA import
- ✅ Good news: You have Object_10 file!

### Issue 2: Academic Year Transition Bug
- Current sync calculates academic year from **current date**, not **data date**
- All historical data gets tagged as 2025/2026
- Need to use **completion_date** field to calculate correct academic year

### Issue 3: Multiple Sync Scripts
- Found 5+ different sync scripts in codebase
- Need to identify which is "current"
- Recommend consolidating to ONE authoritative sync script

### Issue 4: No Archive Protection
- Current sync overwrites historical data
- Need `is_archived` flag to protect 2024/2025 data
- Need academic year-aware sync logic

---

## 🚀 Immediate Actions Required (Before Any Code)

### Action 1: Run Database Audit
```bash
python audit_current_database_state.py
```

**This will:**
- Show current student counts by academic year
- Show VESPA score distribution
- Check what constraints are in use
- Export current state to JSON backup
- **Takes ~5-10 minutes**

**Why:** We need to know what's in the database NOW before making changes

---

### Action 2: Run CSV Analysis
```bash
python analyze_csv_snapshot.py
```

**This will:**
- Analyze all 3 CSV files in detail
- Show academic year distribution in the data
- Identify key fields for import
- Create field mapping documentation
- **Takes ~2-5 minutes**

**Why:** We need to understand the snapshot data structure before importing

---

### Action 3: Review Analysis Results

**Look for:**
1. How many students are currently in database for 2024/2025?
2. How many students are currently in database for 2025/2026?
3. What's the completion date range in Object_10 CSV?
4. Does the CSV data actually span 2024-2025?
5. Are there any obvious data quality issues?

---

## ❓ Questions to Answer

### Q1: What are the expected numbers?
- How many students SHOULD be in 2024/2025 archive?
- How many students SHOULD be in 2025/2026 current?
- This helps us validate the import

### Q2: Which sync script is "current"?
Looking at your codebase, I found:
- `sync_knack_to_supabase.py` (1,898 lines - most comprehensive)
- `sync_knack_to_supabase_backend.py` (661 lines - Heroku optimized)
- `sync_knack_to_supabase_production.py`
- `sync_knack_to_supabase_optimized.py`

**Which one is actually running daily?**

### Q3: How is the sync scheduled?
- Heroku Scheduler?
- Cron job?
- Manual execution?
- What time does it run?

### Q4: Do you have database backup access?
- Can you backup Supabase before we start?
- Do you have Point-in-Time Recovery enabled?

---

## 🎯 Proposed Execution Plan (After Analysis)

### Phase 1: Preparation (Day 1)
1. ✅ Run audit script
2. ✅ Run CSV analysis script
3. ✅ Review results
4. ✅ Backup database
5. ✅ Answer questions above

### Phase 2: Archive Import (Day 2)
1. Create import script based on field mappings
2. Test import on 100 records
3. Validate test results
4. Run full import of 2024/2025 data
5. Validate import (student counts, VESPA scores)
6. Recalculate statistics for 2024/2025

### Phase 3: Sync Repair (Day 3)
1. Identify current sync script
2. Fix academic year calculation
3. Add archive protection logic
4. Test sync on current data
5. Deploy fixed sync
6. Monitor first live run

### Phase 4: Validation (Day 4)
1. Check dashboard displays correctly
2. Verify 2024/2025 archive intact
3. Verify 2025/2026 current data accurate
4. Test academic year switching
5. Validate statistics

### Phase 5: Cleanup (Day 5)
1. Document changes
2. Archive old sync scripts
3. Create runbook for future year transitions
4. Update deployment documentation

---

## ⚠️ Critical Warnings

### WARNING 1: Data Loss Risk
- Any import CAN overwrite existing data
- **MUST backup database first**
- **MUST test on small subset first**

### WARNING 2: Sync Interruption
- Fixing sync means changing production code
- **MUST test thoroughly before deploying**
- **MUST have rollback plan**

### WARNING 3: Academic Year Calculation
- Wrong calculation = wrong academic year assignment
- **MUST validate with known data points**
- Example: Completion date 2024-09-15 should = 2024/2025

---

## 📊 Success Criteria

**After import and sync repair:**
1. ✅ 2024/2025 shows correct student count
2. ✅ 2025/2026 shows correct student count
3. ✅ All 2024/2025 VESPA scores present
4. ✅ Historical data has `is_archived = true`
5. ✅ Sync runs daily without errors
6. ✅ Dashboard switches between years correctly
7. ✅ National benchmarks show for all years

---

## 🎬 What to Do RIGHT NOW

### Step 1: Review the Analysis Document
**File:** `ARCHIVE_FIX_DEEP_DIVE_ANALYSIS.md`
- Read through the entire analysis
- Verify my understanding is correct
- Note any corrections needed

### Step 2: Run the Audit Scripts
```bash
# Audit current database
python audit_current_database_state.py > database_audit_output.txt

# Analyze CSV files
python analyze_csv_snapshot.py > csv_analysis_output.txt
```

### Step 3: Review Outputs
- Look at the generated files
- Check if numbers make sense
- Identify any red flags

### Step 4: Answer the Questions
From "Questions to Answer" section above

### Step 5: Confirm or Adjust Plan
Based on audit results, we may need to adjust the plan

---

## 📁 Files Created for You

### Documentation
1. `ARCHIVE_FIX_DEEP_DIVE_ANALYSIS.md` - Comprehensive analysis
2. `IMMEDIATE_NEXT_STEPS.md` - This file
3. `FIELD_MAPPING.json` - Will be created by CSV analysis script

### Scripts
1. `audit_current_database_state.py` - Database audit
2. `analyze_csv_snapshot.py` - CSV analysis

### Output Files (will be created)
1. `database_audit_YYYYMMDD_HHMMSS.json` - Audit data export
2. `database_audit_output.txt` - Human-readable audit report
3. `csv_analysis_output.txt` - CSV analysis report
4. `FIELD_MAPPING.json` - Field mapping documentation

---

## 💬 Communication

### What I Need From You
1. Run the two audit scripts
2. Share the output (or tell me key findings)
3. Answer the questions in "Questions to Answer" section
4. Confirm expected student counts
5. Approve or adjust the execution plan

### What I'll Do Next
Once you provide the above:
1. Create the import script with exact field mappings
2. Create the sync repair script
3. Create test validation scripts
4. Provide step-by-step execution instructions
5. Be ready to troubleshoot any issues

---

## 🔒 Safety First

**Before ANY code execution:**
- ✅ Full database backup
- ✅ Audit current state
- ✅ Test on small subset
- ✅ Have rollback plan
- ✅ Your approval

**I will NOT make any database changes without your explicit approval.**

---

## 📝 Summary

**Current Status:** Analysis complete, ready for execution
**Next Action:** You run the two audit scripts
**Timeline:** Can complete full fix in 4-5 days
**Risk Level:** Medium (mitigated by careful testing and backups)
**Confidence:** High (clear root causes identified)

**Ready to proceed when you are!**

---

*Generated: October 19, 2025*
*Last Updated: October 19, 2025*

