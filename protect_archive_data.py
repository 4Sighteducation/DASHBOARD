#!/usr/bin/env python3
"""
Solution to protect archived data from being overwritten by blank records
This modifies the sync to NEVER overwrite non-null VESPA scores with null values
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_school_data_status(establishment_name):
    """Check the current status of a school's data"""
    
    # Find the establishment
    est = supabase.table('establishments').select('*').eq('name', establishment_name).execute()
    
    if not est.data:
        logging.error(f"School not found: {establishment_name}")
        return None
    
    establishment_id = est.data[0]['id']
    logging.info(f"Found {establishment_name}: {establishment_id}")
    
    # Get students
    students = supabase.table('students')\
        .select('id')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    if not students.data:
        logging.warning("No students found")
        return None
    
    student_ids = [s['id'] for s in students.data]
    logging.info(f"Found {len(student_ids)} students")
    
    # Check VESPA scores in batches
    batch_size = 100
    null_count = 0
    non_null_count = 0
    
    for i in range(0, len(student_ids), batch_size):
        batch = student_ids[i:i+batch_size]
        
        scores = supabase.table('vespa_scores')\
            .select('vision, effort, systems, practice, attitude')\
            .in_('student_id', batch)\
            .execute()
        
        for score in scores.data:
            if all(score.get(field) is None for field in ['vision', 'effort', 'systems', 'practice', 'attitude']):
                null_count += 1
            else:
                non_null_count += 1
    
    return {
        'establishment_id': establishment_id,
        'total_students': len(student_ids),
        'null_scores': null_count,
        'non_null_scores': non_null_count
    }

def create_archive_protection_view():
    """Create a database view/function to protect archived data"""
    
    protection_sql = """
    -- Create a function to safely upsert VESPA scores
    -- This will NEVER overwrite non-null scores with null values
    
    CREATE OR REPLACE FUNCTION safe_upsert_vespa_scores(
        p_student_id UUID,
        p_cycle INTEGER,
        p_vision INTEGER,
        p_effort INTEGER,
        p_systems INTEGER,
        p_practice INTEGER,
        p_attitude INTEGER,
        p_overall INTEGER,
        p_completion_date DATE,
        p_academic_year VARCHAR
    )
    RETURNS void AS $$
    DECLARE
        existing_record RECORD;
    BEGIN
        -- Check if record exists
        SELECT * INTO existing_record
        FROM vespa_scores
        WHERE student_id = p_student_id AND cycle = p_cycle;
        
        IF existing_record IS NULL THEN
            -- Insert new record
            INSERT INTO vespa_scores (
                student_id, cycle, vision, effort, systems, 
                practice, attitude, overall, completion_date, academic_year
            ) VALUES (
                p_student_id, p_cycle, p_vision, p_effort, p_systems,
                p_practice, p_attitude, p_overall, p_completion_date, p_academic_year
            );
        ELSE
            -- Update only if new values are not null or existing values are null
            UPDATE vespa_scores
            SET 
                vision = COALESCE(p_vision, existing_record.vision),
                effort = COALESCE(p_effort, existing_record.effort),
                systems = COALESCE(p_systems, existing_record.systems),
                practice = COALESCE(p_practice, existing_record.practice),
                attitude = COALESCE(p_attitude, existing_record.attitude),
                overall = COALESCE(p_overall, existing_record.overall),
                completion_date = COALESCE(p_completion_date, existing_record.completion_date),
                academic_year = COALESCE(p_academic_year, existing_record.academic_year)
            WHERE student_id = p_student_id AND cycle = p_cycle
            -- Only update if there's actually new non-null data
            AND (
                (p_vision IS NOT NULL AND p_vision != existing_record.vision) OR
                (p_effort IS NOT NULL AND p_effort != existing_record.effort) OR
                (p_systems IS NOT NULL AND p_systems != existing_record.systems) OR
                (p_practice IS NOT NULL AND p_practice != existing_record.practice) OR
                (p_attitude IS NOT NULL AND p_attitude != existing_record.attitude) OR
                (p_overall IS NOT NULL AND p_overall != existing_record.overall) OR
                (p_completion_date IS NOT NULL AND p_completion_date != existing_record.completion_date) OR
                (p_academic_year IS NOT NULL AND p_academic_year != existing_record.academic_year)
            );
        END IF;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Create an RPC endpoint for this function
    COMMENT ON FUNCTION safe_upsert_vespa_scores IS 'Safely upsert VESPA scores without overwriting non-null values with nulls';
    """
    
    print("SQL function to protect archived data:")
    print("=" * 80)
    print(protection_sql)
    print("=" * 80)
    print("\nRun this SQL in your Supabase SQL editor to enable archive protection")

def suggest_sync_modifications():
    """Suggest modifications to sync_knack_to_supabase.py"""
    
    print("\n" + "=" * 80)
    print("RECOMMENDED SYNC MODIFICATIONS")
    print("=" * 80)
    
    print("""
Modify sync_knack_to_supabase.py to protect archived data:

1. In the sync_vespa_scores() function, add a check before upserting:

```python
def sync_vespa_scores():
    # ... existing code ...
    
    # Before upserting, check if we're about to overwrite non-null with null
    if vision is None and effort is None and systems is None:
        # Check if existing record has data
        existing = supabase.table('vespa_scores')\\
            .select('vision, effort, systems, practice, attitude')\\
            .eq('student_id', student_id)\\
            .eq('cycle', cycle)\\
            .execute()
        
        if existing.data and existing.data[0]:
            # If any existing values are non-null, skip this update
            if any(existing.data[0].get(field) for field in ['vision', 'effort', 'systems', 'practice', 'attitude']):
                logging.warning(f"Skipping null update for student {student_id} cycle {cycle} - preserving existing data")
                continue
    
    # ... continue with upsert ...
```

2. Alternative: Use the safe_upsert_vespa_scores RPC function:

```python
# Instead of direct upsert, use the safe function
supabase.rpc('safe_upsert_vespa_scores', {
    'p_student_id': student_id,
    'p_cycle': cycle,
    'p_vision': vision,
    'p_effort': effort,
    'p_systems': systems,
    'p_practice': practice,
    'p_attitude': attitude,
    'p_overall': overall,
    'p_completion_date': completion_date,
    'p_academic_year': academic_year
}).execute()
```
""")

def main():
    print("=" * 80)
    print("ARCHIVE DATA PROTECTION SOLUTION")
    print("=" * 80)
    
    # Check British School status
    print("\nChecking The British School Al Khubairat...")
    status = check_school_data_status("The British School Al Khubairat")
    
    if status:
        print(f"\nCurrent Status:")
        print(f"  Total students: {status['total_students']}")
        print(f"  Records with NULL scores: {status['null_scores']}")
        print(f"  Records with data: {status['non_null_scores']}")
        
        if status['null_scores'] > status['non_null_scores']:
            print("\n⚠️ WARNING: Majority of records are NULL - data has been wiped!")
            print("   You will need to restore from backup")
    
    # Provide protection solution
    create_archive_protection_view()
    suggest_sync_modifications()
    
    print("\n" + "=" * 80)
    print("RECOMMENDED PROCEDURE FOR FUTURE:")
    print("=" * 80)
    print("""
To prevent this issue in future:

1. BEFORE wiping Knack data:
   - Export current Supabase data as backup
   - Mark records as "archived" with a flag
   
2. DURING sync:
   - Never overwrite non-null values with nulls
   - Use the safe_upsert function provided above
   
3. ALTERNATIVE approach:
   - DELETE students from Knack before new year
   - Upload fresh students
   - This way, archived students remain in Supabase untouched
   
4. FOR THIS YEAR:
   - Restore The British School Al Khubairat from backup
   - Implement the protection before next sync
""")

if __name__ == "__main__":
    main()
