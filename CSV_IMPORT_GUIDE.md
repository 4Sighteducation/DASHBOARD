# CSV to Knack Import Guide

## Quick Start

You have VESPA scores in a CSV and want to create question responses for Knack. Here's how:

### Step 1: Prepare Your CSV

Your CSV needs these columns at minimum:

```csv
email,V1,E1,S1,P1,A1
student1@school.com,7,8,6,7,9
student2@school.com,5,6,5,5,6
```

**Required columns:**
- `email` or `Student Email` - student's email address
- `V1`, `E1`, `S1`, `P1`, `A1` - Cycle 1 VESPA scores (1-10)

**Optional columns:**
- `V2`, `E2`, `S2`, `P2`, `A2` - Cycle 2 VESPA scores
- `V3`, `E3`, `S3`, `P3`, `A3` - Cycle 3 VESPA scores
- `Name` - student name
- `Establishment` - school name
- `O1`, `O2`, `O3` - Overall scores (ignored, calculated automatically)

### Step 2: Run the Importer

```bash
python csv_to_knack_importer.py
```

The script will:
1. Ask for your CSV filename
2. Read the VESPA scores
3. Generate realistic question responses (1-5 Likert scale)
4. Verify the responses produce the correct VESPA scores
5. Create Knack-ready import files

### Step 3: Review the Output

You'll get these files:

1. **`vespa_import_full_TIMESTAMP.json`**
   - Complete data with all details for your records

2. **`vespa_import_cycle1_knack_TIMESTAMP.json`**
   - Ready to import into Knack Object_29 for Cycle 1
   
3. **`vespa_import_cycle2_knack_TIMESTAMP.json`** (if you have Cycle 2 data)
   - Ready to import into Knack Object_29 for Cycle 2
   
4. **`vespa_import_cycle3_knack_TIMESTAMP.json`** (if you have Cycle 3 data)
   - Ready to import into Knack Object_29 for Cycle 3

5. **`vespa_import_summary_TIMESTAMP.csv`**
   - Verification summary showing desired vs actual VESPA scores

### Step 4: Import to Knack

#### Option A: Manual Import (SAFEST)
1. Log into your Knack app
2. Go to Object_29 (Question Responses)
3. Click "Import"
4. Upload the cycle-specific JSON file
5. Map the fields (they should auto-map if field IDs match)
6. Review and complete the import

#### Option B: Direct Import via Script (FASTER)
If you have Knack API credentials in your `.env` file, you can use the direct import:

```bash
python knack_direct_import.py vespa_import_cycle1_knack_TIMESTAMP.json
```

## Example CSV Formats

### Format 1: Single Cycle
```csv
email,Name,V1,E1,S1,P1,A1
john@school.com,John Doe,7,8,6,7,9
jane@school.com,Jane Smith,8,9,7,8,10
```

### Format 2: Multiple Cycles
```csv
email,Name,V1,E1,S1,P1,A1,V2,E2,S2,P2,A2
john@school.com,John Doe,7,8,6,7,9,8,9,7,8,10
jane@school.com,Jane Smith,8,9,7,8,10,9,10,8,9,10
```

### Format 3: From Knack Export
```csv
Student Email,Name,Establishment,V1,E1,S1,P1,A1,O1
john@school.com,John Doe,My School,7,8,6,7,9,7.4
jane@school.com,Jane Smith,My School,8,9,7,8,10,8.4
```

## Verification

The script automatically verifies that generated statement scores produce the correct VESPA scores:

```
Generating scores for john@school.com - Cycle 1
  ✓ Verified - all scores match
```

If there's a mismatch (rare):
```
  ⚠ Warning - some scores don't match:
    VISION: desired 7, got 6
```

This happens when the VESPA score is on a threshold boundary. The script will adjust automatically.

## Understanding the Generated Data

### What Gets Generated

For each VESPA score (1-10), the script generates statement scores (1-5 Likert scale):

- **VISION**: 5 statements
- **EFFORT**: 4 statements  
- **SYSTEMS**: 5 statements
- **PRACTICE**: 6 statements
- **ATTITUDE**: 9 statements

**Total: 29 statements per cycle**

### Generation Method: "Realistic"

The script uses the "realistic" generation method, which creates natural-looking score patterns:

- **High VESPA scores (7-10)**: Mostly 4s and 5s, some 3s
- **Medium VESPA scores (4-6)**: Mix of 2s, 3s, and 4s
- **Low VESPA scores (1-3)**: Mostly 1s and 2s, some 3s

This mimics real student response patterns better than uniform scores.

## Troubleshooting

### Error: "No VESPA scores found for student@email.com"
- Check that your CSV has V1, E1, S1, P1, A1 columns
- Ensure scores are numbers between 1-10
- Check for empty cells

### Error: "Incomplete cycle scores"
- You need all 5 categories (V, E, S, P, A) for each cycle
- Missing any one category will skip that cycle

### Error: "File not found"
- Make sure your CSV is in the same folder as the script
- Check the filename spelling (including spaces)

### Verification Warnings
- If desired and verified scores don't match, it's usually because:
  - The VESPA score is on a threshold boundary
  - The script will try to adjust, but sometimes can't get exact match
  - This is rare and usually only off by 1

## Advanced Usage

### Custom Generation Methods

Edit the script to use different generation methods:

```python
statement_scores = self.calculator.generate_statement_scores(
    vespa_scores, 
    generation_method='balanced'  # or 'random' or 'realistic'
)
```

### Batch Processing Multiple Files

```python
for csv_file in ['school1.csv', 'school2.csv', 'school3.csv']:
    students = importer.read_csv(csv_file)
    results = importer.generate_statement_scores(students)
    importer.save_results(results, output_prefix=csv_file.replace('.csv', ''))
```

## FAQs

**Q: Will these scores be "real"?**  
A: No, they're generated to match the VESPA scores but don't represent actual student opinions. Use this only for students where you have VESPA scores but missing survey responses.

**Q: Can I edit the generated scores before importing?**  
A: Yes! The JSON files are human-readable. You can open them and edit any field values before importing to Knack.

**Q: What if I only have Cycle 1 scores?**  
A: That's fine! The script will only generate records for the cycles that have data in your CSV.

**Q: Can I import to Supabase instead of Knack?**  
A: Yes, but you'll need a different import script. The generated data structure is compatible.

**Q: How do I know which field IDs to use?**  
A: The script uses `psychometric_question_output_object_120.json` which has all the field mappings. These should match your Knack Object_29 fields.

## Need Help?

Check these files for more information:
- `REVERSE_VESPA_CALCULATOR_README.md` - How the calculator works
- `reverse_vespa_calculator.py` - The core calculation logic
- `knack_vespa_automation.py` - Direct Knack integration (reads from Object_10)


