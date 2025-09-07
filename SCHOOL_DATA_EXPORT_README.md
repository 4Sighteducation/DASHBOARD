# School Data Export Guide

## Overview
This guide provides SQL queries and a Python script to export Cycle 1 and Cycle 2 data from Supabase for the following schools:

1. **Tonyrefail Community School** (53e70907-bd30-46fb-b870-e4d4a9c1d06b)
2. **Whitchurch High School** (1a327b33-d924-453c-803e-82671f94a242)
3. **Ysgol Garth Olwg** (65f4eb79-6f08-4797-83ae-c09b8ae3c194)
4. **Llanishen High School** (027ede5d-3384-419e-8390-c86d81cc08ab)

## Files Created
- `supabase_data_export_queries.sql` - Contains all SQL queries
- `export_school_data.py` - Python script for automated export
- `SCHOOL_DATA_EXPORT_README.md` - This guide

## Data Included
### VESPA Scores (vespa_scores table)
- Vision, Effort, Systems, Practice, Attitude scores (0-10 scale)
- Overall score
- Completion dates
- Academic year
- Student information (name, email, year group, course, faculty)

### Question Responses (question_responses table)
- Individual question responses (1-5 scale)
- Question IDs and text
- VESPA categories for each question
- Response timestamps

## Export Methods

### Method 1: Using Supabase Dashboard (Easiest)
1. Log into your Supabase project dashboard
2. Go to the **SQL Editor**
3. Copy one of the queries from `supabase_data_export_queries.sql`
4. Run the query
5. Click the **"Download CSV"** button in the results panel

### Method 2: Using Python Script (Automated)
1. Ensure you have the required environment variables set in `.env`:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

2. Install required packages (if not already installed):
   ```bash
   pip install pandas python-dotenv supabase
   ```

3. Run the export script:
   ```bash
   python export_school_data.py
   ```

4. The script will create a timestamped folder with three CSV files:
   - `vespa_scores_cycles_1_2_[timestamp].csv` - All VESPA scores
   - `question_responses_cycles_1_2_[timestamp].csv` - All question responses
   - `export_summary_[timestamp].csv` - Summary statistics

### Method 3: Using PostgreSQL Client
If you have pgAdmin, DBeaver, or another PostgreSQL client:

1. Connect to your Supabase database using the connection string
2. Run any of the queries from `supabase_data_export_queries.sql`
3. Use the client's export feature to save as CSV

### Method 4: Using PSQL Command Line
```bash
# Connect to database
psql "postgresql://[user]:[password]@[host]:[port]/[database]"

# Export VESPA scores to CSV
\copy (SELECT [paste Query 1 from SQL file here]) TO 'vespa_scores.csv' WITH CSV HEADER

# Export question responses to CSV
\copy (SELECT [paste Query 2 from SQL file here]) TO 'question_responses.csv' WITH CSV HEADER
```

## Available Queries

The `supabase_data_export_queries.sql` file contains 4 queries:

1. **VESPA Scores Query** - Extracts all VESPA scores for cycles 1 & 2
2. **Question Responses Query** - Extracts all individual question responses
3. **Summary View** - Shows data availability counts per school
4. **Detailed Student-Level Summary** - Pivot view combining scores and sample questions

## Data Structure

### VESPA Scores CSV Columns
- `school_name` - Name of the school
- `student_name` - Student's name
- `student_email` - Student's email
- `year_group` - Student's year group
- `course` - Student's course (if applicable)
- `faculty` - Student's faculty (if applicable)
- `cycle` - Assessment cycle (1 or 2)
- `vision` - Vision score (0-10)
- `effort` - Effort score (0-10)
- `systems` - Systems score (0-10)
- `practice` - Practice score (0-10)
- `attitude` - Attitude score (0-10)
- `overall` - Overall score (0-10)
- `completion_date` - Date of assessment completion
- `academic_year` - Academic year
- `score_created_at` - Timestamp when record was created

### Question Responses CSV Columns
- `school_name` - Name of the school
- `student_name` - Student's name
- `student_email` - Student's email
- `year_group` - Student's year group
- `course` - Student's course (if applicable)
- `faculty` - Student's faculty (if applicable)
- `cycle` - Assessment cycle (1 or 2)
- `question_id` - Question identifier (e.g., 'q1', 'q2')
- `question_text` - Full text of the question (if available)
- `vespa_category` - VESPA category (VISION, EFFORT, etc.)
- `response_value` - Student's response (1-5 scale)
- `response_created_at` - Timestamp when response was recorded

## Notes
- The data is filtered to include only cycles 1 and 2 as requested
- All timestamps are in UTC
- Empty values indicate the student hasn't completed that particular assessment
- The Python script creates a summary report showing record counts per school

## Troubleshooting
- If you get no results, verify the establishment IDs are correct
- Check that students are properly linked to establishments
- Ensure your Supabase credentials have read access to all required tables
- For large datasets, the export might take a few minutes

## Support
If you encounter any issues or need different data fields, you can:
1. Modify the SQL queries in `supabase_data_export_queries.sql`
2. Adjust the Python script in `export_school_data.py`
3. Check the database schema in `supabase_schema.sql` for available fields
