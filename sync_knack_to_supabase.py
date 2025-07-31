#!/usr/bin/env python3
"""
Sync script to migrate data from Knack to Supabase
This script fetches all data from Knack and populates the Supabase database
Enhanced with batch processing, resume capability, and timeout handling
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
import pickle
from pathlib import Path
import signal
import threading

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

# Initialize Supabase client with timeout
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Knack field mappings (from your existing app)
OBJECT_KEYS = {
    'establishments': 'object_2',
    'vespa_results': 'object_10',
    'psychometric': 'object_29',
    'staff_admins': 'object_5',  # Fixed: was object_3, should be object_5
    'super_users': 'object_21',  # Added: for super user access
    'academy_trusts': 'object_134'
}

# Checkpoint file for resume capability
CHECKPOINT_FILE = Path('sync_checkpoint.pkl')

# Batch sizes for efficient processing
BATCH_SIZES = {
    'establishments': 50,
    'students': 100,
    'vespa_scores': 200,
    'question_responses': 500
}

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logging.info("Shutdown requested, will stop after current batch...")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class SyncCheckpoint:
    """Manages sync progress for resume capability"""
    def __init__(self):
        self.establishments_synced = False
        self.vespa_page = 1
        self.students_processed = set()
        self.psychometric_page = 1
        self.statistics_calculated = False
        self.last_update = datetime.now()
    
    def save(self):
        """Save checkpoint to disk"""
        with open(CHECKPOINT_FILE, 'wb') as f:
            pickle.dump(self, f)
    
    @classmethod
    def load(cls):
        """Load checkpoint from disk"""
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE, 'rb') as f:
                return pickle.load(f)
        return cls()
    
    def clear(self):
        """Clear checkpoint file"""
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

def keep_system_awake():
    """Prevent system from sleeping during sync"""
    try:
        import ctypes
        if sys.platform == 'win32':
            # Windows: Prevent sleep
            ctypes.windll.kernel32.SetThreadExecutionState(
                0x80000000 | 0x00000001 | 0x00000002
            )
    except Exception as e:
        logging.warning(f"Could not prevent system sleep: {e}")

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
    
    # Filter out cancelled establishments
    filters = [
        {
            'field': 'field_2209',
            'operator': 'is not',
            'value': 'Cancelled'
        }
    ]
    
    establishments = fetch_all_knack_records(OBJECT_KEYS['establishments'], filters=filters)
    
    for est in establishments:
        try:
            # Map Knack fields to Supabase schema
            # Get establishment name with better fallback
            est_name = est.get('field_44') or est.get('field_44_raw') or ""
            if not est_name or est_name == "EMPTY":
                # Try alternative fields or use a descriptive fallback
                est_name = est.get('field_11') or est.get('identifier') or f"Establishment {est['id'][:8]}"
            
            establishment_data = {
                'knack_id': est['id'],
                'name': est_name,
                # Check field_3573 for Australian schools - only "True" counts
                'is_australian': est.get('field_3573_raw', '') == 'True'
            }
            
            # Upsert to Supabase
            result = supabase.table('establishments').upsert(
                establishment_data,
                on_conflict='knack_id'
            ).execute()
            
        except Exception as e:
            logging.error(f"Error syncing establishment {est.get('id')}: {e}")
    
    logging.info(f"Synced {len(establishments)} establishments")

def sync_students_and_vespa_scores(checkpoint=None):
    """Sync students and VESPA scores from Object_10 with batch processing"""
    logging.info("Syncing students and VESPA scores...")
    
    # Load checkpoint data
    if checkpoint:
        page = checkpoint.vespa_page
        students_processed = checkpoint.students_processed
        logging.info(f"Resuming from page {page}, {len(students_processed)} students already processed")
    else:
        page = 1
        students_processed = set()
    
    # Get establishment mapping first - cache this for efficiency
    establishments = supabase.table('establishments').select('id', 'knack_id').execute()
    est_map = {e['knack_id']: e['id'] for e in establishments.data}
    
    # Pre-fetch all Australian establishments to avoid repeated queries
    australian_ests = {e['id']: e['is_australian'] for e in establishments.data}
    
    scores_synced = 0
    student_batch = []
    vespa_batch = []
    
    # Process in batches to avoid memory issues
    while True:
        if shutdown_requested:
            logging.info("Shutdown requested, saving checkpoint...")
            checkpoint.vespa_page = page
            checkpoint.students_processed = students_processed
            checkpoint.save()
            break
            
        logging.info(f"Processing VESPA records page {page}...")
        data = make_knack_request(OBJECT_KEYS['vespa_results'], page=page)
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                # Extract student info
                email_field = record.get('field_197_raw', {})
                if isinstance(email_field, dict):
                    email_value = email_field.get('email', '')
                    # Handle case where email value is also a dict
                    if isinstance(email_value, dict):
                        student_email = email_value.get('address', '') or email_value.get('email', '') or str(email_value)
                    else:
                        student_email = str(email_value) if email_value else ''
                elif isinstance(email_field, str):
                    student_email = email_field
                else:
                    student_email = ''
                
                # Ensure email is a string and not empty
                if not student_email or not isinstance(student_email, str) or student_email == '{}':
                    continue
                
                # Get establishment UUID
                est_field = record.get('field_133_raw', [])
                if est_field and isinstance(est_field, list) and len(est_field) > 0:
                    est_item = est_field[0]
                    # Handle if the establishment reference is a dict
                    if isinstance(est_item, dict):
                        est_knack_id = est_item.get('id') or est_item.get('value') or None
                    else:
                        est_knack_id = est_item
                else:
                    est_knack_id = None
                establishment_id = est_map.get(est_knack_id) if est_knack_id else None
                
                # Create/update student if not already processed
                if student_email not in students_processed:
                    # Extract name safely
                    name_field = record.get('field_187_raw', '')
                    if isinstance(name_field, dict):
                        # Extract full name from the name object
                        student_name = name_field.get('full', '') or f"{name_field.get('first', '')} {name_field.get('last', '')}".strip()
                    elif isinstance(name_field, str):
                        student_name = name_field
                    else:
                        student_name = ''
                    
                    student_data = {
                        'knack_id': record['id'],
                        'email': student_email,
                        'name': student_name,
                        'establishment_id': establishment_id,
                        'group': record.get('field_223', ''),  # field_223 is group
                        'year_group': record.get('field_144', ''),  # Corrected: field_144 is year_group
                        'course': record.get('field_2299', ''),
                        'faculty': record.get('field_782', '')  # Corrected: field_782 is faculty
                    }
                    
                    student_result = supabase.table('students').upsert(
                        student_data,
                        on_conflict='knack_id'
                    ).execute()
                    
                    students_processed.add(student_email)
                
                # Get student ID by knack_id (more reliable than email)
                student = supabase.table('students').select('id').eq('knack_id', record['id']).execute()
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
                        # Helper function to convert empty strings to None
                        def clean_score(value):
                            if value == "" or value is None:
                                return None
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return None
                        
                        vespa_data = {
                            'student_id': student_id,
                            'cycle': cycle,
                            'vision': clean_score(record.get(f'field_{155 + field_offset}_raw')),
                            'effort': clean_score(record.get(f'field_{156 + field_offset}_raw')),
                            'systems': clean_score(record.get(f'field_{157 + field_offset}_raw')),
                            'practice': clean_score(record.get(f'field_{158 + field_offset}_raw')),
                            'attitude': clean_score(record.get(f'field_{159 + field_offset}_raw')),
                            'overall': clean_score(record.get(f'field_{160 + field_offset}_raw')),
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
                # Log more details for debugging
                if 'unhashable' in str(e):
                    logging.error(f"Debug - field_197_raw: {record.get('field_197_raw')}")
                    logging.error(f"Debug - field_133_raw: {record.get('field_133_raw')}")
                    logging.error(f"Debug - student_email type: {type(student_email) if 'student_email' in locals() else 'undefined'}")
        
        page += 1
        time.sleep(0.5)  # Rate limiting
    
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
    
    responses_synced = 0
    
    # Process in batches to avoid memory issues
    page = 1
    while True:
        logging.info(f"Processing psychometric records page {page}...")
        data = make_knack_request(OBJECT_KEYS['psychometric'], page=page)
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                # Get Object_10 connection via field_792 (email-based connection)
                object_10_field = record.get('field_792_raw', [])
                if object_10_field and isinstance(object_10_field, list) and len(object_10_field) > 0:
                    object_10_item = object_10_field[0]
                    # Handle if the Object_10 reference is a dict
                    if isinstance(object_10_item, dict):
                        object_10_knack_id = object_10_item.get('id') or object_10_item.get('value') or None
                    else:
                        object_10_knack_id = object_10_item
                else:
                    object_10_knack_id = None
                # Map Object_10 ID to student ID (students were created from Object_10 records)
                student_id = student_map.get(object_10_knack_id)
                
                if not student_id:
                    continue
                
                # Process each cycle's data
                for cycle in [1, 2, 3]:
                    # Process all questions for this cycle
                    for q_detail in question_mapping:
                        field_id = q_detail.get(f'fieldIdCycle{cycle}')
                        if field_id:
                            response_value = record.get(f'{field_id}_raw')
                            
                            # Only create a record if there's an actual response
                            if response_value is not None and response_value != '':
                                try:
                                    response_data = {
                                        'student_id': student_id,
                                        'cycle': cycle,
                                        'question_id': q_detail['questionId'],
                                        'response_value': int(response_value)
                                    }
                                    
                                    supabase.table('question_responses').insert(response_data).execute()
                                except (ValueError, TypeError):
                                    # Skip if can't convert to int
                                    pass
                                    responses_synced += 1
                                    
            except Exception as e:
                logging.error(f"Error syncing psychometric record {record.get('id')}: {e}")
        
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    logging.info(f"Synced {responses_synced} question responses")

def calculate_academic_year(date_str, establishment_id=None):
    """Calculate academic year based on date and establishment location"""
    if not date_str:
        return None
    
    try:
        # Parse date (Knack format: DD/MM/YYYY - UK format)
        date = datetime.strptime(date_str, '%d/%m/%Y')
        
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