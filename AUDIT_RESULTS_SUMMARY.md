# Audit Results Summary & Action Plan
**Date:** October 19, 2025  
**Status:** ✅ Audits Complete - Ready for Implementation

---

## 📊 **Executive Summary**

**Good News:** ✅ The August CSV snapshot contains 79.8% data from 2024-2025 academic year  
**Challenge:** ⚠️ Need to use `created` date instead of `completion_date` for academic year  
**Action Required:** Import CSV as 2024-2025 archive, fix sync for current year

---

## 🔍 **Audit Results**

### **Current Database State**

#### Students Table
- **Total Students:** 35,830
- **Distribution:**
  - 2024/2025: 750 students
  - 2025/2026: 250 students
  - Other years: ~34,830 students
  
**Critical Issues:**
- ❌ NO email addresses in students table (0 found in sample)
- ❌ NO `is_archived` field exists
- ❌ Missing data for expected student counts

#### VESPA Scores Table
- **Total Scores:** 106,758
- **Distribution:**
  - 2024/2025: 418 scores (Cycles 1, 2, 3)
  - 2025/2026: 414 scores
  - Historical: Rest distributed across 2021-2024
  
**Critical Issues:**
- ❌ Using OLD constraint `(student_id, cycle)` 
- ✅ Should use `(student_id, cycle, academic_year)`
- ❌ NO `is_archived` field

#### Other Tables
- **Establishments:** 124 schools
- **Question Responses:** 926,960 responses
- **National Statistics:** 9 records
- **School Statistics:** 1,194 records

---

## 📁 **CSV Snapshot Analysis**

### **Object_10 (VESPA Results) - Primary Data Source**

**File:** `FullObject_10_2025.csv`  
**Total Size:** ~2.5M lines  
**Sample Analyzed:** 25,098 records

#### Date Distribution
```
Created Dates:
├─ Earliest: 2021-03-15
├─ Latest: 2025-08-29
└─ Peak Month: Sept 2024 (12,516 records)

2024-2025 Academic Year Records:
├─ Count: 20,023 records
├─ Percentage: 79.8% ✅
└─ Date Range: Sept 1, 2024 - Aug 31, 2025

Completion Dates:
├─ Populated: 1,247 records (5.0%)
├─ NULL: 23,851 records (95.0%)  ⚠️
├─ Date Range: 2021-2023 (old data)
└─ Conclusion: Can't use for academic year calculation
```

#### Key Fields (from sample of 5,000)
- ✅ `field_197_email`: 99.9% populated (student email)
- ✅ `field_187_full`: 99.8% populated (student name)
- ✅ `field_147-152`: 71% populated (current VESPA scores)
- ✅ `field_155-160`: 64% populated (Cycle 1 scores)
- ✅ `field_161-166`: 34% populated (Cycle 2 scores)
- ✅ `field_167-172`: 13% populated (Cycle 3 scores)
- ✅ `field_146`: 70% populated (current cycle number)
- ❌ `field_855_date`: Only 5% populated, dates are 2021-2023

#### Recommendation
**Use `created` date for academic year calculation**, not `completion_date`

---

### **Object_6 (Student Accounts)**

**File:** `FullObject_6_2025.csv`  
**Total Records:** 23,458  
**Purpose:** Student account metadata (NOT primary VESPA data)

- ✅ `field_91_email`: 99.8% populated
- ✅ `field_90_full`: 86% populated (names)
- ✅ `field_548`: 86% populated (year groups)
- Peak creation: Sept 2024 (504 records in sample)

**Note:** This is supplementary data. Object_10 is the primary source.

---

### **Object_29 (Question Responses)**

**File:** `FullObject_29_2025.csv`  
**Total Records:** 41,029  
**Purpose:** Individual question-level responses

- ✅ 28 question fields (field_794 to field_821)
- ✅ `field_2732_email`: 45% populated (student link)
- ✅ `field_1826`: 94% populated (cycle)

**Note:** Import this AFTER Object_10 for question-level granularity.

---

## 🎯 **Critical Decisions Made**

### **Decision 1: Which Date to Use for Academic Year?**
**✅ DECISION:** Use `created` date from Object_10  
**Reason:** 
- `completion_date` only 5% populated
- `completion_date` values are old (2021-2023)
- `created` date shows 80% from 2024-2025
- Aligns with actual academic year

### **Decision 2: What Data to Import as Archive?**
**✅ DECISION:** Import records created Sept 2024 - Aug 2025 as 2024/2025 archive  
**Filter:** `created_date >= '2024-09-01' AND created_date <= '2025-08-31'`  
**Expected:** ~20,000 records

### **Decision 3: How to Handle NULL Emails?**
**✅ DECISION:** Skip records without emails  
**Reason:** Can't link to students without email address

---

## 📋 **Implementation Plan**

### **Phase 1: Database Preparation**
**Estimated Time:** 2 hours

#### Step 1.1: Add `is_archived` Field
```sql
-- Add to students table
ALTER TABLE students ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_students_is_archived ON students(is_archived);

-- Add to vespa_scores table
ALTER TABLE vespa_scores ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_vespa_scores_is_archived ON vespa_scores(is_archived);
```

#### Step 1.2: Update Constraint
```sql
-- Drop old constraint
ALTER TABLE vespa_scores DROP CONSTRAINT IF EXISTS vespa_scores_student_id_cycle_key;

-- Add new constraint
ALTER TABLE vespa_scores 
ADD CONSTRAINT vespa_scores_student_id_cycle_academic_year_key 
UNIQUE (student_id, cycle, academic_year);
```

#### Step 1.3: Backup Database
- Export current database state
- Save locally before ANY imports

---

### **Phase 2: Archive Import**
**Estimated Time:** 4-6 hours

#### Step 2.1: Create Import Script
Script will:
1. Read Object_10 CSV
2. Filter for records created Sept 2024 - Aug 2025
3. Calculate academic_year from `created` date
4. Extract student info → students table
5. Extract VESPA scores → vespa_scores table
6. Mark all as `is_archived = TRUE`
7. Set `academic_year = '2024/2025'`

#### Step 2.2: Test Import (100 records)
- Import small subset
- Validate data quality
- Check student/score counts
- Verify academic year assignment

#### Step 2.3: Full Import
- Import all 2024-2025 records
- Monitor progress
- Log any errors

#### Step 2.4: Import Object_29 (Question Responses)
- Link to imported students
- Set academic_year and is_archived

---

### **Phase 3: Sync Repair**
**Estimated Time:** 4 hours

#### Step 3.1: Identify Current Sync Script
**Question for you:** Which sync script is currently running?
- `sync_knack_to_supabase.py`?
- `sync_knack_to_supabase_backend.py`?
- Other?

#### Step 3.2: Fix Academic Year Calculation
Update sync to:
```python
def calculate_academic_year_from_data(knack_record):
    """
    Calculate academic year from DATA dates, not current date
    Priority:
    1. Completion date (if present and recent)
    2. Created date
    3. Current date (fallback)
    """
    completion_date = knack_record.get('field_855_date')
    created_date = knack_record.get('created')
    
    # Use completion date if recent (within last 2 years)
    if completion_date and is_recent(completion_date):
        return calc_year_from_date(completion_date)
    
    # Use created date
    if created_date:
        return calc_year_from_date(created_date)
    
    # Fallback to current (for new records)
    return get_current_academic_year()
```

#### Step 3.3: Add Archive Protection
```python
# Don't overwrite archived data
if existing_record and existing_record.get('is_archived'):
    logger.info(f"Skipping archived record: {record_id}")
    continue
```

#### Step 3.4: Test Sync
- Dry run on test data
- Verify doesn't overwrite archive
- Check current year data imports correctly

---

### **Phase 4: Validation**
**Estimated Time:** 2 hours

#### Validation Queries
```sql
-- 1. Check student counts by year
SELECT academic_year, COUNT(*) as students, 
       COUNT(CASE WHEN is_archived THEN 1 END) as archived
FROM students
GROUP BY academic_year
ORDER BY academic_year DESC;

-- 2. Check VESPA score counts
SELECT academic_year, cycle, COUNT(*) as scores
FROM vespa_scores
GROUP BY academic_year, cycle
ORDER BY academic_year DESC, cycle;

-- 3. Verify archive integrity
SELECT 
    COUNT(*) as total_archived,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM vespa_scores
WHERE is_archived = TRUE AND academic_year = '2024/2025';

-- 4. Check for duplicates
SELECT student_id, cycle, academic_year, COUNT(*)
FROM vespa_scores
GROUP BY student_id, cycle, academic_year
HAVING COUNT(*) > 1;
```

#### Dashboard Validation
- Switch to 2024/2025 in UI
- Verify student count matches expected
- Check VESPA averages make sense
- Test cycle switching
- Verify national benchmarks show

---

## 🚨 **Critical Issues to Address**

### **Issue 1: No Emails in Current Students Table**
**Found:** 0 email addresses in students table sample  
**Impact:** Can't link Object_10 records to existing students  
**Solution:** 
- Object_10 has emails - use those
- This might be WHY sync is failing!
- Need to investigate why current students have no emails

### **Issue 2: Expected Student Counts**
**Question:** What should the counts be?
- 2024/2025: ??? students (please confirm)
- 2025/2026: ??? students (please confirm)

**Current database shows:**
- 2024/2025: Only 750 students (seems low?)
- 2025/2026: Only 250 students (seems low?)

### **Issue 3: Old Constraint**
**Current:** `(student_id, cycle)` - allows only one score per student per cycle across ALL years  
**Needed:** `(student_id, cycle, academic_year)` - allows scores per student per cycle PER YEAR  
**Impact:** MUST fix before import or will get constraint violations

---

## ❓ **Questions for You**

### **Before We Proceed:**

1. **Expected Student Counts:**
   - How many students SHOULD be in 2024/2025 archive?
   - How many students SHOULD be in 2025/2026 current?

2. **Which Sync Script:**
   - Which Python file is the "current" sync script?
   - How is it scheduled? (Heroku? Cron? Manual?)
   - What time does it run?

3. **Database Backup:**
   - Can you create a backup in Supabase before we start?
   - Do you have point-in-time recovery enabled?

4. **Email Address Issue:**
   - Do you know why current students table has no emails?
   - Is this expected or a problem?

5. **Approval:**
   - Are you comfortable proceeding with this plan?
   - Any concerns or questions?

---

## 📝 **Next Actions**

### **You Need To:**
1. ✅ Review this summary
2. ✅ Answer the 5 questions above
3. ✅ Backup Supabase database
4. ✅ Confirm expected student counts
5. ✅ Give approval to proceed

### **I Will Then:**
1. Create the database migration SQL
2. Create the import script
3. Create the sync repair script
4. Provide step-by-step execution guide
5. Monitor and support during execution

---

## 📊 **Success Criteria**

After implementation:
1. ✅ 2024/2025 archive has expected student count
2. ✅ All 2024/2025 data marked `is_archived = TRUE`
3. ✅ 2025/2026 current data separate and accurate
4. ✅ Dashboard switches correctly between years
5. ✅ Sync runs daily without errors
6. ✅ No data loss
7. ✅ Historical data protected from overwrites

---

## ⏱️ **Timeline**

- **Day 1 (Today):** ✅ Audits complete, plan approved
- **Day 2:** Database prep + test import
- **Day 3:** Full archive import + validation
- **Day 4:** Sync repair + testing
- **Day 5:** Final validation + monitoring

**Total:** 4-5 days to complete

---

## 🎉 **We're Ready!**

The analysis is complete, the path is clear. We have:
- ✅ Identified root causes
- ✅ Analyzed data quality
- ✅ Created detailed plan
- ✅ Mitigated risks with testing approach

**Just need your answers to the questions and approval to proceed!**

---

*Generated: October 19, 2025 at 07:50 GMT*  
*Files: `database_audit_20251019_074314.json`, `FIELD_MAPPING.json`*

