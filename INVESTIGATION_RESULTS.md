# Deep Dive Investigation Results

**Date:** October 30, 2025  
**Schools Analyzed:** Ashlyns School, Coffs Harbour Christian Community School

---

## 📊 **ASHLYNS SCHOOL - Full Picture**

### Student Distribution
```
Total Students: 862
├── 2025/2026: 465 students
└── 2024/2025: 397 students
```

### VESPA Score Coverage
```
2025/2026:
├── Cycle 1: 465 students (100%)
├── Cycle 2: 465 students (100%)
└── Cycle 3: 465 students (100%)
Date Range: Sept 17, 2025 - Oct 27, 2025

2024/2025:
├── Cycle 1: 397 students (100%)
├── Cycle 2: 397 students (100%)
└── Cycle 3: 397 students (100%)
Date Range: Oct 18, 2024 - July 15, 2025
```

✅ **VESPA Coverage: PERFECT** - All students have all 3 cycles

### Question Response Coverage
```
2025/2026:
├── Cycle 1: 132 students (28% of 465) ❌
│   └── 4,128 responses (129 complete sets)
└── Cycle 2: 13 students (3% of 465) ❌
    └── 416 responses (13 complete sets)

2024/2025:
├── Cycle 1: 81 students (20% of 397) ❌
│   └── 2,544 responses (79 complete sets)
├── Cycle 2: 45 students (11% of 397) ❌
│   └── 1,392 responses (43 complete sets)
└── Cycle 3: 9 students (2% of 397) ❌
    └── 288 responses (9 complete sets)
```

### 🚨 **CRITICAL GAP IDENTIFIED**

**2025/2026, Cycle 1:**
- Students with VESPA scores: **465** ✓
- Students with Question Responses: **132** ❌
- **MISSING: 333 students (72% gap!)**

**Sample of Missing Students:**
```
22atkini@ashlyns.herts.sch.uk
21conmyj@ashlyns.herts.sch.uk
21robsoa@ashlyns.herts.sch.uk
22bunna@ashlyns.herts.sch.uk
tbenfield@ashlyns.herts.sch.uk
... and 328 more
```

---

## 📊 **COFFS HARBOUR - Full Picture**

### Student Distribution
```
Total Students: 178
├── 2025/2026: 79 students
└── 2024/2025: 99 students
```

### VESPA Score Coverage
```
2025/2026:
├── Cycle 1: 78 students (99% of 79) ✓
├── Cycle 2: 78 students (99% of 79) ✓
└── Cycle 3: 78 students (99% of 79) ✓

2024/2025:
├── Cycle 1: 99 students (100%) ✓
├── Cycle 2: 99 students (100%) ✓
└── Cycle 3: 99 students (100%) ✓
```

✅ **VESPA Coverage: EXCELLENT** - Nearly perfect coverage

### Question Response Coverage
```
2025/2026:
├── Cycle 1: 17 students (22% of 78) ❌
│   └── 520 responses (16 complete sets)
├── Cycle 2: NOT FOUND
└── Cycle 3: 7 students (9% of 78) ❌
    └── 224 responses (7 complete sets)

2024/2025:
├── Cycle 1: 24 students (24% of 99) ❌
│   └── 744 responses (23 complete sets)
├── Cycle 2: 15 students (15% of 99) ❌
│   └── 480 responses (15 complete sets)
└── Cycle 3: 1 student (1% of 99) ❌
    └── 32 responses (1 complete set)
```

### 🚨 **CRITICAL GAP IDENTIFIED**

**2025/2026, Cycle 1:**
- Students with VESPA scores: **78** ✓
- Students with Question Responses: **17** ❌
- **MISSING: 61 students (78% gap!)**

---

## 🔍 **KEY PATTERNS DISCOVERED**

### 1. **VESPA Scores Are Perfect** ✅
- Both schools: 99-100% VESPA coverage
- All cycles syncing correctly
- Academic years assigned correctly
- Date ranges appropriate

### 2. **Question Responses Have MASSIVE Gaps** ❌

| School | Year | Cycle | VESPA | Responses | Gap % |
|--------|------|-------|-------|-----------|-------|
| Ashlyns | 2025/2026 | 1 | 465 | 132 | **72%** |
| Ashlyns | 2025/2026 | 2 | 465 | 13 | **97%** |
| Ashlyns | 2024/2025 | 1 | 397 | 81 | **80%** |
| Coffs | 2025/2026 | 1 | 78 | 17 | **78%** |
| Coffs | 2024/2025 | 1 | 99 | 24 | **76%** |

**Average Gap: ~81% of students missing question responses**

### 3. **Pattern is Consistent**
- Happens in BOTH schools (UK and Australian)
- Happens in BOTH academic years
- Happens across ALL cycles
- Not school-specific, not year-specific → **SYSTEMIC SYNC ISSUE**

---

## ❓ **CRITICAL QUESTIONS**

### Q1: Do these students actually have Object_29 records in Knack?

**Need to verify:**
- Take 10 "missing" students from Ashlyns
- Check Knack Object_29 for their Object_10 IDs
- See if questionnaire responses exist but aren't being synced

**If YES:** Sync is broken (not fetching/linking correctly)  
**If NO:** Students simply haven't completed questionnaires

### Q2: Why is the sync skipping so many Object_29 records?

**Last sync report said:**
```
QUESTION_RESPONSES
  Skipped: 702
  Skip Rate: 81.4%
  Warning: "702 question responses skipped due to missing student links"
```

This matches our ~80% gap!

**Hypothesis:** 
- Object_29 records exist in Knack
- field_792 (link to Object_10) is failing
- Sync can't find student → skips the entire Object_29 record
- Result: 80% of responses never make it to database

### Q3: Is this a recent problem or historical?

**Evidence from 2024/2025:**
- Ashlyns Cycle 1: 81/397 students (80% missing)
- Coffs Cycle 1: 24/99 students (76% missing)

**Conclusion:** This has been happening for a LONG TIME (not just current year)

---

## 💡 **IMPLICATIONS FOR YOUR PROPOSED SOLUTION**

### Current-Year-Only Sync Won't Fix This

**Why:**
- Problem isn't about syncing old data
- Problem is that **current data isn't syncing**
- Only 20% of Object_29 records successfully link to students
- 80% fail the link check and get skipped

### What Needs to be Fixed FIRST

**Before implementing current-year-only sync:**

1. **Fix the Object_29 → Student link**
   - Understand why field_792 lookup fails for 80% of records
   - Possible causes:
     - Hard wipes create new knack_ids, breaking links
     - field_792 is blank/malformed in many records
     - Student doesn't exist yet when Object_29 syncs
     - Email-based fallback needed

2. **Test with a sample**
   - Pick 10 "missing" students
   - Manually check Knack for their Object_29 records
   - Verify field_792 values
   - Test if sync can find them

3. **Then implement current-year filtering**
   - Once link is working for 100% of valid records
   - Add date filters to only fetch current year
   - This becomes safe and fast

---

## 🎯 **RECOMMENDED NEXT STEPS**

### Step 1: Verify Knack Data (Manual Check)
Check 5-10 missing students in Knack:
```
Missing Student: 22atkini@ashlyns.herts.sch.uk
Knack ID (Object_10): 68c86d4a5160c20f6382...

Questions:
1. Does Object_29 record exist for this student?
2. What is field_792 value in that Object_29 record?
3. Does it match the Object_10 knack_id above?
4. If not, what does it point to?
```

### Step 2: Understand the Link Failure
Based on Knack check:
- If field_792 is blank → Need to handle missing links
- If field_792 points to old/wrong ID → Need email-based matching
- If Object_29 doesn't exist → Students haven't completed (expected)

### Step 3: Fix or Accept
- **If fixable:** Update sync logic to handle the link issue
- **If not fixable:** Accept that these students haven't completed questionnaires
- **Document** which case it is for clarity

### Step 4: Then Proceed with Current-Year Sync
- Only after understanding the gap
- With confidence that valid data won't be skipped

---

## 📋 **SQL Queries for Further Investigation**

All queries saved in: `investigate_question_responses.sql`

Run in Supabase SQL Editor to get more details.


