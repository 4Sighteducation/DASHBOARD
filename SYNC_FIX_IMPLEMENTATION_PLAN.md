# Sync Fix Implementation Plan
**Date:** October 28, 2025  
**File to Fix:** sync_knack_to_supabase.py

---

## 🎯 **Summary of Fixes Needed**

### **5 Critical Issues Identified:**

1. **Students upsert** - Wrong constraint (2 locations)
2. **Question responses** - Missing academic_year field
3. **Question responses upsert** - Wrong constraint (2 locations)
4. **Fallback logic** - Should use 'created' date before current date
5. **Type conversion** - Ensure integers where needed

---

## 🔧 **Detailed Fix Instructions**

### **FIX #1: Students Table Upsert Constraint**

**Location:** Lines 473 and 626

**Current Code:**
```python
result = supabase.table('students').upsert(
    student_batch,
    on_conflict='email'  # ❌ WRONG
).execute()
```

**Fixed Code:**
```python
result = supabase.table('students').upsert(
    student_batch,
    on_conflict='email,academic_year'  # ✅ CORRECT
).execute()
```

**Why:** Database constraint is `UNIQUE(email, academic_year)` - must match!

---

### **FIX #2: Improve Fallback for NULL Completion Dates**

**Location:** Lines 432-445

**Current Code:**
```python
completion_date_raw = record.get('field_855')
if completion_date_raw and completion_date_raw.strip():
    academic_year = calculate_academic_year(completion_date_raw, ...)
else:
    # ❌ Falls back to TODAY
    academic_year = calculate_academic_year(
        datetime.now().strftime('%d/%m/%Y'), ...
    )
```

**Fixed Code:**
```python
completion_date_raw = record.get('field_855')
created_date_raw = record.get('created')  # Get Knack created date

# Priority: 1) completion_date, 2) created date, 3) current date
if completion_date_raw and completion_date_raw.strip():
    academic_year = calculate_academic_year(completion_date_raw, ...)
elif created_date_raw:
    # Use created date (ISO format from Knack)
    academic_year = calculate_academic_year(created_date_raw, ...)
else:
    # Last resort: current date
    academic_year = calculate_academic_year(
        datetime.now().strftime('%d/%m/%Y'), ...
    )
```

**Why:** Most records have NULL field_855, but 'created' date exists for all records

---

### **FIX #3: Question Responses - Add Academic Year Field**

**Location:** Lines 682-856 (sync_question_responses function)

**Need to add academic_year calculation at start of record processing:**

**After line 748 (start of record loop), add:**
```python
for record in records:
    try:
        # ✅ ADD THIS: Calculate academic year from field_856
        completion_date_raw = record.get('field_856')
        created_date_raw = record.get('created')
        
        if completion_date_raw and str(completion_date_raw).strip():
            academic_year = calculate_academic_year(completion_date_raw, None, False)
        elif created_date_raw:
            academic_year = calculate_academic_year(created_date_raw, None, False)
        else:
            academic_year = calculate_academic_year(
                datetime.now().strftime('%d/%m/%Y'), None, False
            )
        
        # Rest of existing code...
        if record['id'] in processed_object29_ids:
            ...
```

**Then in response_data dictionary (line 796-801), add academic_year:**
```python
response_data = {
    'student_id': student_id,
    'cycle': cycle,
    'academic_year': academic_year,  # ✅ ADD THIS
    'question_id': q_detail['questionId'],
    'response_value': int_value
}
```

---

### **FIX #4: Question Responses Upsert Constraint**

**Location:** Lines 826 and 853

**Current Code:**
```python
supabase.table('question_responses').upsert(
    deduped_batch,
    on_conflict='student_id,cycle,question_id'  # ❌ MISSING academic_year
).execute()
```

**Fixed Code:**
```python
supabase.table('question_responses').upsert(
    deduped_batch,
    on_conflict='student_id,cycle,academic_year,question_id'  # ✅ ADD academic_year
).execute()
```

---

### **FIX #5: Ensure Proper Type Conversion**

**Location:** Lines 520-539 (score extraction)

**Current code tries to clean scores - verify it's working:**
```python
def clean_score(value):
    if value is None or value == '':
        return None
    try:
        # Convert to float first, then to int for 1-10 scores
        float_val = float(value)
        # Ensure it's in valid range
        if 1 <= float_val <= 10:
            return int(round(float_val))  # ✅ Convert to INTEGER
        return None
    except (ValueError, TypeError):
        return None
```

**Status:** Need to verify this function exists and is being used

---

## 📋 **Implementation Checklist**

### **Phase 1: Create Fixed Version**
- [ ] Create `sync_knack_to_supabase_FIXED.py`
- [ ] Apply Fix #1 (students upsert)
- [ ] Apply Fix #2 (fallback logic)
- [ ] Apply Fix #3 (question responses academic_year)
- [ ] Apply Fix #4 (question responses upsert)
- [ ] Apply Fix #5 (type conversion)
- [ ] Add better logging
- [ ] Add dry-run mode for testing

### **Phase 2: Test Locally**
- [ ] Run with dry-run flag
- [ ] Verify no constraint errors
- [ ] Check academic year assignments
- [ ] Validate student deduplication
- [ ] Ensure no data loss

### **Phase 3: Deploy**
- [ ] Backup current sync script
- [ ] Replace with fixed version
- [ ] Update sync_with_sendgrid_report.py if needed
- [ ] Push to GitHub
- [ ] Deploy to Heroku
- [ ] Monitor first scheduled run

---

## ⏱️ **Estimated Timeline**

- **Creating fixes:** 2-3 hours
- **Testing locally:** 1-2 hours
- **Deployment & verification:** 1 hour
- **Total:** Half day to full day

---

## 🚀 **Ready to Create the Fixed Version?**

I'll create a new file: `sync_knack_to_supabase_FIXED.py` with all corrections applied.

This way:
- ✅ Keep original as backup
- ✅ Test the fixed version
- ✅ Can easily compare
- ✅ Rollback if needed

**Shall I proceed?**

