# Final Action Plan - Dashboard Fix
**Date:** October 28, 2025  
**Status:** Analysis complete, ready for implementation

---

## ✅ **What We've Accomplished Today**

1. ✅ Deep dive analysis complete
2. ✅ Database audit showing 999 students (missing ~20K)
3. ✅ CSV analysis revealing missing connection fields
4. ✅ Architecture mapping (2 Heroku jobs identified)
5. ✅ Database constraints fixed for multi-year support
6. ✅ **Decision made: Focus on current year going forward, not archive**
7. ✅ All work committed to GitHub

---

## 🎯 **The Real Solution (No CSV Import!)**

**KEY INSIGHT:** CSV exports are incomplete (missing field_133 and other connection fields)

**Therefore:**
- ❌ **Don't use CSV import**
- ✅ **Fix the existing Knack API sync** (`sync_knack_to_supabase.py`)

---

## 🏗️ **Current Architecture**

### **Heroku Job 1:** `calculate_national_averages.py` (12:00 AM UTC)
**Purpose:** Calculate national averages for current academic year

**What it does:**
- ✅ Uses **completion date filtering** (field_855, field_856) ← **CORRECT!**
- ✅ Calculates averages from Knack API
- ✅ Updates Object_120 in Knack
- ✅ Syncs to Supabase national_statistics

**Status:** Script looks good, needs verification

---

### **Heroku Job 2:** `sync_with_sendgrid_report.py` (2:00 AM UTC)
**Purpose:** Sync all Knack data to Supabase

**What it runs:** `sync_knack_to_supabase.py` (1,898 lines)

**What needs fixing:**
- ❌ Uses current date instead of completion date
- ❌ No email-based multi-year student handling
- ❌ Creates duplicates or loses students

---

## 🔧 **What Needs to Be Fixed**

### **Fix 1: `sync_knack_to_supabase.py`** (Priority: HIGH)

**Current problems:**
```python
# Line ~434: Wrong!
academic_year = calculate_academic_year(
    completion_date_raw,  # Often NULL!
    establishment_id,
    is_australian=False
)

# If completion_date is NULL, uses TODAY
# → Everything becomes 2025/2026
# → Historical data corrupted
```

**What it should be:**
```python
# Use completion date FIRST, fall back to created date
completion_date = record.get('field_855')
created_date = record.get('created')

if completion_date and is_valid_date(completion_date):
    academic_year = calculate_year_from_date(completion_date)
elif created_date:
    academic_year = calculate_year_from_date(created_date)
else:
    academic_year = get_current_academic_year()
```

---

### **Fix 2: Email-Based Student Matching**

**Current:** Likely uses record ID matching → creates duplicates

**Should be:**
```python
# Find student by EMAIL + ACADEMIC YEAR
student = find_or_create_student(
    email=student_email,
    academic_year=academic_year,  # From completion date!
    knack_id=record['id']  # May change year-to-year
)

# This handles BOTH workflows automatically:
# - Keep & refresh: Same email, same knack_id, different year
# - Delete & re-upload: Same email, different knack_id, different year
```

---

### **Fix 3: Academic Year Format Standardization**

**Current mess:**
- `calculate_national_averages.py`: Uses `2024-2025` (hyphen)
- `sync_knack_to_supabase.py`: Uses `2024/2025` (slash)
- Database has both formats!

**Solution:** Standardize on `2024/2025` (slash) everywhere

---

## 📋 **Immediate Actions**

### **Action 1: Check Heroku Logs**

**Can you check:**
1. Is `calculate_national_averages.py` running successfully?
2. Are there errors in the logs?
3. Is Object_120 being updated in Knack?

**How to check:**
- Go to Heroku dashboard
- More → View Logs
- Or run: `heroku logs --app vespa-dashboard --tail`

**Look for:**
- "National average calculation task completed successfully"
- Any errors or warnings
- Record counts being processed

---

### **Action 2: Verify Object_120 in Knack**

**Check if it exists:**
- Log into Knack
- Go to Data → Object_120
- Look for record: "National VESPA Averages by Cycle 2025-2026"
- Check if date field shows recent update

---

### **Action 3: Let Me Fix the Main Sync**

Once we know the status of Job 1, I'll:
1. Create FIXED version of `sync_knack_to_supabase.py`
2. Test it locally with your .env
3. Deploy to Heroku
4. Monitor first run

---

## 🎯 **Expected Outcomes**

### **After Fixes:**

**For Students:**
- ✅ Email is primary identifier
- ✅ Multiple academic year records per email
- ✅ Works with both workflows automatically
- ✅ No duplicates within same year

**For VESPA Scores:**
- ✅ Linked by completion date to academic year
- ✅ Same student can have Cycle 1 in 2024/2025 AND 2025/2026
- ✅ Historical data protected

**For Question Responses:**
- ✅ Linked to correct academic year via completion date
- ✅ Same student can answer questions across multiple years
- ✅ 13K skip issue resolved

**For Dashboard:**
- ✅ Switch between academic years correctly
- ✅ Accurate student counts per year
- ✅ Proper statistics calculations
- ✅ National benchmarks showing

---

## 📊 **Timeline**

**Today:**
- ✅ Analysis complete
- ✅ Constraints fixed
- ✅ Architecture mapped

**Tomorrow:**
- Check Heroku logs (you)
- Fix sync script (me)
- Test locally (me)

**Day 3:**
- Deploy to Heroku
- Monitor first sync
- Verify results

**Day 4:**
- Clean up old scripts
- Document final architecture
- Create runbook for future

---

## 💬 **What You Need to Do**

### **Right Now:**
1. **Check Heroku logs** for `calculate_national_averages.py`
2. **Check Object_120** in Knack - is it being updated?
3. **Share findings** with me

### **Then:**
- I'll fix `sync_knack_to_supabase.py`
- We'll test it together
- Deploy when ready

---

## 🎉 **Bottom Line**

**Good News:**
- ✅ We understand the problem completely
- ✅ Solution is clear and achievable
- ✅ Constraints are fixed
- ✅ Architecture is solid

**What's Left:**
- Fix completion date logic in main sync
- Add email-based matching
- Verify national averages job
- Clean up old scripts

**Timeline:** 2-3 days to complete properly

---

## 📝 **Next Message**

Please share:
1. Heroku log output (last 100 lines or so)
2. Whether Object_120 exists in Knack and when it was last updated
3. Any errors you see

Then I'll create the fixed sync script! 🚀

---

*All analysis and investigation work has been committed to GitHub*

