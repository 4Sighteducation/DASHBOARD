# Questions Table Setup

## Overview
A new `questions` table has been added to Supabase to store all psychometric questions and their metadata. This provides a single source of truth for question information instead of relying on JSON files.

## Table Structure
```sql
questions (
    id UUID PRIMARY KEY,
    question_id VARCHAR(50) UNIQUE,      -- e.g., 'q1', 'q2', 'outcome_q_support'
    question_text TEXT,
    vespa_category VARCHAR(20),          -- VISION, EFFORT, SYSTEMS, PRACTICE, ATTITUDE, NA_OUTCOME
    question_order INTEGER,
    current_cycle_field_id VARCHAR(20),
    historical_cycle_field_base VARCHAR(20),
    field_id_cycle_1 VARCHAR(20),
    field_id_cycle_2 VARCHAR(20),
    field_id_cycle_3 VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

## Setup Instructions

### 1. Create the Table
Run `create_questions_table.sql` in Supabase SQL Editor:
```bash
# This will:
- Create the questions table
- Add indexes for performance
- Enable RLS policies
- Create a vespa_questions view
```

### 2. Load Questions Data
Run the Python script to populate the table:
```bash
python load_questions_to_supabase.py
```

This will:
- Load all questions from `AIVESPACoach/psychometric_question_details.json`
- Clear any existing questions
- Insert 32 questions (28 VESPA + 3 outcome + 1 vision grades)
- Verify the data was loaded correctly

## API Endpoint

A new API endpoint has been added to `app.py`:

```
GET /api/questions
```

Query Parameters:
- `category` - Filter by VESPA category (VISION, EFFORT, etc.)
- `active` - Filter by active status (default: true)

Example Usage:
```javascript
// Get all active questions
fetch('/api/questions')

// Get only VISION questions
fetch('/api/questions?category=VISION')

// Get all questions including inactive
fetch('/api/questions?active=false')
```

## Benefits

1. **Data Integrity**: Questions are now properly linked to responses and statistics
2. **Single Source of Truth**: No more managing multiple JSON files
3. **Better Querying**: Can JOIN with other tables for comprehensive analysis
4. **Frontend Flexibility**: Questions can be fetched dynamically via API
5. **Easy Updates**: Questions can be updated in the database without code changes

## Database Relationships

```
questions (1) ← → (many) question_responses
questions (1) ← → (many) question_statistics
```

The `question_id` field links all three tables together.

## Maintenance

- To add new questions: Insert into the questions table
- To deactivate questions: Set `is_active = false`
- To reorder questions: Update the `question_order` field

## View for VESPA Questions Only

A convenience view is created:
```sql
SELECT * FROM vespa_questions;  -- Returns only VESPA questions (excludes NA_OUTCOME)
```