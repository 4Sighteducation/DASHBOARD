# Quick Start: CSV to Knack Import

## ⚡ TL;DR - I have a CSV with VESPA scores

1. **Format your CSV** with these columns:
   ```
   email,V1,E1,S1,P1,A1
   ```

2. **Run the importer**:
   ```bash
   python csv_to_knack_importer.py
   ```

3. **Import to Knack**: Upload the generated JSON files to Object_29

---

## Your Two Options

### Option 1: CSV Import (You have scores in a spreadsheet)

✅ **Best when:**
- You have VESPA scores in Excel/CSV
- You want to review data before importing
- You're importing many students at once

📝 **Steps:**
1. Export your spreadsheet to CSV
2. Make sure it has columns: `email`, `V1`, `E1`, `S1`, `P1`, `A1`
3. Run: `python csv_to_knack_importer.py`
4. Import the generated JSON files into Knack Object_29

📖 **Full guide**: See [CSV_IMPORT_GUIDE.md](CSV_IMPORT_GUIDE.md)

---

### Option 2: Direct from Knack (VESPA scores already in Object_10)

✅ **Best when:**
- VESPA scores are already in Knack Object_10
- You want automatic processing
- You're comfortable with scripts writing directly to Knack

📝 **Steps:**
1. Ensure `.env` file has `KNACK_APP_ID` and `KNACK_API_KEY`
2. Run: `python knack_vespa_automation.py`
3. Script reads Object_10 and writes to Object_29 automatically

⚠️ **Warning**: This writes directly to your Knack database. Use dry-run mode first!

---

## CSV Format Examples

### Minimal (Cycle 1 only)
```csv
email,V1,E1,S1,P1,A1
student@school.com,7,8,6,7,9
```

### With Cycle 2
```csv
email,V1,E1,S1,P1,A1,V2,E2,S2,P2,A2
student@school.com,7,8,6,7,9,8,9,7,8,10
```

### Full (All 3 cycles + optional fields)
```csv
email,Name,Establishment,V1,E1,S1,P1,A1,V2,E2,S2,P2,A2,V3,E3,S3,P3,A3
student@school.com,John Doe,My School,7,8,6,7,9,8,9,7,8,10,9,10,8,9,10
```

**Note:** V=Vision, E=Effort, S=Systems, P=Practice, A=Attitude

---

## What Gets Generated?

For each VESPA score (1-10), the system generates statement responses (1-5 Likert scale):

| Category | # Questions |
|----------|-------------|
| VISION   | 5           |
| EFFORT   | 4           |
| SYSTEMS  | 5           |
| PRACTICE | 6           |
| ATTITUDE | 9           |
| **TOTAL**| **29 per cycle** |

### Example

**Input:** VISION = 7  
**Generated:** `[4, 4, 5, 3, 4]` (average ≈ 4.0)  
**Verified:** VISION = 7 ✓

---

## Output Files

Running `csv_to_knack_importer.py` creates:

1. **`vespa_import_cycle1_knack_TIMESTAMP.json`**  
   → Import this into Knack Object_29 for Cycle 1

2. **`vespa_import_cycle2_knack_TIMESTAMP.json`**  
   → Import this into Knack Object_29 for Cycle 2 (if data exists)

3. **`vespa_import_full_TIMESTAMP.json`**  
   → Complete data for your records

4. **`vespa_import_summary_TIMESTAMP.csv`**  
   → Verification showing desired vs actual scores

---

## Need Help?

**"My CSV has different column names"**  
→ The script looks for: `email`, `Student Email`, or `Email`  
→ Edit `csv_to_knack_importer.py` line 70 to add your column name

**"I only have some cycles"**  
→ That's fine! Script only generates data for cycles you have

**"Scores don't verify correctly"**  
→ Rare, usually means score is on a threshold boundary  
→ Check the summary CSV for details

**"What if I make a mistake?"**  
→ Review the JSON files before importing to Knack  
→ You can edit them manually if needed

---

## Files Reference

| File | Purpose |
|------|---------|
| `csv_to_knack_importer.py` | Main script - CSV → Knack format |
| `reverse_vespa_calculator.py` | Core calculator logic |
| `knack_vespa_automation.py` | Direct Knack integration |
| `CSV_IMPORT_GUIDE.md` | Detailed CSV import instructions |
| `REVERSE_VESPA_CALCULATOR_README.md` | How the calculator works |
| `vespa_scores_template.csv` | Example CSV format |

---

## Summary

**You have VESPA scores** → **You need question responses** → **For Knack Object_29**

1. CSV → `python csv_to_knack_importer.py` → JSON files → Import to Knack
2. OR: Knack Object_10 → `python knack_vespa_automation.py` → Knack Object_29

Choose the method that fits your workflow!


