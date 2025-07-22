# Testing the VESPA Automation Locally

## Prerequisites

1. **Python installed** (check with `python --version` in PowerShell)
2. **Required packages** installed:
   ```powershell
   pip install requests numpy
   ```

## Step 1: Test the Basic Calculator First

This doesn't require any Knack API access:

```powershell
# In PowerShell, navigate to your project directory
cd "C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD"

# Test the reverse calculator
python reverse_vespa_calculator.py
```

This will show:
- Examples of generating statement scores from VESPA scores
- Different generation methods
- Verification that the math works correctly

## Step 2: Test Statement Generation

```powershell
# Test the add missing students script
python add_missing_students.py
```

This will:
- Generate example students
- Show how statement scores are created
- Save test files (generated_students.json, etc.)

## Step 3: Set Up for Knack Testing

1. **Create your config file**:
   ```powershell
   # Copy the example config
   copy knack_config_example.py knack_config.py
   ```

2. **Edit knack_config.py** (use Notepad or your editor):
   ```python
   # Add your actual values
   KNACK_APP_ID = "your-actual-app-id"
   KNACK_API_KEY = "your-actual-api-key"
   
   # Update Object_10 field IDs if needed
   OBJECT_10_FIELDS = {
       'email': 'field_XXX',  # Your actual email field ID
       # ... etc
   }
   ```

## Step 4: Test with Dry Run (SAFE - No Changes Made)

```powershell
# Run the automation script
python run_vespa_automation.py
```

Choose option 3 for test data first:
```
How would you like to provide student emails?
1. Type/paste emails manually
2. Load from a text file
3. Use test data

Enter choice (1-3): 3
```

The script will:
1. Use test emails (test.student1@example.com, etc.)
2. Show what it WOULD do (dry run mode)
3. NOT create any actual records

## Step 5: Test with Real Student Email (Still Safe)

Run again and choose option 1:
```powershell
python run_vespa_automation.py
```

Enter a real student email that you know has VESPA scores in Object_10.

The dry run will show:
- Whether the student was found
- What VESPA scores were read
- What would be created in Object_29
- Any existing cycles that would be skipped

## Step 6: Create a Test Student List

Create a file `test_students.txt`:
```
student1@yourschool.edu
student2@yourschool.edu
student3@yourschool.edu
```

Then run:
```powershell
python run_vespa_automation.py
```

Choose option 2 and enter `test_students.txt`

## Understanding the Output

### Dry Run Output Example:
```
[1/3] Processing student1@yourschool.edu...
  Found VESPA scores for cycles: [1, 2]
  Would create records for cycles: [1, 2]

[2/3] Processing student2@yourschool.edu...
  No record found for email: student2@yourschool.edu

[3/3] Processing student3@yourschool.edu...
  Found VESPA scores for cycles: [1]
  Cycle 1 already exists for student3@yourschool.edu, skipping...
  Would create records for cycles: []
```

### What to Check:
- ✓ Students are found in Object_10
- ✓ VESPA scores are read correctly
- ✓ Existing records are detected
- ✓ No errors about field mappings

## Step 7: Small Production Test

Once dry run looks good:

1. **Pick ONE student** who definitely needs Object_29 records
2. Run the script and say "yes" when asked to create records
3. Check in Knack that the Object_29 record was created correctly

## Troubleshooting

### "Module not found" error:
```powershell
pip install requests numpy
```

### "knack_config.py not found":
```powershell
copy knack_config_example.py knack_config.py
# Then edit it with your values
```

### "Student not found in Object_10":
- Check the email field ID in your config
- Verify the email exists in Object_10
- Check for typos in the email

### API errors:
- Verify your API credentials
- Check your Knack plan's API limits
- Look at the error message details

## Safety Features

The script has multiple safety features:
- **Dry run by default** - shows what would happen
- **Confirmation required** - must type "yes" to proceed
- **Duplicate prevention** - won't overwrite existing data
- **Detailed logging** - saves reports of what was done
- **Rate limiting** - respects API limits

## Files Created During Testing

After testing, you'll have these files (safe to delete):
- `knack_config.py` (KEEP THIS - your configuration)
- `generated_students.json` (test data)
- `vespa_automation_report_*.txt` (run reports)
- `vespa_automation_results_*.json` (detailed results)

## When You're Ready

After successful testing:
1. The scripts are ready to use
2. You can process larger batches of students
3. All changes are logged for your records

Remember: Always start with dry run mode to see what will happen! 