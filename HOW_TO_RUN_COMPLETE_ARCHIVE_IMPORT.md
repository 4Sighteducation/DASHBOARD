# How to Run COMPLETE Archive Import

## 🎯 **What This Script Does**

This is the **full solution** that imports:
1. ✅ **~20,000 students** from Object_10 (2024-2025)
2. ✅ **All VESPA scores** for all cycles (1, 2, 3)
3. ✅ **School statistics** for each establishment
4. ✅ **National statistics** for benchmarks

**This fixes the missing 20,000+ students problem!**

---

## ⏱️ **Estimated Runtime**

- Loading data: 3-5 minutes
- Importing students: 10-15 minutes
- Importing VESPA scores: 10-15 minutes
- Calculating statistics: 5-10 minutes
- **Total: 30-45 minutes**

---

## 🚀 **How to Run**

### **Step 1: Make Sure CSV Exists**
```
C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv
```

### **Step 2: Check Environment**
Make sure `.env` has:
```
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

### **Step 3: Run the Script**
```bash
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"

python import_archive_COMPLETE_2024_2025.py
```

---

## 📊 **What You'll See**

```
╔══════════════════════════════════════════════════════════════════╗
║            COMPLETE ARCHIVE IMPORT: 2024-2025                    ║
║               Students + Scores + Statistics                     ║
╚══════════════════════════════════════════════════════════════════╝

================================================================================
  LOADING ESTABLISHMENTS
================================================================================
✅ Loaded 124 establishments

================================================================================
  LOADING OBJECT_10 DATA
================================================================================
  Loaded 50,000 rows...
  Loaded 100,000 rows...
  ...
✅ Total records: 2,529,559
✅ Filtered to 20,023 records from 2024-2025

================================================================================
  IMPORTING STUDENTS
================================================================================
  Imported 1000 students...
  Imported 2000 students...
  ...
✅ Students Import Complete:
   New: 18,234
   Updated: 1,234
   Skipped: 555
   Errors: 0

================================================================================
  IMPORTING VESPA SCORES
================================================================================
  Imported 5000 VESPA scores...
  Imported 10000 VESPA scores...
  ...
✅ VESPA Scores Import Complete:
   Imported: 45,678
   Skipped: 123
   Errors: 0

================================================================================
  CALCULATING STATISTICS
================================================================================
  Loaded 10,000 scores...
  Loaded 20,000 scores...
  ...
✅ Loaded 45,678 VESPA scores
✅ Imported 2,160 school statistics
✅ Imported 18 national statistics

================================================================================
  VERIFICATION
================================================================================
✅ Students for 2024/2025: 18,234
✅ VESPA scores for 2024/2025: 45,678
✅ School statistics: 2,160
✅ National statistics: 18

================================================================================
  IMPORT COMPLETE
================================================================================

📊 COMPLETE IMPORT SUMMARY
=========================
Academic Year: 2024/2025
Duration: 0:32:15

Students:
  New: 18,234
  Updated: 1,234
  Skipped: 555
  Errors: 0

VESPA Scores:
  Imported: 45,678
  Skipped: 123
  Errors: 0

Statistics:
  School: 2,160
  National: 18

✅ Archive for 2024-2025 is now complete!

This should fix:
  ✅ Missing ~20,000 students issue
  ✅ 13K question responses can now sync
  ✅ Historical statistics preserved
  ✅ Dashboard will show correct data
```

---

## ✅ **After Import - Verification**

### **1. Check Supabase Directly**

**Query: Total students for 2024-2025**
```sql
SELECT COUNT(*) 
FROM students 
WHERE academic_year = '2024/2025';
```
Expected: ~18,000-20,000

**Query: VESPA scores for 2024-2025**
```sql
SELECT cycle, COUNT(*) 
FROM vespa_scores 
WHERE academic_year = '2024/2025'
GROUP BY cycle
ORDER BY cycle;
```

**Query: Sample statistics**
```sql
SELECT 
    e.name,
    ss.cycle,
    ss.element,
    ss.mean,
    ss.count
FROM school_statistics ss
JOIN establishments e ON e.id = ss.establishment_id
WHERE ss.academic_year = '2024/2025'
LIMIT 20;
```

### **2. Check Dashboard**
- Switch to "2024/2025" academic year
- Should see realistic student counts
- VESPA averages should make sense (5-7 range)
- National benchmarks should appear

### **3. Run Diagnostic Again**
```bash
python diagnose_missing_students.py
```

Should now show:
- ✅ Most emails from Object_29 found in Supabase
- ✅ Dramatically fewer skipped responses

---

## 🔍 **What Gets Imported**

### **Students Table**
For each 2024-2025 student:
- Email (lowercase, trimmed)
- Name
- Establishment
- Knack ID
- Academic year = '2024/2025'
- Year group, course, faculty

### **VESPA Scores Table**
For each student, all cycles with data:
- Cycle 1 scores (if present)
- Cycle 2 scores (if present)  
- Cycle 3 scores (if present)
- V, E, S, P, A, Overall scores
- Academic year = '2024/2025'

### **Statistics Tables**
- School statistics: Per establishment × cycle × element
- National statistics: Per cycle × element
- All marked as 2024/2025

---

## ⚠️ **Important Notes**

### **Safe to Re-run**
- Uses `upsert` with conflict resolution
- Won't create duplicates
- Will update existing records
- Safe to run multiple times

### **Email-Based Matching**
- Links students by EMAIL (not Knack ID)
- Handles both workflows automatically:
  - Keep & refresh: Same email, updates data
  - Delete & re-upload: Same email, new Knack ID

### **Academic Year Assignment**
- All imported data tagged as '2024/2025'
- Based on `created` date (Sept 2024 - Aug 2025)
- Protected from future syncs

---

## 🆘 **Troubleshooting**

### **"Out of Memory" Error**
- Script processes in chunks
- Should work on most systems
- If fails, contact me for optimization

### **"Establishment not found"**
- Some Knack establishments might not be in Supabase
- These records will be skipped (logged)
- Check the log file for details

### **"Constraint violation"**
- Might need to update database constraint first
- Run this SQL first if error occurs:
```sql
-- Drop old constraint
ALTER TABLE vespa_scores 
DROP CONSTRAINT IF EXISTS vespa_scores_student_id_cycle_key;

-- Add new constraint
ALTER TABLE vespa_scores 
ADD CONSTRAINT vespa_scores_student_id_cycle_academic_year_key 
UNIQUE (student_id, cycle, academic_year);
```

### **Import Taking Too Long**
- 30-45 mins is normal
- Script shows progress every 1,000 records
- Check log file: `archive_import_COMPLETE_2024_2025.log`

---

## 🎯 **Expected Results**

Based on diagnostic:
- **Students**: 18,000-20,000 (from filtered 20,023 records)
- **VESPA Scores**: 40,000-50,000 (students × cycles)
- **School Statistics**: ~2,000 (establishments × cycles × elements)
- **National Statistics**: 18 (6 elements × 3 cycles)

---

## 📝 **Next Steps After Import**

1. ✅ Verify dashboard shows 2024-2025 data
2. ✅ Check that question responses sync properly now
3. ✅ Monitor daily sync - should have fewer skips
4. ✅ Archive is protected and complete

---

## 🚀 **Ready to Run!**

```bash
python import_archive_COMPLETE_2024_2025.py
```

**Grab a coffee ☕ - this will take 30-45 minutes!**

All progress is logged to: `archive_import_COMPLETE_2024_2025.log`

