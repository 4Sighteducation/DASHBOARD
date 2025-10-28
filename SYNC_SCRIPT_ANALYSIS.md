# sync_knack_to_supabase.py - Complete Analysis
**File:** sync_knack_to_supabase.py (1,898 lines)  
**Purpose:** Main sync from Knack to Supabase  
**Runs:** Daily at 2:00 AM UTC via `sync_with_sendgrid_report.py`

---

## ✅ **What It Does Well**

### **1. Academic Year Calculation (Lines 912-959)**
```python
def calculate_academic_year(date_str, establishment_id=None, is_australian=None):
    # ✅ Correctly handles UK vs Australian schools
    # ✅ Uses August 1st cutoff for UK
    # ✅ Returns format: "2025/2026" (slash)
```
**Status:** ✅ **Function itself is CORRECT!**

---

### **2. Completion Date Usage (Lines 432-445)**
```python
# Line 432-438: TRIES to use completion date
completion_date_raw = record.get('field_855')
if completion_date_raw and completion_date_raw.strip():
    academic_year = calculate_academic_year(
        completion_date_raw,
        establishment_id,
        is_australian=False
    )
else:
    # Falls back to current date
    academic_year = calculate_academic_year(
        datetime.now().strftime('%d/%m/%Y'),
        establishment_id,
        is_australian=False
    )
```
**Status:** ⚠️ **Logic exists but has issues (see below)**

---

### **3. Email-Based Student Matching (Lines 346-362)**
```python
# Pre-fetches students and builds TWO maps:
student_id_map = {}      # knack_id -> student_id
student_email_map = {}   # email -> student_id ✅
```
**Status:** ✅ **Has email mapping!**

---

### **4. Field Mappings**
```python
# ✅ Uses correct fields:
field_197_raw = Student email
field_855 = Completion date (VESPA)
field_856 = Completion date (Questions)
field_792_raw = Object_10 connection (for Object_29)
```
**Status:** ✅ **Field mappings are CORRECT!**

---

## 🚨 **Critical Issues Found**

### **ISSUE #1: Wrong Students Upsert Constraint** ⚠️⚠️⚠️

**Lines 471-474 and 624-627:**
```python
supabase.table('students').upsert(
    student_batch,
    on_conflict='email'  # ❌ WRONG!
).execute()
```

**Problem:**
- Database constraint is: `UNIQUE(email, academic_year)`
- Script uses: `on_conflict='email'`
- **MISMATCH!**

**Impact:**
- Can't have same email across different years!
- Student from 2024/2025 blocks import of same email in 2025/2026
- **This is why 20,023 students were skipped!**

**Fix needed:**
```python
on_conflict='email,academic_year'  # ✅ Match the constraint
```

---

### **ISSUE #2: Wrong Question Responses Constraint** ⚠️⚠️⚠️

**Lines 824-827 and 851-854:**
```python
supabase.table('question_responses').upsert(
    deduped_batch,
    on_conflict='student_id,cycle,question_id'  # ❌ MISSING academic_year!
).execute()
```

**Problem:**
- Database constraint is: `UNIQUE(student_id, cycle, academic_year, question_id)`
- Script uses: `on_conflict='student_id,cycle,question_id'`
- **MISMATCH!**

**Impact:**
- Can't import same question response across different years
- Student who answered Q1/Cycle1 in 2024/2025 can't answer it in 2025/2026
- **This causes the 13K skipped responses!**

**Fix needed:**
```python
on_conflict='student_id,cycle,academic_year,question_id'  # ✅ Include academic_year
```

---

### **ISSUE #3: Fallback to Current Date** ⚠️

**Lines 440-445:**
```python
else:
    # No completion date, use current academic year
    academic_year = calculate_academic_year(
        datetime.now().strftime('%d/%m/%Y'),  # ❌ Uses TODAY
        establishment_id,
        is_australian=False
    )
```

**Problem:**
- 95% of records have NULL completion_date (per our CSV analysis)
- ALL of them get assigned current year (2025/2026)
- Historical data gets wrong academic year

**Better approach:**
```python
else:
    # Use 'created' date from Knack record
    created_date = record.get('created')
    if created_date:
        academic_year = calculate_academic_year(created_date, ...)
    else:
        # Only use current date as last resort
        academic_year = calculate_academic_year(datetime.now()..., ...)
```

---

### **ISSUE #4: Question Responses Missing Academic Year** ⚠️⚠️

**Lines 796-801:**
```python
response_data = {
    'student_id': student_id,
    'cycle': cycle,
    'question_id': q_detail['questionId'],
    'response_value': int_value
    # ❌ MISSING: 'academic_year'!
}
```

**Problem:**
- Question responses don't have academic_year assigned
- Can't differentiate between years
- Constraint will fail

**Fix needed:**
```python
response_data = {
    'student_id': student_id,
    'cycle': cycle,
    'academic_year': academic_year,  # ✅ Add this!
    'question_id': q_detail['questionId'],
    'response_value': int_value
}
```

**But where to get academic_year for Object_29?**
- Need to use field_856 (completion date for questions)
- OR inherit from the linked Object_10 record's academic_year

---

### **ISSUE #5: VESPA Scores - Float/Integer Mismatch** ⚠️

**Lines 520-539:** Scores are extracted as floats/strings but database expects integers for some fields

**From your earlier error:**
```
'invalid input syntax for type integer: "6.0"'
```

**The script does clean scores** but might not convert properly.

---

## 📊 **Summary of Issues**

| Issue | Severity | Lines | Impact |
|-------|----------|-------|--------|
| Students upsert constraint mismatch | 🔴 CRITICAL | 473, 626 | Can't have multi-year students |
| Question responses missing academic_year field | 🔴 CRITICAL | 796-801 | No year tracking |
| Question responses constraint mismatch | 🔴 CRITICAL | 826, 853 | Can't have multi-year responses |
| Fallback to current date | 🟡 MAJOR | 440-445 | Wrong year for NULL dates |
| Float/Integer conversion | 🟡 MAJOR | Various | Import failures |

---

## ✅ **What Works Well**

1. ✅ Has completion date logic (field_855, field_856)
2. ✅ calculate_academic_year function is correct
3. ✅ Email-based student mapping exists
4. ✅ Handles Object_10 → Object_29 linking via field_792
5. ✅ Batch processing for efficiency
6. ✅ Deduplication logic present

---

## 🔧 **Required Fixes**

### **Fix #1: Students Upsert** (2 locations)
**Lines 473 and 626:**
```python
# CHANGE FROM:
on_conflict='email'

# CHANGE TO:
on_conflict='email,academic_year'
```

---

### **Fix #2: Question Responses - Add Academic Year Field**

**Need to:**
1. Calculate academic_year for each Object_29 record (from field_856)
2. Add to response_data dictionary
3. Update upsert constraint

**Lines to modify:**
- ~750: Calculate academic year from Object_29
- ~796-801: Add academic_year to response_data
- ~826, 853: Update on_conflict

---

### **Fix #3: Improve Fallback Logic**

**Line 440-445:**
Use `created` date before falling back to current date:
```python
# 1st choice: completion_date (field_855)
# 2nd choice: created date
# 3rd choice: current date (last resort)
```

---

### **Fix #4: Score Type Conversion**

Ensure all scores are converted to proper types:
- Vision, Effort, Systems, Practice, Attitude: INTEGER
- Overall: DECIMAL/FLOAT

---

## 🎯 **Next Steps**

1. Create FIXED version of sync_knack_to_supabase.py
2. Test locally with dry-run mode
3. Verify no data corruption
4. Deploy to Heroku
5. Monitor first run

---

**Ready for me to create the fixed version?** 🚀

