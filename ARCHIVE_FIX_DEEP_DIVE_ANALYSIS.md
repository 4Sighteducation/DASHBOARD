# Archive Fix - Deep Dive Analysis
**Date:** October 19, 2025  
**Status:** Pre-Implementation Assessment

---

## 🎯 Executive Summary

The dashboard has been experiencing critical failures since the academic year transition (2024-2025 → 2025-2026). This document provides a comprehensive analysis of the situation and outlines a clear path to resolution.

### Critical Issues Identified
1. **Daily sync failing** - Current sync process unable to handle academic year transitions
2. **Historical data corruption** - Archive data (2024-2025) is incomplete/inaccurate
3. **Piecemeal fixes** - Multiple attempts to patch issues have created conflicts
4. **Missing graduated students** - Year 13 students deleted in Knack not in archive

### The Solution
Use the August 2025 Knack snapshot as the **definitive source of truth** for 2024-2025 archive data, then repair the sync process for 2025-2026 current data.

---

## 📊 Data Snapshot Analysis

### Files Provided (August 2025 Historical Snapshot)

#### 1. **FullObject_6_2025.csv** - Student Accounts
- **Total Records:** 23,458 students
- **Key Fields Identified:**
  - `id`: Knack user account ID
  - `created`: Account creation timestamp
  - `updated`: Last update timestamp
  - `field_90_*`: Name components (first, last, full)
  - `field_186`: Student code/ID
  - `field_91_email`: Email address
  - `field_193`: Connection to establishment (record ID format)
  - `field_548`: Year group
  - `field_565`: Class/group
  - `field_832`: Language (e.g., "English")
  - `field_1358`: Gender
  
- **Data Quality:**
  - Contains created dates from 2022-2025
  - Many records from 2024-09 onwards (September 2024 = start of 2024-2025 academic year)
  - Some records updated as late as 2025-05 (May 2025 = end of 2024-2025)

- **Key Insight:** This is Object_6 (Student Accounts), NOT Object_10 (VESPA Results)
  - Object_6 = User accounts in Knack
  - Object_10 = VESPA results records (what we actually need)
  - **PROBLEM:** We need Object_10 data, not Object_6 data!

#### 2. **FullObject_10_2025.csv** - VESPA Results
- **Total Records:** 2,529,559 lines (2.5M records!)
- **Key Fields Identified:**
  - `id`: VESPA result record ID
  - `field_187_*`: Student name (full name connection)
  - `field_197_email`: Student email (KEY LINKING FIELD)
  - `field_137`: Student identifier
  - `field_143`: Gender
  - `field_568`: Level (Level 2/3)
  - `field_223`: Group/class
  - `field_144`: Year group
  - `field_782`: Faculty/course
  - `field_146`: Current cycle (1, 2, or 3)
  - `field_147-152`: **Current VESPA scores** (V, E, S, P, A, Overall)
  - `field_155-160`: **Cycle 1 VESPA scores**
  - `field_161-166`: **Cycle 2 VESPA scores**
  - `field_167-172`: **Cycle 3 VESPA scores**
  - `field_855_date`: Completion date
  - `field_833`: Language
  - `field_2299`: Course field

- **Data Insights:**
  - Oldest record: 2022-01-27 (Poppy OFFSIDE example)
  - Contains historical cycles data
  - Each student can have multiple records (one per cycle or year)
  - **This is the PRIMARY data source we need**

#### 3. **FullObject_29_2025.csv** - Question Responses
- **Total Records:** 41,029 responses
- **Key Fields:**
  - `id`: Response record ID
  - `field_794-821`: Individual question responses (28 questions)
  - `field_857-863`: Summary scores (appear to be cycle scores)
  - `field_1823_*`: Student name
  - `field_1824`: Some identifier
  - `field_1825`: Subject/course
  - `field_1826`: Cycle number
  - `field_1827`: Level
  - `field_1828`: Active status
  - `field_2732_email`: Student email
  - Many fields for individual question responses

- **Data Insights:**
  - Question-level granular data
  - Links to students via email
  - Contains cycle information

---

## 🗄️ Current Database Architecture

### Existing Tables (from schema analysis)

1. **trusts** - Academy trust information
2. **establishments** - Schools/colleges
3. **staff_admins** - Staff user accounts
4. **students** - Student master records
   - Has `academic_year` field (added recently)
   - Has `email`, `name`, `establishment_id`, `year_group`, `course`
   
5. **vespa_scores** - VESPA assessment results
   - Link to students via `student_id`
   - Has `cycle` (1, 2, 3)
   - Has VESPA components: `vision`, `effort`, `systems`, `practice`, `attitude`, `overall`
   - Has `completion_date`
   - Has `academic_year` field
   - **UNIQUE constraint:** `(student_id, cycle, academic_year)` OR `(student_id, cycle)` depending on migration state

6. **question_responses** - Individual question-level responses
   - Links to students
   - Has cycle information

7. **school_statistics** - Pre-calculated school stats
8. **question_statistics** - Question-level stats
9. **national_statistics** - National benchmarks

### Current Sync Scripts Identified

1. `sync_knack_to_supabase.py` - Main comprehensive sync script
2. `sync_knack_to_supabase_backend.py` - Heroku backend optimized version
3. `sync_knack_to_supabase_optimized.py` - Optimized version with checkpoints
4. `sync_knack_to_supabase_production.py` - Production version
5. Multiple `sync_object120_*` scripts - Specific object syncs

**ISSUE:** Too many sync scripts, unclear which is "current"

---

## 🚨 Root Cause Analysis

### Problem 1: Academic Year Transition Logic
**What's happening:**
- New academic year started (September 2025 → 2025/2026)
- Sync script calculates academic year based on **current date**, not **data date**
- All synced data gets tagged as `2025/2026` even if it's historical
- Historical 2024/2025 data being overwritten

**Code Evidence:**
```python
# In sync_knack_to_supabase.py line ~434
academic_year = calculate_academic_year(
    completion_date_raw,
    establishment_id,
    is_australian=False
)
```

**The calculate_academic_year function:**
- Uses August 1st cutoff
- If month >= 8: returns current_year/next_year
- Currently returns `2025/2026` for any date after August 2025
- **But** the historical data has completion dates from 2024-2025!

### Problem 2: Student Record Duplication Strategy
**Two workflows observed:**
1. **Delete & Re-upload** (Large schools): Same email, different Knack ID each year
2. **Update in place** (Small schools): Same Knack ID, update year group

**Current sync doesn't handle either well:**
- No enrollment history tracking
- No detection of which workflow is being used
- Overwrites previous year data

### Problem 3: Historical Data Loss
**Missing:**
- Graduated Year 13 students from 2024-2025 (deleted from Knack)
- Complete VESPA cycle data from last year
- Accurate completion dates

**Why:**
- Schools delete students at year-end
- No archive process before deletion
- Sync only captures "current" Knack data

### Problem 4: Field Mapping Confusion
**Discovered:**
- Object_6 ≠ Object_10
- Object_6 = Student user accounts
- Object_10 = VESPA results records
- Current sync may be mixing these up

---

## 📋 Current Database State Assessment

### What Needs Investigation
1. **How many students currently in database for each year?**
   - 2024/2025 count
   - 2025/2026 count
   - By establishment

2. **How many VESPA scores for each year?**
   - By cycle
   - By academic year
   - Completion date distribution

3. **Are there duplicate student records?**
   - Same email, multiple IDs
   - Different academic years

4. **What's the constraint situation?**
   ```sql
   -- Need to check if using:
   UNIQUE(student_id, cycle, academic_year)
   -- OR
   UNIQUE(student_id, cycle)
   ```

---

## 🎯 Proposed Solution Architecture

### Phase 1: Archive Creation (Historical Data Import)
**Objective:** Create definitive 2024-2025 archive from August snapshot

#### Step 1.1: Pre-Import Audit
- Query current database state
- Count students/scores per academic year
- Identify what will be affected
- **BACKUP current database state**

#### Step 1.2: Field Mapping Creation
Create comprehensive field mapping document:
```
Knack Object_10 → Supabase Tables
- field_197_email → students.email
- field_187_full → students.name
- field_144 → students.year_group
- field_855_date → vespa_scores.completion_date
- field_146 → vespa_scores.cycle (currentMCycle)
- field_147-152 → Current cycle scores
- field_155-160 → Cycle 1 scores
- field_161-166 → Cycle 2 scores
- field_167-172 → Cycle 3 scores
```

#### Step 1.3: Archive Import Strategy
**Option A: Separate Archive Tables**
```sql
CREATE TABLE students_archive (
    -- Same structure as students
    -- Plus archived_year field
    academic_year TEXT DEFAULT '2024/2025'
);

CREATE TABLE vespa_scores_archive (
    -- Same structure as vespa_scores
    academic_year TEXT DEFAULT '2024/2025'
);
```

**Option B: Single Tables with Archive Flag**
```sql
ALTER TABLE students ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
ALTER TABLE vespa_scores ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
```

**Recommendation:** Option B (simpler queries, single source of truth)

#### Step 1.4: Import Process
```python
def import_historical_snapshot():
    """
    Import August 2025 snapshot as 2024/2025 archive
    """
    # Read Object_10 CSV
    df = pd.read_csv('FullObject_10_2025.csv')
    
    for record in df.itertuples():
        # Parse completion date
        completion_date = parse_date(record.field_855_date)
        
        # Calculate ACTUAL academic year from completion date
        if completion_date:
            academic_year = calculate_academic_year_from_date(completion_date)
        else:
            academic_year = '2024/2025'  # Default for August snapshot
        
        # ONLY import if academic_year is 2024/2025 or earlier
        if academic_year <= '2024/2025':
            # Create/update student record
            student_id = upsert_student(
                email=record.field_197_email,
                name=record.field_187_full,
                academic_year=academic_year,
                is_archived=True
            )
            
            # Create VESPA scores for all cycles present
            import_vespa_cycles(student_id, record, academic_year)
```

### Phase 2: Sync Process Repair
**Objective:** Fix daily sync to handle 2025-2026 data correctly

#### Step 2.1: Academic Year Logic Fix
```python
def calculate_academic_year_from_completion_date(completion_date_str):
    """
    Calculate academic year from ACTUAL completion date, not current date
    """
    if not completion_date_str:
        return None
    
    completion_date = parse_date(completion_date_str)
    
    # UK academic year: August 1st cutoff
    if completion_date.month >= 8:
        return f"{completion_date.year}/{completion_date.year + 1}"
    else:
        return f"{completion_date.year - 1}/{completion_date.year}"
```

#### Step 2.2: Dual-Workflow Support
```python
def sync_student(knack_record):
    """
    Support both delete-reupload and update-in-place workflows
    """
    email = extract_email(knack_record)
    knack_id = knack_record['id']
    
    # Find existing student(s) by email
    existing = find_students_by_email(email)
    
    if existing:
        # Determine workflow
        same_knack_id = any(s['knack_id'] == knack_id for s in existing)
        
        if same_knack_id:
            # WORKFLOW B: Update in place
            update_student(knack_id, knack_record)
        else:
            # WORKFLOW A: New year, new record
            # Check if this is current academic year
            current_year = get_current_academic_year()
            existing_current = [s for s in existing if s['academic_year'] == current_year]
            
            if not existing_current:
                # Create new student record for current year
                create_student(knack_record, academic_year=current_year)
            else:
                # Update existing current year record
                update_student(existing_current[0]['id'], knack_record)
    else:
        # New student
        create_student(knack_record, academic_year=get_current_academic_year())
```

#### Step 2.3: Archive Protection
```python
def sync_vespa_scores(student_id, knack_record):
    """
    Sync VESPA scores WITHOUT overwriting archive data
    """
    completion_date = knack_record.get('field_855_date')
    
    if completion_date:
        academic_year = calculate_academic_year_from_completion_date(completion_date)
    else:
        academic_year = get_current_academic_year()
    
    # CRITICAL: Do not overwrite archived data
    if academic_year <= '2024/2025':
        # Check if this is already archived
        existing = check_archived_score(student_id, cycle, academic_year)
        if existing and existing['is_archived']:
            logger.info(f"Skipping archived score for {student_id}")
            return
    
    # Proceed with upsert for current year data
    upsert_vespa_score(student_id, cycle, scores, academic_year)
```

### Phase 3: Data Validation
**Objective:** Ensure data integrity after import and sync repair

#### Validation Checks
1. **Student Count Validation**
   ```sql
   SELECT academic_year, COUNT(*) as student_count
   FROM students
   GROUP BY academic_year
   ORDER BY academic_year DESC;
   ```

2. **VESPA Score Validation**
   ```sql
   SELECT 
       academic_year,
       cycle,
       COUNT(*) as score_count,
       COUNT(DISTINCT student_id) as unique_students
   FROM vespa_scores
   GROUP BY academic_year, cycle
   ORDER BY academic_year DESC, cycle;
   ```

3. **Duplicate Detection**
   ```sql
   SELECT email, academic_year, COUNT(*)
   FROM students
   GROUP BY email, academic_year
   HAVING COUNT(*) > 1;
   ```

4. **Archive Integrity**
   ```sql
   -- Ensure archived data has is_archived = TRUE
   SELECT COUNT(*)
   FROM students
   WHERE academic_year = '2024/2025'
   AND is_archived = FALSE;
   ```

---

## ⚠️ Critical Decisions Needed

### Decision 1: What to do with current database data?

**Option A: Clean Slate for 2024/2025**
- Delete all 2024/2025 data
- Import fresh from snapshot
- **Pros:** Clean, no conflicts
- **Cons:** Lose any post-August updates

**Option B: Merge Strategy**
- Keep existing 2024/2025 data
- Merge with snapshot
- Prefer snapshot data for conflicts
- **Pros:** Preserves post-August data
- **Cons:** Complex merge logic

**Recommendation:** Option A for 2024/2025, but **preserve any 2025/2026 data**

### Decision 2: Archive Table Strategy?

**Option A:** Separate archive tables
**Option B:** Single tables with `is_archived` flag
**Option C:** Use `academic_year` field only, no special archive handling

**Recommendation:** Option B (single tables + archive flag)

### Decision 3: Which Sync Script is "Current"?

Need to identify ONE sync script as the canonical version:
- `sync_knack_to_supabase.py` appears most comprehensive
- Has ~1900 lines, includes statistics calculation
- Should consolidate others or clearly mark as deprecated

---

## 📅 Implementation Plan

### Pre-Implementation (Day 0)
- [x] Deep dive analysis (this document)
- [ ] Review and approve plan
- [ ] Identify which sync script is current
- [ ] Database backup
- [ ] Audit current database state

### Phase 1: Historical Archive Import (Days 1-2)
- [ ] Create field mapping documentation
- [ ] Write import script for Object_10
- [ ] Test import on subset (100 records)
- [ ] Run full import for 2024/2025 data
- [ ] Validate import (student counts, VESPA scores)
- [ ] Import Object_29 question responses
- [ ] Calculate statistics for 2024/2025

### Phase 2: Sync Repair (Days 3-4)
- [ ] Fix calculate_academic_year function
- [ ] Implement archive protection logic
- [ ] Add dual-workflow support
- [ ] Test sync with sample data
- [ ] Dry-run sync for current year
- [ ] Deploy sync fix
- [ ] Monitor first live sync

### Phase 3: Validation & Testing (Day 5)
- [ ] Run all validation queries
- [ ] Check dashboard displays correctly
- [ ] Verify 2024/2025 archive intact
- [ ] Verify 2025/2026 current data accurate
- [ ] Test academic year switching in UI
- [ ] Load testing

### Phase 4: Documentation & Cleanup (Day 6)
- [ ] Update README with new architecture
- [ ] Document field mappings
- [ ] Archive/delete old sync scripts
- [ ] Create runbook for future year transitions
- [ ] Train on new process

---

## 🔍 Immediate Next Steps

### 1. Database Audit Query
Run this to understand current state:
```sql
-- Student distribution by year
SELECT 
    academic_year,
    COUNT(*) as total_students,
    COUNT(DISTINCT email) as unique_emails
FROM students
GROUP BY academic_year;

-- VESPA scores by year and cycle
SELECT 
    academic_year,
    cycle,
    COUNT(*) as score_count
FROM vespa_scores
GROUP BY academic_year, cycle
ORDER BY academic_year, cycle;

-- Check for completion dates in vespa_scores
SELECT 
    MIN(completion_date) as earliest,
    MAX(completion_date) as latest,
    COUNT(*) as total_with_dates,
    COUNT(CASE WHEN completion_date IS NULL THEN 1 END) as null_dates
FROM vespa_scores;
```

### 2. Sample CSV Analysis
Extract and analyze sample records:
```python
# Get first 1000 records from Object_10
df = pd.read_csv('FullObject_10_2025.csv', nrows=1000)

# Analyze completion dates
print(df['field_855_date'].value_counts())

# Check academic year distribution
df['calculated_year'] = df['field_855_date'].apply(calculate_academic_year)
print(df['calculated_year'].value_counts())
```

### 3. Field Mapping Verification
Create test mapping for critical fields:
```python
# Test record from CSV
sample_record = {
    'id': '61f2c2a3339b33001efda404',
    'field_197_email': '18offsidep@caerleoncomprehensive.net',
    'field_187_full': 'Poppy OFFSIDE',
    'field_146': '1',  # Current cycle
    'field_147': '5',  # Vision
    'field_148': '6',  # Effort
    # ...
}

# Map to Supabase structure
supabase_student = map_to_student(sample_record)
supabase_vespa = map_to_vespa_scores(sample_record)
```

---

## 🚦 Risk Assessment

### High Risk
1. **Data Loss:** Overwriting archive data during import
   - **Mitigation:** Backup before import, dry-run testing
   
2. **Duplicate Creation:** Creating duplicate students
   - **Mitigation:** Proper upsert logic, email-based deduplication

### Medium Risk
3. **Sync Failure:** New sync breaking after repair
   - **Mitigation:** Extensive testing, rollback plan
   
4. **Performance:** Large import affecting database performance
   - **Mitigation:** Batch processing, off-peak execution

### Low Risk
5. **UI Display Issues:** Dashboard not showing correct data
   - **Mitigation:** Frontend testing, gradual rollout

---

## 📊 Success Metrics

### Quantitative
- 2024/2025 student count matches expected (~15,000-20,000?)
- 2025/2026 student count accurate
- Zero duplicate students per academic year
- All VESPA cycles represented for archive data
- Sync completes within 30 minutes
- Zero errors in sync logs

### Qualitative
- Dashboard displays correct historical data
- Users can switch between academic years
- National benchmarks show for all years
- No data loss reported
- Sync runs successfully daily

---

## 🤔 Open Questions

1. **Expected student counts:** What's the expected total for 2024/2025? For 2025/2026?
2. **Establishment mapping:** Do we have establishment IDs mapped correctly?
3. **Object_6 usage:** Do we need Object_6 data at all, or just Object_10?
4. **Question responses:** Should we import Object_29 or recalculate from Object_10?
5. **National statistics:** Do we need to recalculate for 2024/2025 archive?
6. **Current sync schedule:** How often does sync run? (Daily? Heroku Scheduler?)

---

## 📝 Conclusion

This is a **complex but solvable problem**. The key is:
1. Use the August snapshot as source of truth for 2024/2025
2. Fix the sync to properly handle academic year transitions
3. Protect archive data from future sync overwriting
4. Establish clear processes for future year transitions

**Recommendation:** Proceed with phased approach, starting with detailed database audit and field mapping verification before any imports.

**Estimated Timeline:** 5-6 days for complete resolution

**Next Action:** Run database audit queries and review findings before proceeding with implementation.

---

*This analysis document should be reviewed and approved before any code changes are made.*


