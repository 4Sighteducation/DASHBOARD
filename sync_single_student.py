#!/usr/bin/env python3
"""
Sync a single student from Knack to Supabase
Usage: python sync_single_student.py aramsey@vespa.academy
"""

import os
import sys
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

def calculate_academic_year(date_str):
    """Calculate UK academic year (Aug-Jul)"""
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

def sync_student(email):
    """Sync a single student and their VESPA data from Knack"""
    logging.info(f"Syncing student: {email}")
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY
    }
    
    # 1. Find student in Knack Object_10 by email (field_197)
    filters = json.dumps({'match': 'and', 'rules': [{'field': 'field_197', 'operator': 'is', 'value': email}]})
    
    response = requests.get(
        "https://api.knack.com/v1/objects/object_10/records",
        headers=headers,
        params={'filters': filters},
        timeout=30
    )
    
    if not response.ok:
        logging.error(f"Knack API error: {response.status_code}")
        return False
    
    records = response.json().get('records', [])
    
    if not records:
        logging.error(f"Student not found in Knack: {email}")
        return False
    
    record = records[0]  # Take first match
    logging.info(f"Found Knack record: {record['id']}")
    
    # 2. Get establishment
    est_field = record.get('field_133_raw', [])
    establishment_id = None
    
    if est_field and isinstance(est_field, list) and len(est_field) > 0:
        est_knack_id = est_field[0].get('id') if isinstance(est_field[0], dict) else est_field[0]
        # Map to Supabase
        est_result = supabase.table('establishments').select('id').eq('knack_id', est_knack_id).execute()
        if est_result.data:
            establishment_id = est_result.data[0]['id']
    
    # 3. Calculate academic year
    completion_date = record.get('field_855', '')
    academic_year = calculate_academic_year(completion_date)
    
    # 4. Create student record
    name_field = record.get('field_187_raw', record.get('field_198', ''))
    if isinstance(name_field, dict):
        student_name = name_field.get('full', '')
    else:
        student_name = str(name_field)
    
    student_data = {
        'knack_id': record['id'],
        'email': email,
        'name': student_name,
        'establishment_id': establishment_id,
        'academic_year': academic_year,
        'group': record.get('field_223', ''),
        'year_group': record.get('field_144', ''),
        'course': record.get('field_2299', ''),
        'faculty': record.get('field_782', '')
    }
    
    logging.info(f"Creating student: {student_name} ({academic_year})")
    student_result = supabase.table('students').upsert(student_data, on_conflict='email,academic_year').execute()
    student_id = student_result.data[0]['id']
    logging.info(f"Student ID: {student_id}")
    
    # 5. Sync VESPA scores for all 3 cycles
    scores_synced = 0
    for cycle in [1, 2, 3]:
        field_offset = (cycle - 1) * 6
        vision = record.get(f'field_{155 + field_offset}_raw')
        
        if vision is not None:
            completion_date_raw = record.get('field_855', '')
            completion_date = None
            if completion_date_raw:
                try:
                    date_obj = datetime.strptime(completion_date_raw, '%d/%m/%Y')
                    completion_date = date_obj.strftime('%Y-%m-%d')
                except:
                    pass
            
            vespa_data = {
                'student_id': student_id,
                'cycle': cycle,
                'vision': int(vision) if vision else None,
                'effort': int(record.get(f'field_{156 + field_offset}_raw') or 0) or None,
                'systems': int(record.get(f'field_{157 + field_offset}_raw') or 0) or None,
                'practice': int(record.get(f'field_{158 + field_offset}_raw') or 0) or None,
                'attitude': int(record.get(f'field_{159 + field_offset}_raw') or 0) or None,
                'overall': int(record.get(f'field_{160 + field_offset}_raw') or 0) or None,
                'completion_date': completion_date,
                'academic_year': academic_year
            }
            
            logging.info(f"Syncing Cycle {cycle}: V{vespa_data['vision']}, E{vespa_data['effort']}, S{vespa_data['systems']}, P{vespa_data['practice']}, A{vespa_data['attitude']}")
            
            supabase.table('vespa_scores').upsert(vespa_data, on_conflict='student_id,cycle,academic_year').execute()
            scores_synced += 1
    
    # 6. Sync student responses (field_2302, 2303, 2304)
    for cycle, field in [(1, 'field_2302'), (2, 'field_2303'), (3, 'field_2304')]:
        response_text = record.get(field, '') or record.get(f'{field}_raw', '')
        if response_text:
            response_data = {
                'student_id': student_id,
                'cycle': cycle,
                'academic_year': academic_year,
                'response_text': response_text
            }
            supabase.table('student_responses').upsert(response_data, on_conflict='student_id,cycle,academic_year').execute()
            logging.info(f"Synced response for Cycle {cycle}")
    
    # 7. Sync goals (field_2499, 2493, 2494)
    goal_fields = [(1, 'field_2499', 'field_2321', 'field_2500'),
                   (2, 'field_2493', 'field_2496', 'field_2497'),
                   (3, 'field_2494', 'field_2497', 'field_2498')]
    
    for cycle, text_field, set_date_field, due_date_field in goal_fields:
        goal_text = record.get(text_field, '') or record.get(f'{text_field}_raw', '')
        if goal_text:
            # Convert UK dates to ISO format
            set_date_raw = record.get(set_date_field, '')
            due_date_raw = record.get(due_date_field, '')
            
            set_date = None
            due_date = None
            
            if set_date_raw:
                try:
                    set_date = datetime.strptime(set_date_raw, '%d/%m/%Y').strftime('%Y-%m-%d')
                except:
                    pass
            
            if due_date_raw:
                try:
                    due_date = datetime.strptime(due_date_raw, '%d/%m/%Y').strftime('%Y-%m-%d')
                except:
                    pass
            
            goal_data = {
                'student_id': student_id,
                'cycle': cycle,
                'academic_year': academic_year,
                'goal_text': goal_text,
                'goal_set_date': set_date,
                'goal_due_date': due_date
            }
            supabase.table('student_goals').upsert(goal_data, on_conflict='student_id,cycle,academic_year').execute()
            logging.info(f"Synced goals for Cycle {cycle}")
    
    # 8. Find and sync Object_29 (question responses)
    logging.info("Syncing question responses...")
    
    # Find Object_29 records connected to this Object_10
    obj29_response = requests.get(
        "https://api.knack.com/v1/objects/object_29/records",
        headers=headers,
        params={'filters': json.dumps({'match': 'and', 'rules': [{'field': 'field_792', 'operator': 'is', 'value': record['id']}]})},
        timeout=30
    )
    
    if obj29_response.ok:
        obj29_records = obj29_response.json().get('records', [])
        
        if obj29_records:
            # Load question mapping
            with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
                question_mapping = json.load(f)
            
            obj29 = obj29_records[0]  # Take first match
            
            for cycle in [1, 2, 3]:
                for q_detail in question_mapping:
                    field_id = q_detail.get(f'fieldIdCycle{cycle}')
                    if field_id:
                        response_value = obj29.get(f'{field_id}_raw')
                        if response_value and str(response_value).isdigit():
                            int_value = int(response_value)
                            if 1 <= int_value <= 5:
                                response_data = {
                                    'student_id': student_id,
                                    'cycle': cycle,
                                    'academic_year': academic_year,
                                    'question_id': q_detail['questionId'],
                                    'response_value': int_value
                                }
                                supabase.table('question_responses').upsert(response_data, on_conflict='student_id,cycle,academic_year,question_id').execute()
            
            logging.info(f"Synced question responses for all cycles")
    
    logging.info(f"✅ Sync complete for {email}!")
    logging.info(f"   - Student ID: {student_id}")
    logging.info(f"   - Academic Year: {academic_year}")
    logging.info(f"   - Cycles synced: {scores_synced}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_single_student.py <email>")
        print("Example: python sync_single_student.py aramsey@vespa.academy")
        sys.exit(1)
    
    email = sys.argv[1]
    sync_student(email)

