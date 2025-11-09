#!/usr/bin/env python3
"""
Sync student responses, goals, and coaching notes from Knack Object_10 to Supabase
This populates the new student profile tables
"""

import os
import json
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Field mappings from Object_10
FIELD_MAPPINGS = {
    'responses': {
        1: 'field_2302',
        2: 'field_2303',
        3: 'field_2304'
    },
    'goals': {
        1: {'text': 'field_2499', 'set_date': 'field_2321', 'due_date': 'field_2500'},
        2: {'text': 'field_2493', 'set_date': 'field_2496', 'due_date': 'field_2497'},
        3: {'text': 'field_2494', 'set_date': 'field_2497', 'due_date': 'field_2498'}
    },
    'coaching': {
        1: {'text': 'field_2488', 'date': 'field_2485'},
        2: {'text': 'field_2490', 'date': 'field_2486'},
        3: {'text': 'field_2491', 'date': 'field_2487'}
    }
}

def fetch_knack_records(object_key, page=1):
    """Fetch records from Knack with pagination"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY
    }
    
    response = requests.get(
        f"https://api.knack.com/v1/objects/{object_key}/records",
        headers=headers,
        params={'page': page, 'rows_per_page': 1000},
        timeout=30
    )
    
    return response.json()

def parse_knack_date(date_str):
    """Parse Knack date format (DD/MM/YYYY) to ISO format (YYYY-MM-DD)"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except:
        return None

def calculate_academic_year(date_str):
    """Simple academic year calculation"""
    if not date_str:
        date = datetime.now()
    else:
        try:
            date = datetime.strptime(date_str, '%d/%m/%Y')
        except:
            date = datetime.now()
    
    if date.month >= 8:
        return f"{date.year}/{date.year + 1}"
    else:
        return f"{date.year - 1}/{date.year}"

def sync_student_profile_data():
    """Sync student responses, goals, and coaching notes from Object_10"""
    logging.info("Syncing student profile data from Object_10...")
    
    # Get student ID mappings
    logging.info("Loading student mappings...")
    student_map = {}  # email -> student_id
    offset = 0
    limit = 1000
    
    while True:
        students = supabase.table('students').select('id', 'email').limit(limit).offset(offset).execute()
        if not students.data:
            break
        for student in students.data:
            if student.get('email'):
                student_map[student['email'].lower()] = student['id']
        if len(students.data) < limit:
            break
        offset += limit
    
    logging.info(f"Loaded {len(student_map)} student mappings")
    
    # Fetch all Object_10 records with batch processing
    page = 1
    total_processed = 0
    responses_synced = 0
    goals_synced = 0
    coaching_synced = 0
    
    # Batch containers
    response_batch = []
    goal_batch = []
    coaching_batch = []
    BATCH_SIZE = 100
    
    while True:
        logging.info(f"Fetching Object_10 page {page}...")
        data = fetch_knack_records('object_10', page)
        records = data.get('records', [])
        
        if not records:
            break
        
        for record in records:
            try:
                # Get student email
                email_field = record.get('field_197_raw', {})
                if isinstance(email_field, dict):
                    student_email = email_field.get('email', '')
                else:
                    student_email = str(email_field) if email_field else ''
                
                if not student_email:
                    continue
                
                # Get student_id from map
                student_id = student_map.get(student_email.lower())
                if not student_id:
                    continue
                
                # Calculate academic year
                completion_date = record.get('field_855', '')
                academic_year = calculate_academic_year(completion_date)
                
                # Process each cycle
                for cycle in [1, 2, 3]:
                    # === SYNC STUDENT RESPONSE ===
                    response_field = FIELD_MAPPINGS['responses'][cycle]
                    response_text = record.get(response_field, '') or record.get(f'{response_field}_raw', '')
                    
                    if response_text and response_text.strip():
                        response_batch.append({
                            'student_id': student_id,
                            'cycle': cycle,
                            'academic_year': academic_year,
                            'response_text': response_text
                        })
                    
                    # === SYNC STUDENT GOALS ===
                    goal_fields = FIELD_MAPPINGS['goals'][cycle]
                    goal_text = record.get(goal_fields['text'], '') or record.get(f'{goal_fields["text"]}_raw', '')
                    goal_set_date = parse_knack_date(record.get(goal_fields['set_date'], ''))
                    goal_due_date = parse_knack_date(record.get(goal_fields['due_date'], ''))
                    
                    if goal_text and goal_text.strip():
                        goal_batch.append({
                            'student_id': student_id,
                            'cycle': cycle,
                            'academic_year': academic_year,
                            'goal_text': goal_text,
                            'goal_set_date': goal_set_date,
                            'goal_due_date': goal_due_date
                        })
                    
                    # === SYNC COACHING NOTES ===
                    coaching_fields = FIELD_MAPPINGS['coaching'][cycle]
                    coaching_text = record.get(coaching_fields['text'], '') or record.get(f'{coaching_fields["text"]}_raw', '')
                    coaching_date = parse_knack_date(record.get(coaching_fields['date'], ''))
                    
                    if coaching_text and coaching_text.strip():
                        coaching_batch.append({
                            'student_id': student_id,
                            'staff_id': None,  # Don't have staff mapping yet
                            'cycle': cycle,
                            'academic_year': academic_year,
                            'coaching_text': coaching_text,
                            'coaching_date': coaching_date
                        })
                
                # Process batches when they reach size limit
                if len(response_batch) >= BATCH_SIZE:
                    supabase.table('student_responses').upsert(response_batch, on_conflict='student_id,cycle,academic_year').execute()
                    responses_synced += len(response_batch)
                    logging.info(f"  Synced {responses_synced} responses...")
                    response_batch = []
                
                if len(goal_batch) >= BATCH_SIZE:
                    supabase.table('student_goals').upsert(goal_batch, on_conflict='student_id,cycle,academic_year').execute()
                    goals_synced += len(goal_batch)
                    logging.info(f"  Synced {goals_synced} goals...")
                    goal_batch = []
                
                if len(coaching_batch) >= BATCH_SIZE:
                    supabase.table('staff_coaching_notes').upsert(coaching_batch, on_conflict='student_id,cycle,academic_year').execute()
                    coaching_synced += len(coaching_batch)
                    logging.info(f"  Synced {coaching_synced} coaching notes...")
                    coaching_batch = []
                
                total_processed += 1
                
                if total_processed % 100 == 0:
                    logging.info(f"Processed {total_processed} records...")
            
            except Exception as e:
                logging.error(f"Error processing record {record.get('id')}: {e}")
        
        page += 1
    
    # Process remaining batches
    if response_batch:
        supabase.table('student_responses').upsert(response_batch, on_conflict='student_id,cycle,academic_year').execute()
        responses_synced += len(response_batch)
    
    if goal_batch:
        supabase.table('student_goals').upsert(goal_batch, on_conflict='student_id,cycle,academic_year').execute()
        goals_synced += len(goal_batch)
    
    if coaching_batch:
        supabase.table('staff_coaching_notes').upsert(coaching_batch, on_conflict='student_id,cycle,academic_year').execute()
        coaching_synced += len(coaching_batch)
    
    logging.info(f"\n✅ Sync complete!")
    logging.info(f"  Total records processed: {total_processed}")
    logging.info(f"  Student responses synced: {responses_synced}")
    logging.info(f"  Student goals synced: {goals_synced}")
    logging.info(f"  Coaching notes synced: {coaching_synced}")

if __name__ == '__main__':
    sync_student_profile_data()

