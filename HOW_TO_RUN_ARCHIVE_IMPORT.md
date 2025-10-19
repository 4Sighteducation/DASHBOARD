# How to Run Archive Import for 2024-2025

## 📋 **What This Does**

Imports aggregate statistics from your August 2025 snapshot into the database as the **2024-2025 archive baseline**.

- ✅ Calculates school statistics (per establishment, per cycle)
- ✅ Calculates national statistics (per cycle)
- ✅ Stores with `academic_year = '2024/2025'`
- ✅ Does NOT import individual students (not needed)
- ✅ Safe to run (uses upsert - won't create duplicates)

---

## 🚀 **Before You Run**

### **1. Verify CSV Paths**

Check that these files exist:
```
C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv
```

### **2. Check Environment Variables**

Make sure your `.env` file has:
```
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

### **3. Estimated Time**

- Loading data: 2-3 minutes
- Calculating statistics: 5-10 minutes
- Importing: 1-2 minutes
- **Total: ~10-15 minutes**

---

## ▶️ **How to Run**

### **Step 1: Open Terminal**
```bash
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"
```

### **Step 2: Run the Script**
```bash
python import_archive_statistics_2024_2025.py
```

### **Step 3: Watch the Output**

You'll see:
```
========================================
  LOADING DATA
========================================

✅ Loaded 2,529,559 total records from Object_10
✅ Filtered to 20,023 records from 2024-2025

========================================
  LOADING ESTABLISHMENT MAPPING
========================================

✅ Loaded 124 establishments from database

========================================
  CALCULATING ESTABLISHMENT STATISTICS
========================================

📊 Processing: Whitchurch High School
   Records: 450
   ✅ Cycle 1: 6 elements calculated
   ✅ Cycle 2: 6 elements calculated
   ✅ Cycle 3: 6 elements calculated

... (continues for all schools)
```

---

## ✅ **Verification**

After it completes, you'll see:
```
📊 ARCHIVE IMPORT SUMMARY
========================
Academic Year: 2024/2025
Duration: 0:12:34

School Statistics:
  Calculated: 2,160
  Imported: 2,160
  Errors: 0

National Statistics:
  Calculated: 18
  Imported: 18
  Errors: 0

✅ Archive statistics for 2024-2025 are now preserved in the database.
```

---

## 🔍 **Check Results in Supabase**

### **Query 1: School Statistics**
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
ORDER BY e.name, ss.cycle, ss.element
LIMIT 20;
```

### **Query 2: National Statistics**
```sql
SELECT 
    cycle,
    element,
    mean,
    count
FROM national_statistics
WHERE academic_year = '2024/2025'
ORDER BY cycle, element;
```

---

## ⚠️ **If Something Goes Wrong**

### **"File not found" Error**
- Check the CSV path in the script
- Make sure FullObject_10_2025.csv exists

### **"Supabase connection failed"**
- Check your `.env` file
- Verify SUPABASE_URL and SUPABASE_KEY

### **"Establishment not found"**
- Some establishments in CSV might not be in database
- Script will skip them and continue
- Check the log file: `archive_import_2024_2025.log`

### **Need to Re-run**
- Safe to run multiple times
- Uses `upsert` so won't create duplicates
- Will update existing 2024/2025 statistics

---

## 📊 **Expected Results**

Based on your data:
- **~124 establishments** in database
- **~80-100 establishments** will have 2024-2025 data (some may have joined later)
- **Each establishment** should have:
  - Up to 6 elements (vision, effort, systems, practice, attitude, overall)
  - For 1-3 cycles (depending on when they joined)
  - = ~18 statistics records per school with all 3 cycles
- **Total school statistics**: 1,500-2,500 records
- **Total national statistics**: 18 records (6 elements × 3 cycles)

---

## 🎯 **After Import Complete**

### **1. Check Dashboard**
- Go to your dashboard
- Switch to academic year "2024/2025"
- Verify you see:
  - Student counts (aggregate)
  - VESPA averages
  - Cycle comparisons
  - National benchmarks

### **2. What You Should See**
For 2024-2025:
- Realistic average scores (5-7 range)
- Reasonable student counts per school
- National benchmarks showing

### **3. Next Steps**
Once archive is confirmed working:
- ✅ Archive is protected
- ✅ Can focus on optimizing current sync
- ✅ No rush - archive is safe now!

---

## 📝 **Log File**

All output is saved to: `archive_import_2024_2025.log`

Check this if you need details about:
- Which establishments were processed
- How many records per school
- Any warnings or errors

---

## 🆘 **Need Help?**

If the import fails or results look wrong:
1. Check the log file
2. Run the verification queries above
3. Share the log file output

The script is designed to be **safe** - it won't delete existing data, only adds/updates 2024-2025 statistics.

---

**Ready to run!** Just execute:
```bash
python import_archive_statistics_2024_2025.py
```

