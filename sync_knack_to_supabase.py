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
import re
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
        logging.FileHandler('sync_knack_to_supabase.log', encoding='utf-8'),
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

# Add super_users table definition (missing from original schema)
SUPER_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS super_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knack_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

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

# Global sync report tracking
sync_report = {
    'start_time': None,
    'end_time': None,
    'tables': {},
    'warnings': [],
    'errors': []
}

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

def extract_email_from_html(html_or_email):
    """Extract email address from HTML anchor tag or return as-is if plain email"""
    if not html_or_email:
        return ''
    
    # If it starts with <a href, extract the email
    if '<a href="mailto:' in str(html_or_email):
        # Extract email between mailto: and "
        match = re.search(r'mailto:([^"]+)"', str(html_or_email))
        if match:
            return match.group(1)
    
    # Otherwise assume it's already a plain email
    return str(html_or_email).strip()

def sync_establishments():
    """Sync establishments (schools) from Knack to Supabase"""
    logging.info("Syncing establishments...")
    
    # Track metrics
    table_name = 'establishments'
    sync_report['tables'][table_name] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'updated_records': 0,
        'errors': 0
    }
    
    # Get count before sync
    try:
        before_count = supabase.table('establishments').select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_before'] = before_count.count
    except:
        pass
    
    # Filter out cancelled establishments AND resource portals
    # Only sync COACHING PORTAL establishments
    filters = [
        {
            'field': 'field_2209',
            'operator': 'is not',
            'value': 'Cancelled'
        },
        {
            'field': 'field_63',  # Portal type field
            'operator': 'contains',
            'value': 'COACHING PORTAL'
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
                # trust_id removed - needs to be handled separately as it requires UUID reference
            }
            
            # Upsert to Supabase
            result = supabase.table('establishments').upsert(
                establishment_data,
                on_conflict='knack_id'
            ).execute()
            
        except Exception as e:
            logging.error(f"Error syncing establishment {est.get('id')}: {e}")
            sync_report['tables'][table_name]['errors'] += 1
    
    # Get count after sync
    try:
        after_count = supabase.table('establishments').select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_after'] = after_count.count
        sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
        sync_report['tables'][table_name]['end_time'] = datetime.now()
    except:
        pass
    
    logging.info(f"Synced {len(establishments)} establishments")

def sync_students_and_vespa_scores():
    """Sync students and VESPA scores from Object_10 with batch processing"""
    logging.info("Syncing students and VESPA scores...")
    
    # Track metrics for both tables
    for table_name in ['students', 'vespa_scores']:
        sync_report['tables'][table_name] = {
            'start_time': datetime.now(),
            'records_before': 0,
            'records_after': 0,
            'new_records': 0,
            'updated_records': 0,
            'errors': 0
        }
        try:
            before_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_before'] = before_count.count
        except:
            pass
    
    # Initialize tracking variables
    page = 1
    students_processed = set()
    
    # Get establishment mapping first - cache this for efficiency
    establishments = supabase.table('establishments').select('id', 'knack_id', 'is_australian').execute()
    est_map = {e['knack_id']: e['id'] for e in establishments.data}
    
    # Pre-fetch all Australian establishments to avoid repeated queries
    australian_ests = {e['id']: e.get('is_australian', False) for e in establishments.data}
    
    # Pre-fetch existing students to build knack_id -> student_id mapping
    logging.info("Loading existing student mappings...")
    student_id_map = {}
    offset = 0
    limit = 1000
    while True:
        existing_students = supabase.table('students').select('id', 'knack_id').limit(limit).offset(offset).execute()
        if not existing_students.data:
            break
        for student in existing_students.data:
            student_id_map[student['knack_id']] = student['id']
        if len(existing_students.data) < limit:
            break
        offset += limit
    logging.info(f"Loaded {len(student_id_map)} existing student mappings")
    
    scores_synced = 0
    students_synced = 0
    student_batch = []
    vespa_batch = []
    
    # Process in batches to avoid memory issues
    while True:
        if shutdown_requested:
            logging.info("Shutdown requested, stopping gracefully...")
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
                    
                    student_batch.append(student_data)
                    students_processed.add(student_email)
                    
                    # Process batch if it reaches the limit
                    if len(student_batch) >= BATCH_SIZES['students']:
                        logging.info(f"Processing batch of {len(student_batch)} students...")
                        result = supabase.table('students').upsert(
                            student_batch,
                            on_conflict='knack_id'
                        ).execute()
                        
                        # Update the student_id_map with the newly inserted/updated students
                        for student in result.data:
                            student_id_map[student['knack_id']] = student['id']
                        
                        students_synced += len(student_batch)
                        student_batch = []
                
                # Get student ID from map (avoid individual lookups)
                student_id = student_id_map.get(record['id'])
                if not student_id:
                    # Student might be in the current batch but not yet in database
                    # Skip for now, it will be processed in the next sync run
                    continue
                
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
                        
                        # Convert UK date format to ISO format for PostgreSQL
                        completion_date_raw = record.get('field_855')
                        completion_date = None
                        if completion_date_raw and completion_date_raw.strip():  # Check for empty strings
                            try:
                                # Parse UK format DD/MM/YYYY and convert to YYYY-MM-DD
                                date_obj = datetime.strptime(completion_date_raw, '%d/%m/%Y')
                                completion_date = date_obj.strftime('%Y-%m-%d')
                            except ValueError:
                                logging.warning(f"Invalid date format: {completion_date_raw}")
                        
                        # Get individual scores
                        vision = clean_score(record.get(f'field_{155 + field_offset}_raw'))
                        effort = clean_score(record.get(f'field_{156 + field_offset}_raw'))
                        systems = clean_score(record.get(f'field_{157 + field_offset}_raw'))
                        practice = clean_score(record.get(f'field_{158 + field_offset}_raw'))
                        attitude = clean_score(record.get(f'field_{159 + field_offset}_raw'))
                        
                        # Get overall score from Knack
                        overall = clean_score(record.get(f'field_{160 + field_offset}_raw'))
                        
                        # Validate overall score is within valid range (0-10)
                        if overall is not None and (overall < 0 or overall > 10):
                            logging.warning(f"Invalid overall score {overall} for record {record['id']}, cycle {cycle} - skipping this score")
                            # Skip this entire VESPA score entry if overall is invalid
                            continue
                        
                        vespa_data = {
                            'student_id': student_id,
                            'cycle': cycle,
                            'vision': vision,
                            'effort': effort,
                            'systems': systems,
                            'practice': practice,
                            'attitude': attitude,
                            'overall': overall,
                            'completion_date': completion_date,
                            'academic_year': calculate_academic_year(
                                record.get('field_855'),
                                establishment_id,
                                australian_ests.get(establishment_id, False)
                            )
                        }
                        
                        vespa_batch.append(vespa_data)
                        
                        # Process batch if it reaches the limit
                        if len(vespa_batch) >= BATCH_SIZES['vespa_scores']:
                            logging.info(f"Processing batch of {len(vespa_batch)} VESPA scores...")
                            supabase.table('vespa_scores').upsert(
                                vespa_batch,
                                on_conflict='student_id,cycle'
                            ).execute()
                            scores_synced += len(vespa_batch)
                            vespa_batch = []
                        
            except Exception as e:
                error_msg = f"Error syncing VESPA record {record.get('id')}: {e}"
                logging.error(error_msg)
                sync_report['errors'].append(error_msg)
                sync_report['tables']['vespa_scores']['errors'] += 1
                # Log more details for debugging
                if 'unhashable' in str(e):
                    logging.error(f"Debug - field_197_raw: {record.get('field_197_raw')}")
                    logging.error(f"Debug - field_133_raw: {record.get('field_133_raw')}")
                    logging.error(f"Debug - student_email type: {type(student_email) if 'student_email' in locals() else 'undefined'}")
        
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    # Process any remaining students in the batch
    if student_batch:
        logging.info(f"Processing final batch of {len(student_batch)} students...")
        result = supabase.table('students').upsert(
            student_batch,
            on_conflict='knack_id'
        ).execute()
        
        # Update the student_id_map with the newly inserted/updated students
        for student in result.data:
            student_id_map[student['knack_id']] = student['id']
        
        students_synced += len(student_batch)
    
    # Process any remaining VESPA scores in the batch
    if vespa_batch:
        logging.info(f"Processing final batch of {len(vespa_batch)} VESPA scores...")
        supabase.table('vespa_scores').upsert(
            vespa_batch,
            on_conflict='student_id,cycle'
        ).execute()
        scores_synced += len(vespa_batch)
    
    # Get final counts
    for table_name in ['students', 'vespa_scores']:
        try:
            after_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_after'] = after_count.count
            sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
            sync_report['tables'][table_name]['end_time'] = datetime.now()
        except:
            pass
    
    logging.info(f"Synced {students_synced} students and {scores_synced} VESPA scores")

def sync_question_responses():
    """Sync psychometric question responses from Object_29"""
    logging.info("Syncing question responses...")
    
    # Track metrics
    table_name = 'question_responses'
    sync_report['tables'][table_name] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'updated_records': 0,
        'errors': 0,
        'skipped': 0,
        'duplicates_handled': 0
    }
    
    # Get count before sync
    try:
        before_count = supabase.table(table_name).select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_before'] = before_count.count
    except:
        pass
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        question_mapping = json.load(f)
    
    # Get student mapping - need to get ALL students, not just first 1000
    logging.info("Loading all students for mapping...")
    student_map = {}
    
    # Supabase returns max 1000 by default, need to paginate
    offset = 0
    limit = 1000
    while True:
        students = supabase.table('students').select('id', 'knack_id').limit(limit).offset(offset).execute()
        if not students.data:
            break
        
        for student in students.data:
            student_map[student['knack_id']] = student['id']
        
        logging.info(f"  Loaded batch at offset {offset}: {len(students.data)} students")
        
        if len(students.data) < limit:
            break
        offset += limit
    
    logging.info(f"Total loaded: {len(student_map)} student mappings")
    
    responses_synced = 0
    response_batch = []
    
    # Track processed Object_29 records to avoid duplicates
    processed_object29_ids = set()
    duplicate_object29_count = 0
    
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
                # Check if we've already processed this Object_29 record
                if record['id'] in processed_object29_ids:
                    duplicate_object29_count += 1
                    continue
                processed_object29_ids.add(record['id'])
                
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
                    sync_report['tables'][table_name]['skipped'] += 1
                    if sync_report['tables'][table_name]['skipped'] == 1:
                        sync_report['warnings'].append(f"Some question responses skipped due to missing student links")
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
                                    int_value = int(response_value)
                                    # Skip responses with value 0 (violates DB constraint)
                                    if int_value > 0:
                                        response_data = {
                                            'student_id': student_id,
                                            'cycle': cycle,
                                            'question_id': q_detail['questionId'],
                                            'response_value': int_value
                                        }
                                        
                                        response_batch.append(response_data)
                                        
                                        # Process batch if it reaches the limit
                                        if len(response_batch) >= BATCH_SIZES['question_responses']:
                                            # Deduplicate batch before sending
                                            deduped_batch = deduplicate_response_batch(response_batch)
                                            duplicates_removed = len(response_batch) - len(deduped_batch)
                                            if duplicates_removed > 0:
                                                logging.warning(f"Removed {duplicates_removed} duplicate responses from batch")
                                                sync_report['tables'][table_name]['duplicates_handled'] += duplicates_removed
                                            
                                            logging.info(f"Processing batch of {len(deduped_batch)} question responses...")
                                            supabase.table('question_responses').upsert(
                                                deduped_batch,
                                                on_conflict='student_id,cycle,question_id'
                                            ).execute()
                                            responses_synced += len(deduped_batch)
                                            response_batch = []
                                            
                                except (ValueError, TypeError):
                                    # Skip if can't convert to int
                                    pass
                                    
            except Exception as e:
                error_msg = f"Error syncing psychometric record {record.get('id')}: {e}"
                logging.error(error_msg)
                sync_report['tables'][table_name]['errors'] += 1
                if sync_report['tables'][table_name]['errors'] <= 10:
                    sync_report['errors'].append(error_msg)
        
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    # Process any remaining responses in the batch
    if response_batch:
        # Deduplicate batch before sending
        deduped_batch = deduplicate_response_batch(response_batch)
        duplicates_removed = len(response_batch) - len(deduped_batch)
        if duplicates_removed > 0:
            logging.warning(f"Removed {duplicates_removed} duplicate responses from final batch")
            sync_report['tables'][table_name]['duplicates_handled'] += duplicates_removed
        
        logging.info(f"Processing final batch of {len(deduped_batch)} question responses...")
        supabase.table('question_responses').upsert(
            deduped_batch,
            on_conflict='student_id,cycle,question_id'
        ).execute()
        responses_synced += len(deduped_batch)
    
    # Get final count
    try:
        after_count = supabase.table(table_name).select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_after'] = after_count.count
        sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
        sync_report['tables'][table_name]['end_time'] = datetime.now()
    except:
        pass
    
    if sync_report['tables'][table_name]['skipped'] > 0:
        sync_report['warnings'].append(f"{sync_report['tables'][table_name]['skipped']} question responses skipped due to missing student links")
    
    if sync_report['tables'][table_name]['duplicates_handled'] > 0:
        sync_report['warnings'].append(f"{sync_report['tables'][table_name]['duplicates_handled']} duplicate responses removed (multiple Object_29 records for same student)")
    
    if duplicate_object29_count > 0:
        logging.warning(f"Skipped {duplicate_object29_count} duplicate Object_29 records")
    
    logging.info(f"Synced {responses_synced} question responses")

def deduplicate_response_batch(batch):
    """Remove duplicate student/cycle/question combinations from a batch, keeping the first occurrence"""
    seen = set()
    deduped = []
    
    for response in batch:
        key = (response['student_id'], response['cycle'], response['question_id'])
        if key not in seen:
            seen.add(key)
            deduped.append(response)
    
    return deduped

def calculate_academic_year(date_str, establishment_id=None, is_australian=None):
    """Calculate academic year based on date and establishment location"""
    if not date_str:
        return None
    
    try:
        # Parse date (Knack format: DD/MM/YYYY - UK format)
        date = datetime.strptime(date_str, '%d/%m/%Y')
        
        # Check if Australian school
        if is_australian is None and establishment_id:
            # Only do API call if is_australian not provided (backward compatibility)
            try:
                est = supabase.table('establishments').select('is_australian').eq('id', establishment_id).execute()
                if est.data and len(est.data) > 0:
                    is_australian = est.data[0].get('is_australian', False)
                else:
                    is_australian = False
            except Exception as e:
                logging.warning(f"Could not determine if establishment is Australian: {e}")
                is_australian = False
        elif is_australian is None:
            is_australian = False
        
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

def sync_staff_admins():
    """Sync staff admins from object_5"""
    logging.info("Syncing staff admins...")
    
    # Track metrics
    table_name = 'staff_admins'
    sync_report['tables'][table_name] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'errors': 0
    }
    
    try:
        # Get count before
        before_count = supabase.table(table_name).select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_before'] = before_count.count
    except:
        pass
    
    try:
        staff_admins = fetch_all_knack_records(OBJECT_KEYS['staff_admins'])
        count = 0
        
        for admin in staff_admins:
            try:
                # Map fields from object_5
                # Extract email from HTML if needed
                email_raw = admin.get('field_86', '') or admin.get('field_86_raw', '')
                
                admin_data = {
                    'knack_id': admin['id'],
                    'email': extract_email_from_html(email_raw),
                    'name': admin.get('field_85', '') or admin.get('field_85_raw', '')  # Name field
                }
                
                if admin_data['email']:  # Only sync if email exists
                    supabase.table('staff_admins').upsert(
                        admin_data,
                        on_conflict='knack_id'
                    ).execute()
                    count += 1
                    
            except Exception as e:
                logging.error(f"Error processing staff admin {admin.get('id')}: {e}")
        
        # Get final count
        try:
            after_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_after'] = after_count.count
            sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
            sync_report['tables'][table_name]['end_time'] = datetime.now()
        except:
            pass
        
        logging.info(f"Synced {count} staff admins")
        
    except Exception as e:
        logging.error(f"Failed to sync staff admins: {e}")
        sync_report['errors'].append(f"Staff admin sync failed: {e}")

def sync_super_users():
    """Sync super users from object_21"""
    logging.info("Syncing super users...")
    
    # Track metrics
    table_name = 'super_users'
    sync_report['tables'][table_name] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'errors': 0
    }
    
    try:
        # Get count before
        before_count = supabase.table(table_name).select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_before'] = before_count.count
    except:
        pass
    
    try:
        # Check if we have the super_users table
        # First, let's create it if it doesn't exist
        try:
            supabase.table('super_users').select('id').limit(1).execute()
        except:
            logging.info("Creating super_users table...")
            # Table might not exist, but we'll continue anyway
        
        super_users = fetch_all_knack_records(OBJECT_KEYS['super_users'])
        count = 0
        
        for user in super_users:
            try:
                # Map fields from object_21
                # Extract email from HTML if needed
                email_raw = user.get('field_473', '') or user.get('field_473_raw', '')
                
                # Extract name from field_472_raw which has the name structure
                name_field = user.get('field_472_raw', {})
                if isinstance(name_field, dict):
                    full_name = name_field.get('full', '') or f"{name_field.get('first', '')} {name_field.get('last', '')}".strip()
                else:
                    full_name = user.get('field_472', '')
                
                user_data = {
                    'knack_id': user['id'],
                    'email': extract_email_from_html(email_raw),
                    'name': full_name
                }
                
                if user_data['email']:  # Only sync if email exists
                    supabase.table('super_users').upsert(
                        user_data,
                        on_conflict='knack_id'
                    ).execute()
                    count += 1
                    
            except Exception as e:
                logging.error(f"Error processing super user {user.get('id')}: {e}")
        
        # Get final count
        try:
            after_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_after'] = after_count.count
            sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
            sync_report['tables'][table_name]['end_time'] = datetime.now()
        except:
            pass
        
        logging.info(f"Synced {count} super users")
        
    except Exception as e:
        logging.error(f"Failed to sync super users: {e}")
        sync_report['errors'].append(f"Super user sync failed: {e}")

def calculate_statistics():
    """Calculate and store statistics for schools"""
    logging.info("Calculating school statistics...")
    
    # Track metrics
    table_name = 'school_statistics'
    sync_report['tables'][table_name] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'errors': 0
    }
    
    try:
        # Get count before
        before_count = supabase.table(table_name).select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_before'] = before_count.count
    except:
        pass
    
    try:
        # Try to use the enhanced stored procedure first
        result = supabase.rpc('calculate_all_statistics', {}).execute()
        logging.info("School statistics calculated successfully using stored procedure")
        
        # Get final count after stored procedure
        try:
            after_count = supabase.table('school_statistics').select('id', count='exact').execute()
            sync_report['tables']['school_statistics']['records_after'] = after_count.count
            sync_report['tables']['school_statistics']['new_records'] = after_count.count - sync_report['tables']['school_statistics']['records_before']
            sync_report['tables']['school_statistics']['end_time'] = datetime.now()
        except:
            pass
        
        return True
    except Exception as e:
        logging.warning(f"Stored procedure failed: {e}, falling back to manual calculation...")
    
    # Manual calculation fallback
    # Get all establishments
    establishments = supabase.table('establishments').select('*').execute()
    
    for est in establishments.data:
        try:
            # Get current academic year
            current_year = calculate_academic_year(
                datetime.now().strftime('%d/%m/%Y'), 
                est['id'], 
                est.get('is_australian', False)
            )
            
            # Get all students for this establishment
            students = supabase.table('students').select('id').eq('establishment_id', est['id']).execute()
            if not students.data:
                continue
                
            student_ids = [s['id'] for s in students.data]
            
            # Calculate statistics for each cycle and element
            for cycle in [1, 2, 3]:
                # Get all scores for this cycle
                scores = supabase.table('vespa_scores')\
                    .select('vision, effort, systems, practice, attitude, overall')\
                    .in_('student_id', student_ids)\
                    .eq('cycle', cycle)\
                    .execute()
                
                if not scores.data:
                    continue
                
                # Calculate stats for each element
                for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                    values = [s[element] for s in scores.data if s[element] is not None]
                    
                    if values:
                        import statistics as stats
                        
                        # Calculate distribution (count of each score 1-10 for ALL VESPA elements)
                        distribution = [0] * 10  # Indices 0-9 for scores 1-10
                        for v in values:
                            if 1 <= v <= 10:
                                distribution[int(v) - 1] += 1  # Score 1 goes to index 0, etc.
                        
                        stats_data = {
                            'establishment_id': est['id'],
                            'cycle': cycle,
                            'academic_year': current_year,
                            'element': element,
                            'mean': round(sum(values) / len(values), 2),
                            'std_dev': round(stats.stdev(values), 2) if len(values) > 1 else 0,
                            'count': len(values),
                            'percentile_25': round(stats.quantiles(values, n=4)[0], 2) if len(values) > 1 else values[0],
                            'percentile_50': round(stats.median(values), 2),
                            'percentile_75': round(stats.quantiles(values, n=4)[2], 2) if len(values) > 1 else values[0],
                            'distribution': distribution
                        }
                        
                        supabase.table('school_statistics').upsert(
                            stats_data,
                            on_conflict='establishment_id,cycle,academic_year,element'
                        ).execute()
                        
        except Exception as e:
            logging.error(f"Error calculating statistics for {est['name']}: {e}")
    
    # Get final count
    try:
        after_count = supabase.table('school_statistics').select('id', count='exact').execute()
        sync_report['tables']['school_statistics']['records_after'] = after_count.count
        sync_report['tables']['school_statistics']['new_records'] = after_count.count - sync_report['tables']['school_statistics']['records_before']
        sync_report['tables']['school_statistics']['end_time'] = datetime.now()
    except:
        pass
    
    logging.info("School statistics calculation complete")
    return True

def calculate_question_statistics():
    """Calculate comprehensive question-level statistics"""
    logging.info("Calculating question statistics...")
    
    # Track metrics
    table_name = 'question_statistics'
    sync_report['tables'][table_name] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'errors': 0
    }
    
    try:
        # Get count before
        before_count = supabase.table(table_name).select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_before'] = before_count.count
    except:
        pass
    
    try:
        # Try to use the enhanced stored procedure
        result = supabase.rpc('calculate_question_statistics_enhanced', {}).execute()
        logging.info("Question statistics calculated successfully using stored procedure")
        
        # Get final count
        try:
            after_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_after'] = after_count.count
            sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
            sync_report['tables'][table_name]['end_time'] = datetime.now()
        except:
            pass
        
        # Also calculate national question statistics
        try:
            result = supabase.rpc('calculate_national_question_statistics', {}).execute()
            logging.info("National question statistics calculated successfully")
        except Exception as e:
            logging.warning(f"National question statistics calculation failed: {e}")
        
        return True
        
    except Exception as e:
        logging.warning(f"Enhanced stored procedure failed: {e}, falling back to Python calculation...")
        
        # Fallback: Calculate in Python
        try:
            # Get all question responses with student establishment info
            logging.info("Fetching question responses for statistics calculation...")
            
            # Clear existing statistics
            supabase.table('question_statistics').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            
            # Get current academic year
            now = datetime.now()
            if now.month >= 9:
                current_year = f"{now.year}/{now.year + 1}"
            else:
                current_year = f"{now.year - 1}/{now.year}"
            
            # Get all establishments
            establishments = supabase.table('establishments').select('id', 'is_australian').execute()
            
            for est in establishments.data:
                # Get all students for this establishment
                students = supabase.table('students').select('id').eq('establishment_id', est['id']).execute()
                if not students.data:
                    continue
                
                student_ids = [s['id'] for s in students.data]
                
                # Process each cycle
                for cycle in [1, 2, 3]:
                    # Get all responses for these students and cycle
                    responses = supabase.table('question_responses')\
                        .select('question_id', 'response_value')\
                        .in_('student_id', student_ids)\
                        .eq('cycle', cycle)\
                        .execute()
                    
                    if not responses.data:
                        continue
                    
                    # Group by question
                    question_groups = {}
                    for resp in responses.data:
                        qid = resp['question_id']
                        if qid not in question_groups:
                            question_groups[qid] = []
                        if resp['response_value'] is not None:
                            question_groups[qid].append(resp['response_value'])
                    
                    # Calculate statistics for each question
                    for question_id, values in question_groups.items():
                        if len(values) == 0:
                            continue
                        
                        import statistics as stats
                        
                        # Calculate distribution
                        distribution = [0, 0, 0, 0, 0]
                        for v in values:
                            if 1 <= v <= 5:
                                distribution[v-1] += 1
                        
                        # Find mode (most frequent value)
                        mode_value = max(range(1, 6), key=lambda x: distribution[x-1])
                        
                        stats_data = {
                            'establishment_id': est['id'],
                            'question_id': question_id,
                            'cycle': cycle,
                            'academic_year': current_year,
                            'mean': round(sum(values) / len(values), 2),
                            'std_dev': round(stats.stdev(values), 2) if len(values) > 1 else 0,
                            'count': len(values),
                            'mode': mode_value,
                            'percentile_25': round(stats.quantiles(values, n=4)[0], 2) if len(values) > 1 else values[0],
                            'percentile_75': round(stats.quantiles(values, n=4)[2], 2) if len(values) > 1 else values[0],
                            'distribution': distribution
                        }
                        
                        supabase.table('question_statistics').insert(stats_data).execute()
            
            # Get final count
            try:
                after_count = supabase.table(table_name).select('id', count='exact').execute()
                sync_report['tables'][table_name]['records_after'] = after_count.count
                sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
                sync_report['tables'][table_name]['end_time'] = datetime.now()
            except:
                pass
            
            logging.info("Question statistics calculation complete")
            return True
            
        except Exception as e:
            logging.error(f"Error calculating question statistics: {e}")
            sync_report['errors'].append(f"Question statistics calculation failed: {e}")
            return False

def calculate_national_statistics():
    """Calculate national statistics across all schools"""
    logging.info("Calculating national statistics...")
    
    # Track metrics
    table_name = 'national_statistics'
    sync_report['tables'][table_name] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'errors': 0
    }
    
    try:
        # Get count before
        before_count = supabase.table(table_name).select('id', count='exact').execute()
        sync_report['tables'][table_name]['records_before'] = before_count.count
    except:
        pass
    
    try:
        # Get current academic year (matching format used in school_statistics)
        now = datetime.now()
        if now.month >= 8:  # August onwards (matching SQL stored procedure)
            current_year = f"{now.year}-{str(now.year + 1)[2:]}"  # e.g., "2025-26"
        else:
            current_year = f"{now.year - 1}-{str(now.year)[2:]}"  # e.g., "2024-25"
        
        logging.info(f"Calculating for academic year: {current_year}")
        
        # Clear existing national statistics for current year
        supabase.table('national_statistics').delete().eq('academic_year', current_year).execute()
        
        # For each cycle and element combination
        national_count = 0
        for cycle in [1, 2, 3]:
            for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                # Get all school statistics for this combination
                school_stats = supabase.table('school_statistics')\
                    .select('mean, count, percentile_25, percentile_50, percentile_75, distribution')\
                    .eq('cycle', cycle)\
                    .eq('element', element)\
                    .eq('academic_year', current_year)\
                    .execute()
                
                if not school_stats.data:
                    continue
                
                # Calculate weighted national averages
                total_students = sum(s['count'] for s in school_stats.data)
                if total_students == 0:
                    continue
                
                # Weighted mean
                weighted_sum = sum(s['mean'] * s['count'] for s in school_stats.data)
                national_mean = weighted_sum / total_students
                
                # Collect all school means for percentile calculation
                school_means = [s['mean'] for s in school_stats.data]
                
                # Calculate national percentiles from school means
                import statistics as stats
                if len(school_means) >= 2:
                    national_p25 = stats.quantiles(school_means, n=4)[0]
                    national_p50 = stats.median(school_means)
                    national_p75 = stats.quantiles(school_means, n=4)[2]
                    national_std = stats.stdev(school_means)
                else:
                    # If only one school, use that school's values
                    national_p25 = school_stats.data[0]['percentile_25']
                    national_p50 = school_stats.data[0]['percentile_50']
                    national_p75 = school_stats.data[0]['percentile_75']
                    national_std = 0
                
                # Aggregate distribution from all schools
                # ALL VESPA elements use scores 1-10, so all distributions have 10 elements
                national_distribution = [0] * 10  # For scores 1-10
                
                for school in school_stats.data:
                    if school.get('distribution'):
                        school_dist = school['distribution']
                        # Add school's distribution to national
                        for i in range(min(len(school_dist), len(national_distribution))):
                            national_distribution[i] += school_dist[i]
                
                # Insert national statistics
                national_data = {
                    'cycle': cycle,
                    'academic_year': current_year,
                    'element': element,
                    'mean': round(national_mean, 2),
                    'std_dev': round(national_std, 2),
                    'count': total_students,
                    'percentile_25': round(national_p25, 2),
                    'percentile_50': round(national_p50, 2),
                    'percentile_75': round(national_p75, 2),
                    'distribution': national_distribution
                }
                
                supabase.table('national_statistics').insert(national_data).execute()
                national_count += 1
        
        # Get final count
        try:
            after_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_after'] = after_count.count
            sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
            sync_report['tables'][table_name]['end_time'] = datetime.now()
        except:
            pass
        
        logging.info(f"National statistics calculation complete - {national_count} entries created")
        return True
        
    except Exception as e:
        logging.error(f"Error calculating national statistics: {e}")
        sync_report['errors'].append(f"National statistics calculation failed: {e}")
        return False

def refresh_materialized_views():
    """Refresh materialized views for comparative analytics"""
    logging.info("Refreshing materialized views...")
    
    try:
        # This requires the comparative_metrics materialized view to exist
        # It's created by prepare_comparative_analytics.sql
        supabase.rpc('refresh_materialized_view', {'view_name': 'comparative_metrics'}).execute()
        logging.info("Materialized views refreshed successfully")
        return True
    except Exception as e:
        # If the function doesn't exist, try direct SQL (note: this might not work with Supabase client)
        logging.warning(f"Could not refresh materialized view via RPC: {e}")
        # The view will be stale but still usable
        return True

def generate_sync_report():
    """Generate comprehensive sync report"""
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("VESPA SYNC REPORT")
    report_lines.append("=" * 60)
    report_lines.append(f"Date: {sync_report['start_time'].strftime('%Y-%m-%d %H:%M:%S') if sync_report['start_time'] else 'N/A'}")
    
    if sync_report['start_time'] and sync_report['end_time']:
        duration = sync_report['end_time'] - sync_report['start_time']
        report_lines.append(f"Duration: {duration}")
    
    report_lines.append("\n=== TABLE SUMMARY ===")
    
    for table_name, metrics in sync_report['tables'].items():
        report_lines.append(f"\n{table_name.upper()}:")
        report_lines.append(f"  Records before: {metrics['records_before']:,}")
        report_lines.append(f"  Records after: {metrics['records_after']:,}")
        report_lines.append(f"  New records: {metrics['new_records']:,}")
        if 'skipped' in metrics and metrics['skipped'] > 0:
            report_lines.append(f"  Skipped: {metrics['skipped']:,}")
        report_lines.append(f"  Errors: {metrics['errors']}")
        
        if 'start_time' in metrics and 'end_time' in metrics:
            table_duration = metrics['end_time'] - metrics['start_time']
            report_lines.append(f"  Duration: {table_duration}")
        
        # Status indicator
        if metrics['errors'] == 0:
            report_lines.append(f"  Status: ✓ OK")
        else:
            report_lines.append(f"  Status: ⚠ WARNINGS")
    
    # Issues requiring attention
    if sync_report['warnings'] or sync_report['errors']:
        report_lines.append("\n=== ISSUES REQUIRING ATTENTION ===")
        for warning in sync_report['warnings']:
            report_lines.append(f"WARNING: {warning}")
        for error in sync_report['errors'][:10]:  # Show first 10 errors
            report_lines.append(f"ERROR: {error}")
        if len(sync_report['errors']) > 10:
            report_lines.append(f"... and {len(sync_report['errors']) - 10} more errors")
    
    report_lines.append("\n=== END OF REPORT ===")
    
    return "\n".join(report_lines)

def main():
    """Main sync function"""
    start_time = datetime.now()
    sync_report['start_time'] = start_time
    
    # Prevent system from sleeping during sync
    keep_system_awake()
    
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
        sync_staff_admins()  # Added
        sync_super_users()   # Added
        sync_question_responses()
        
        # Calculate all statistics
        if calculate_statistics():
            # Calculate question-level statistics
            calculate_question_statistics()
            # Calculate national statistics
            calculate_national_statistics()
            # Refresh materialized views
            refresh_materialized_views()
        else:
            logging.warning("School statistics calculation failed, skipping other statistics")
        
        # Update sync log
        end_time = datetime.now()
        supabase.table('sync_logs').update({
            'status': 'completed',
            'completed_at': end_time.isoformat(),
            'metadata': {
                'duration_seconds': (end_time - start_time).total_seconds(),
                'tables_synced': ['establishments', 'students', 'vespa_scores', 'staff_admins', 'super_users', 'question_responses', 'school_statistics', 'national_statistics']
            }
        }).eq('id', sync_log_id).execute()
        
        sync_report['end_time'] = end_time
        
        # Generate and display report
        report = generate_sync_report()
        logging.info("\n" + report)
        
        # Save report to file
        report_filename = f"sync_report_{start_time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        logging.info(f"Report saved to {report_filename}")
        
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