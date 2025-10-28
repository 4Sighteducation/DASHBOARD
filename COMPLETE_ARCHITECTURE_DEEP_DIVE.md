# Complete Architecture Deep Dive
**Date:** October 28, 2025  
**Purpose:** Understand current state and create fix plan

---

## 🏗️ **Current Heroku Architecture**

### **Two Scheduled Jobs Running Daily:**

#### **Job 1: National Averages Calculator** (12:00 AM UTC)
```bash
python calculate_national_averages.py
```

**Location:** `heroku_backend/calculate_national_averages.py`

**What it does:**
1. ✅ Fetches Object_10 (VESPA) from Knack - **FILTERED BY COMPLETION DATE** (field_855)
2. ✅ Fetches Object_29 (Questions) from Knack - **FILTERED BY COMPLETION DATE** (field_856)
3. ✅ Calculates national averages for current academic year
4. ✅ Updates/creates record in Knack **Object_120** (National Averages Data)
5. ✅ Syncs to Supabase `national_statistics` table

**Academic Year Format:** `2024-2025` (hyphen)

**Date Filtering Logic:**
```python
# For current academic year 2025-2026:
filter_start_date = 2025-08-01 (minus 1 day = 2025-07-31)
filter_end_date = 2026-07-31 (plus 1 day = 2026-08-01)

# Filters: field_855 > 2025-07-31 AND field_855 < 2026-08-01
```

**THIS SCRIPT IS ACTUALLY CORRECT!** ✅

---

#### **Job 2: Main Sync to Supabase** (2:00 AM UTC)
```bash
python sync_with_sendgrid_report.py
```

**What it does:**
1. Runs `sync_knack_to_supabase.py`
2. Sends email report via SendGrid

**Which then runs:** `sync_knack_to_supabase.py` (1,898 lines!)

**What sync_knack_to_supabase.py does:**
1. Syncs establishments from Object_2
2. Syncs students + VESPA scores from Object_10
3. Syncs question responses from Object_29
4. Syncs staff_admins from Object_5
5. Syncs super_users from Object_21
6. Calculates school statistics
7. Calculates national statistics
8. Updates academic year in question responses
9. Calculates national ERI

**Academic Year Format:** `2024/2025` (slash)

---

## ⚠️ **The Problem with Academic Year Format**

**Two different formats in use:**
- `calculate_national_averages.py`: Uses `2024-2025` (hyphen)
- `sync_knack_to_supabase.py`: Uses `2024/2025` (slash)

**Supabase national_statistics table:**
- Some records have `2024-25` (hyphen, short year)
- Some have `2024/2025` (slash, full year)
- This causes mismatches!

---

## 🔍 **Root Cause Analysis**

### **Why Daily Sync Has Issues:**

#### **1. Academic Year Calculation Problem**
In `sync_knack_to_supabase.py` around line 434:
```python
academic_year = calculate_academic_year(
    completion_date_raw,
    establishment_id,
    is_australian=False
)
```

**The `calculate_academic_year` function** (line 912):
- Uses current date if no completion_date provided
- Returns format: `2024/2025` (slash)

**Problem:**
- If completion_date is NULL → uses TODAY's date
- Everything gets tagged as current year (2025/2026)
- Historical data gets wrong academic year

#### **2. Email-Based Linking Not Implemented**
Current sync likely:
- Uses Knack record ID as primary key
- Doesn't handle workflow transitions (keep & refresh vs delete & re-upload)
- Creates duplicates or loses students

#### **3. No Establishment Field in CSV**
- CSV exports don't include connection fields (like field_133)
- Can't import from CSV without establishment linkage
- **Must sync from Knack API, not CSV!**

---

## 💡 **The Real Solution**

**Forget the CSV approach!** The CSV exports are incomplete (missing connection fields).

**Instead: Fix the existing sync scripts that use Knack API!**

### **What Needs Fixing:**

#### **Fix 1: sync_knack_to_supabase.py**
- ✅ Use completion date to determine academic year
- ✅ Handle NULL completion dates (use created date)
- ✅ Email-based student matching
- ✅ Don't overwrite if completion date indicates different year

#### **Fix 2: Standardize Academic Year Format**
- Choose ONE format: `2024/2025` (slash) ← Recommend this
- Update calculate_national_averages.py to use slash
- Ensure consistency across all scripts

#### **Fix 3: Multi-Year Support**
- ✅ Constraints already fixed (email + academic_year)
- ✅ Allow same student across years
- ✅ Use completion date to separate years

---

## 🎯 **Revised Strategy**

### **Phase 1: Fix sync_knack_to_supabase.py** (The Main Sync)
**Priority:** HIGH - This is what runs daily and affects current data

**Changes needed:**
1. Fix academic year calculation to use completion dates
2. Add email-based student deduplication
3. Handle both workflows automatically
4. Don't create duplicates within same year
5. Protect historical data from overwrites

---

### **Phase 2: Verify calculate_national_averages.py**
**Priority:** MEDIUM - Check why it's not updating

**Investigation needed:**
1. Check Heroku logs - is it running?
2. Check if it's finding any records (date filter might be too strict)
3. Verify Object_120 record exists in Knack
4. Check JSON mapping files are deployed to Heroku

---

### **Phase 3: Clean Up Old Scripts**
**Priority:** LOW - After main sync works

**Action:**
- Archive 20+ old sync scripts
- Document which is "current"
- Remove deprecated code

---

## 📋 **Immediate Next Steps**

### **Step 1: Check Heroku Logs**

Can you check Heroku logs for `calculate_national_averages.py`?

```bash
heroku logs --app vespa-dashboard --ps scheduler --tail
```

Or in Heroku dashboard: More → View Logs

**Look for:**
- Is it running successfully?
- Any errors?
- How many records is it processing?

---

### **Step 2: Abandon CSV Import Approach**

**Decision:** Don't import from CSV (missing connection fields)

**Instead:** Fix the Knack API sync scripts

---

### **Step 3: Create Comprehensive Sync Fix**

I'll create a FIXED version of `sync_knack_to_supabase.py` that:
- Uses completion dates properly
- Handles email-based multi-year students
- Works with both workflows
- Doesn't corrupt historical data

---

## ❓ **Questions for You**

1. **Can you check Heroku logs?** See if calculate_national_averages.py shows any errors?

2. **In Knack Object_120**, do you see the "National VESPA Averages by Cycle 2025-2026" record?

3. **Academic year format preference:** Slash (2024/2025) or hyphen (2024-2025)?

4. **Do you want me to:**
   - A) Fix sync_knack_to_supabase.py first (main sync)
   - B) Investigate calculate_national_averages.py first (national averages)
   - C) Both in parallel?

---

## 📝 **My Recommendation**

**Priority Order:**
1. ✅ Check Heroku logs for both jobs
2. ✅ Fix `sync_knack_to_supabase.py` (the main sync) - completion date logic
3. ✅ Verify `calculate_national_averages.py` is working (might already be fine!)
4. ✅ Test everything works together
5. ✅ Clean up old scripts

**Timeline:** 1-2 days to fix and test properly

---

**Ready to dive into fixing the sync script?** Let me know what you want to tackle first! 🚀

