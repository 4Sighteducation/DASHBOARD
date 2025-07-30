#!/usr/bin/env python3
"""
Sync script to migrate data from Knack to Supabase
This script fetches all data from Knack and populates the Supabase database
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_knack_to_supabase.log'),
        logging.StreamHandler()
    ]
)

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
BASE_KNACK_URL = "https://api.knack.com/v1/objects"

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Knack field mappings (from your existing app)
OBJECT_KEYS = {
    'establishments': 'object_2',
    'vespa_results': 'object_10',
    'psychometric': 'object_29',
    'staff_admins': 'object_3',
    'academy_trusts': 'object_134'
}

def make_knack_request(object_key, page=1, rows_per_page=1000, filters=None):
    """Make a request to Knack API with pagination support"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"{BASE_KNACK_URL}/{object_key}/records"
    params = {
        'page': page,
        'rows_per_page': rows_per_page
    }
    
    if filters:
        params['filters'] = json.dumps(filters)
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Knack API error: {e}")
        raise

def fetch_all_knack_records(object_key, filters=None):
    """Fetch all records from a Knack object, handling pagination"""
    all_records = []
    page = 1
    total_pages = None
    
    while True:
        logging.info(f"Fetching {object_key} page {page}...")
        data = make_knack_request(object_key, page=page, filters=filters)
        
        records = data.get('records', [])
        all_records.extend(records)
        
        if total_pages is None:
            total_pages = data.get('total_pages', 1)
            logging.info(f"Total pages for {object_key}: {total_pages}")
        
        if page >= total_pages or not records:
            break
            
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    logging.info(f"Fetched {len(all_records)} records from {object_key}")
    return all_records

def sync_establishments():
    """Sync establishments (schools) from Knack to Supabase"""
    logging.info("Syncing establishments...")
    
    establishments = fetch_all_knack_records(OBJECT_KEYS['establishments'])
    
    for est in establishments:
        try:
            # Map Knack fields to Supabase schema
            establishment_data = {
                'knack_id': est['id'],
                'name': est.get('field_11', ''),  # School name
                'is_australian': est.get('field_3508_raw', False) == 'true'
            }
            
            # Upsert to Supabase
            result = supabase.table('establishments').upsert(establishment_data).execute()
            
        except Exception as e:
            logging.error(f"Error syncing establishment {est.get('id')}: {e}")
    
    logging.info(f"Synced {len(establishments)} establishments")

def sync_students_and_vespa_scores():
    """Sync students and VESPA scores from Object_10"""
    logging.info("Syncing students and VESPA scores...")
    
    vespa_records = fetch_all_knack_records(OBJECT_KEYS['vespa_results'])
    
    # Get establishment mapping
    establishments = supabase.table('establishments').select('id', 'knack_id').execute()
    est_map = {e['knack_id']: e['id'] for e in establishments.data}
    
    students_processed = set()
    scores_synced = 0
    
    for record in vespa_records:
        try:
            # Extract student info
            student_email = record.get('field_197_raw', {}).get('email', '')
            if not student_email:
                continue
            
            # Get establishment UUID
            est_knack_id = record.get('field_133_raw', [None])[0] if record.get('field_133_raw') else None
            establishment_id = est_map.get(est_knack_id) if est_knack_id else None
            
            # Create/update student if not already processed
            if student_email not in students_processed:
                student_data = {
                    'knack_id': record['id'],
                    'email': student_email,
                    'name': record.get('field_187_raw', ''),
                    'establishment_id': establishment_id,
                    'year_group': record.get('field_223', ''),
                    'course': record.get('field_2299', ''),
                    'faculty': record.get('field_144_raw', '')
                }
                
                student_result = supabase.table('students').upsert(
                    student_data,
                    on_conflict='email'
                ).execute()
                
                students_processed.add(student_email)
            
            # Get student ID
            student = supabase.table('students').select('id').eq('email', student_email).execute()
            if not student.data:
                continue
                
            student_id = student.data[0]['id']
            
            # Extract VESPA scores for each cycle
            for cycle in [1, 2, 3]:
                # Calculate field offsets for each cycle
                field_offset = (cycle - 1) * 6
                vision_field = f'field_{155 + field_offset}_raw'
                
                # Check if this cycle has data
                if record.get(vision_field) is not None:
                    vespa_data = {
                        'student_id': student_id,
                        'cycle': cycle,
                        'vision': record.get(f'field_{155 + field_offset}_raw'),
                        'effort': record.get(f'field_{156 + field_offset}_raw'),
                        'systems': record.get(f'field_{157 + field_offset}_raw'),
                        'practice': record.get(f'field_{158 + field_offset}_raw'),
                        'attitude': record.get(f'field_{159 + field_offset}_raw'),
                        'overall': record.get(f'field_{160 + field_offset}_raw'),
                        'completion_date': record.get('field_855'),
                        'academic_year': calculate_academic_year(
                            record.get('field_855'),
                            establishment_id
                        )
                    }
                    
                    # Upsert VESPA scores
                    supabase.table('vespa_scores').upsert(
                        vespa_data,
                        on_conflict='student_id,cycle'
                    ).execute()
                    
                    scores_synced += 1
                    
        except Exception as e:
            logging.error(f"Error syncing VESPA record {record.get('id')}: {e}")
    
    logging.info(f"Synced {len(students_processed)} students and {scores_synced} VESPA scores")

def sync_question_responses():
    """Sync psychometric question responses from Object_29"""
    logging.info("Syncing question responses...")
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        question_mapping = json.load(f)
    
    # Get student mapping
    students = supabase.table('students').select('id', 'knack_id').execute()
    student_map = {s['knack_id']: s['id'] for s in students.data}
    
    psychometric_records = fetch_all_knack_records(OBJECT_KEYS['psychometric'])
    responses_synced = 0
    
    for record in psychometric_records:
        try:
            # Get student ID from connection
            student_knack_id = record.get('field_1819_raw', [None])[0] if record.get('field_1819_raw') else None
            student_id = student_map.get(student_knack_id)
            
            if not student_id:
                continue
            
            # Process each cycle's data
            for cycle in [1, 2, 3]:
                cycle_field_map = {
                    1: 'field_1953',
                    2: 'field_1955',
                    3: 'field_1956'
                }
                
                # Check if this cycle has data
                if record.get(cycle_field_map[cycle]):
                    # Process all questions
                    for q_detail in question_mapping:
                        field_id = q_detail.get(f'fieldIdCycle{cycle}')
                        if field_id:
                            response_value = record.get(f'{field_id}_raw')
                            
                            if response_value:
                                response_data = {
                                    'student_id': student_id,
                                    'cycle': cycle,
                                    'question_id': q_detail['questionId'],
                                    'response_value': int(response_value)
                                }
                                
                                supabase.table('question_responses').insert(response_data).execute()
                                responses_synced += 1
                                
        except Exception as e:
            logging.error(f"Error syncing psychometric record {record.get('id')}: {e}")
    
    logging.info(f"Synced {responses_synced} question responses")

def calculate_academic_year(date_str, establishment_id=None):
    """Calculate academic year based on date and establishment location"""
    if not date_str:
        return None
    
    try:
        # Parse date (Knack format: MM/DD/YYYY)
        date = datetime.strptime(date_str, '%m/%d/%Y')
        
        # Check if Australian school
        is_australian = False
        if establishment_id:
            est = supabase.table('establishments').select('is_australian').eq('id', establishment_id).execute()
            if est.data:
                is_australian = est.data[0].get('is_australian', False)
        
        if is_australian:
            # Australian: Calendar year
            return str(date.year)
        else:
            # UK: Academic year (Aug-Jul)
            if date.month >= 8:
                return f"{date.year}-{str(date.year + 1)[2:]}"
            else:
                return f"{date.year - 1}-{str(date.year)[2:]}"
                
    except Exception as e:
        logging.error(f"Error calculating academic year: {e}")
        return None

def calculate_statistics():
    """Calculate and store statistics for schools"""
    logging.info("Calculating statistics...")
    
    # Get all establishments
    establishments = supabase.table('establishments').select('*').execute()
    
    for est in establishments.data:
        try:
            # Get current academic year
            current_year = calculate_academic_year(datetime.now().strftime('%m/%d/%Y'), est['id'])
            
            # Calculate statistics for each cycle and element
            for cycle in [1, 2, 3]:
                for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                    # Call the Supabase function to calculate stats
                    result = supabase.rpc('calculate_element_stats', {
                        'p_establishment_id': est['id'],
                        'p_cycle': cycle,
                        'p_element': element
                    }).execute()
                    
                    if result.data and result.data[0].get('count', 0) > 0:
                        stats_data = {
                            'establishment_id': est['id'],
                            'cycle': cycle,
                            'academic_year': current_year,
                            'element': element,
                            **result.data[0]
                        }
                        
                        supabase.table('school_statistics').upsert(
                            stats_data,
                            on_conflict='establishment_id,cycle,academic_year,element'
                        ).execute()
                        
        except Exception as e:
            logging.error(f"Error calculating statistics for {est['name']}: {e}")
    
    logging.info("Statistics calculation complete")

def main():
    """Main sync function"""
    start_time = datetime.now()
    
    try:
        # Log sync start
        sync_log = {
            'sync_type': 'full_sync',
            'status': 'started',
            'started_at': start_time.isoformat()
        }
        log_result = supabase.table('sync_logs').insert(sync_log).execute()
        sync_log_id = log_result.data[0]['id']
        
        # Run sync operations
        sync_establishments()
        sync_students_and_vespa_scores()
        sync_question_responses()
        calculate_statistics()
        
        # Update sync log
        end_time = datetime.now()
        supabase.table('sync_logs').update({
            'status': 'completed',
            'completed_at': end_time.isoformat(),
            'metadata': {
                'duration_seconds': (end_time - start_time).total_seconds()
            }
        }).eq('id', sync_log_id).execute()
        
        logging.info(f"Sync completed successfully in {end_time - start_time}")
        
    except Exception as e:
        logging.error(f"Sync failed: {e}")
        
        # Update sync log with error
        if 'sync_log_id' in locals():
            supabase.table('sync_logs').update({
                'status': 'failed',
                'completed_at': datetime.now().isoformat(),
                'error_message': str(e)
            }).eq('id', sync_log_id).execute()
        
        raise

if __name__ == "__main__":
    main()