# Knack VESPA Automation

## Overview

This automation system integrates with your Knack database to automatically generate Object_29 records (statement scores) for students who have VESPA scores but are missing detailed survey responses.

## How It Works

1. **Reads from Object_10**: Finds student records by email and extracts their VESPA scores (V1-O1, V2-O2, V3-O3)
   - Note: The OVERALL score (O1, O2, O3) is read but NOT used in generation - it's calculated from the 5 VESPA categories

2. **Generates Statement Scores**: Uses the reverse VESPA calculator to create realistic statement scores (1-5) that would produce those VESPA scores
   - VISION: 5 statements
   - EFFORT: 4 statements  
   - SYSTEMS: 5 statements
   - PRACTICE: 6 statements
   - ATTITUDE: 9 statements

3. **Creates Object_29 Records**: Maps generated scores to the correct fields using `psychometric_question_output_object_120.json`:
   - Each question has specific field IDs for cycles 1, 2, and 3
   - Example: Question q1 (VISION) → field_3309 (Cycle 1), field_3310 (Cycle 2), field_3311 (Cycle 3)
   - The script automatically uses the correct field IDs from the JSON mapping

4. **Preserves Connected Fields**: Copies these many-to-many connections from Object_10 to Object_29:
   - field_133 → field_1821: VESPA Customer IDs (array)
   - field_439 → field_2069: Staff Admin IDs (array)
   - field_145 → field_2070: Tutors IDs (array)
   - Plus field_2732: Student email (added to Object_29)

## Setup Instructions

### 1. Install Requirements

Ensure you have all required Python packages:

```bash
pip install requests numpy
```

### 2. Configure Field Mappings

1. Copy `knack_config_example.py` to `knack_config.py`:
   ```bash
   cp knack_config_example.py knack_config.py
   ```

2. Edit `knack_config.py` with your actual values:
   - **API Credentials**: Your Knack app ID and API key
   - **Field Mappings**: The actual field IDs for VESPA scores in Object_10
   - **Connected Fields**: The many-to-many connection fields:
     - field_133 (VESPA Customer) → field_1821
     - field_439 (Staff Admin) → field_2069  
     - field_145 (Tutors) → field_2070

### 3. Field Mapping Reference

You need to map these fields in `knack_config.py`:

**Object_10 VESPA Score Fields:**
- Cycle 1: V1 (Vision), E1 (Effort), S1 (Systems), P1 (Practice), A1 (Attitude), O1 (Overall)
- Cycle 2: V2, E2, S2, P2, A2, O2
- Cycle 3: V3, E3, S3, P3, A3, O3

**Object_29 Statement Score Fields** (from `psychometric_question_output_object_120.json`):
- These are automatically mapped by the script using the JSON configuration files
- The script reads this file to know exactly which field to use for each question and cycle

Example Field Mapping:
```
Question "I've worked out the next steps..." (VISION):
- Cycle 1: field_3309
- Cycle 2: field_3310  
- Cycle 3: field_3311

Question "I am a hard working student" (EFFORT):
- Cycle 1: field_3333
- Cycle 2: field_3334
- Cycle 3: field_3335
```

## Usage

### Basic Usage

Run the automation script:

```bash
python run_vespa_automation.py
```

The script will:
1. Ask how you want to provide student emails (manual entry, file, or test data)
2. Perform a dry run to show what would be created
3. Ask for confirmation before creating actual records
4. Generate detailed reports of the results

### Input Methods

#### Method 1: Manual Entry
Type or paste emails one per line when prompted.

#### Method 2: File Input
Create a text file with one email per line:
```
student1@example.com
student2@example.com
student3@example.com
```

#### Method 3: Test Mode
Use built-in test emails to verify the system works.

### Advanced Usage

For direct API usage in your own scripts:

```python
from knack_vespa_automation import KnackVESPAAutomation

# Initialize
automation = KnackVESPAAutomation(app_id, api_key)

# Process students
emails = ['student@example.com']
results = automation.process_student_list(emails, dry_run=False)
```

## Features

### Safety Features
- **Dry Run Mode**: Always shows what would be created before making changes
- **Duplicate Prevention**: Checks existing Object_29 records to avoid duplicates
- **Cycle-Specific Processing**: Only adds data for cycles that have VESPA scores
- **Rate Limiting**: Respects Knack API limits

### Reporting
- **Summary Report**: Overview of processing results
- **Detailed JSON**: Complete record of all operations
- **Success List**: Emails of successfully processed students

### Error Handling
- Validates email formats
- Handles missing students gracefully
- Reports specific errors for each student
- Continues processing even if some students fail

## Output Files

The script generates timestamped files:

1. `vespa_automation_report_YYYYMMDD_HHMMSS.txt` - Human-readable summary
2. `vespa_automation_results_YYYYMMDD_HHMMSS.json` - Detailed JSON results
3. `vespa_automation_success_YYYYMMDD_HHMMSS.txt` - List of successful emails

## Troubleshooting

### Common Issues

1. **"Student not found in Object_10"**
   - Verify the email exists in Object_10
   - Check that the email field ID is correct in `knack_config.py`

2. **"No VESPA scores found"**
   - Ensure the VESPA score field IDs are correct
   - Verify the student has V1-O1, V2-O2, or V3-O3 scores

3. **"Failed to create Object_29 record"**
   - Check API credentials are valid
   - Verify you have permission to create Object_29 records
   - Check the API response for specific error messages
   - Ensure connected field arrays are properly formatted

4. **Connected Fields Issues**
   - The script expects arrays for VESPA Customer, Staff Admin, and Tutors
   - If Object_10 returns objects instead of IDs, the script extracts the IDs
   - Empty arrays are handled gracefully

### API Rate Limits

Adjust `API_RATE_LIMIT` in `knack_config.py` based on your Knack plan:
- Free plan: 1 request per second (set to 1.0)
- Paid plans: Check your plan details

## Data Integrity

The generated statement scores:
- Are mathematically consistent with VESPA scores
- Follow realistic response patterns
- Are verified to produce the correct VESPA scores
- Won't perfectly reflect actual student opinions (they're approximations)

## Security Notes

- Never commit `knack_config.py` with real credentials
- Keep your API key secure
- Consider using environment variables for production
- Add `knack_config.py` to `.gitignore`

## Support

For issues or questions:
1. Check the error messages in the console
2. Review the generated report files
3. Verify your field mappings in `knack_config.py`
4. Ensure your Knack API credentials have proper permissions 