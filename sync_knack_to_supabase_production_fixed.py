#!/usr/bin/env python3
"""
PRODUCTION SYNC SCRIPT - FIXED VERSION
Incorporates the PROVEN approach for question_responses (clear first, then sync)
"""

import os
import time
import json
import requests
import logging
import signal
import pickle
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import platform

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

# API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Validate credentials
if not all([KNACK_APP_ID, KNACK_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables. Check your .env file.")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Knack API configuration
KNACK_API_URL = 'https://api.knack.com/v1'
KNACK_HEADERS = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

# Object keys mapping
OBJECT_KEYS = {
    'establishments': 'object_2',
    'vespa_results': 'object_10',
    'psychometric': 'object_29',
    'staff_admins': 'object_5',
    'super_users': 'object_21'
}

# Batch sizes for efficient processing
BATCH_SIZES = {
    'establishments': 50,
    'students': 100,
    'vespa_scores': 200,
    'question_responses': 1000,  # Proven to work
    'staff_admins': 50,
    'super_users': 50
}

# Load question mapping
try:
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        question_mapping = json.load(f)
except FileNotFoundError:
    logging.error("psychometric_question_details.json not found!")
    question_mapping = []

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    global shutdown_requested
    logging.info("Shutdown signal received. Finishing current batch...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)

def keep_system_awake():
    """Prevent system from sleeping during sync"""
    if platform.system() == 'Windows':
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        logging.info("System sleep prevention enabled (Windows)")
    elif platform.system() == 'Darwin':  # macOS
        os.system("caffeinate -d &")
        logging.info("System sleep prevention enabled (macOS)")
    else:  # Linux
        logging.info("System sleep prevention not implemented for this OS")

def make_knack_request(object_key: str, page: int = 1, filters: Optional[List[Dict]] = None) -> Dict:
    """Make a request to Knack API with retry logic"""
    max_retries = 3
    base_wait = 2
    
    url = f"{KNACK_API_URL}/objects/{object_key}/records"
    params = {'page': page, 'rows_per_page': 500}
    
    if filters:
        params['filters'] = json.dumps({"match": "and", "rules": filters})
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=KNACK_HEADERS, params=params)
            
            if response.status_code == 429:  # Rate limit
                wait_time = base_wait * (2 ** attempt)
                logging.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to fetch {object_key} page {page} after {max_retries} attempts: {e}")
                raise
            time.sleep(base_wait * (2 ** attempt))
    
    return {'records': [], 'total_pages': 0}

def fetch_all_knack_records(object_key: str, filters: Optional[List[Dict]] = None) -> List[Dict]:
    """Fetch all records from a Knack object with pagination"""
    all_records = []
    page = 1
    
    while True:
        logging.info(f"Fetching {object_key} page {page}...")
        data = make_knack_request(object_key, page, filters)
        
        records = data.get('records', [])
        if not records:
            break
            
        all_records.extend(records)
        
        if page == 1:
            total_pages = data.get('total_pages', 1)
            logging.info(f"Total pages for {object_key}: {total_pages}")
        
        page += 1
        time.sleep(0.5)  # Rate limiting
        
    logging.info(f"Fetched {len(all_records)} records from {object_key}")
    return all_records

def batch_upsert_with_retry(table: str, data: List[Dict], on_conflict: str) -> bool:
    """Perform batch upsert with retry logic"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            result = supabase.table(table).upsert(data, on_conflict=on_conflict).execute()
            return True
        except Exception as e:
            logging.error(f"Batch upsert error on {table} (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logging.error(f"Failed to upsert batch to {table} after {max_retries} attempts")
                return False
            time.sleep(2 ** attempt)
    
    return False

def calculate_academic_year(date_str: str, establishment_id: str, is_australian: bool) -> str:
    """Calculate academic year based on date and location"""
    if not date_str:
        return str(datetime.now().year)
    
    try:
        if isinstance(date_str, str) and '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                date_obj = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                date_obj = datetime.now()
        else:
            date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
        
        if is_australian:
            return str(date_obj.year) if date_obj.month >= 1 else str(date_obj.year - 1)
        else:
            return str(date_obj.year) if date_obj.month >= 9 else str(date_obj.year - 1)
    except Exception as e:
        logging.error(f"Error parsing date {date_str}: {e}")
        return str(datetime.now().year)

def format_date_for_postgres(date_str: str) -> Optional[str]:
    """Convert UK date format (DD/MM/YYYY) to PostgreSQL format (YYYY-MM-DD)"""
    if not date_str or not isinstance(date_str, str) or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            logging.warning(f"Unable to parse date: {date_str}")
            return None

def extract_email_from_html(html_or_email: str) -> str:
    """Extract plain email from HTML anchor tag or return as-is"""
    if not html_or_email:
        return ""
    
    if '<a href="mailto:' in html_or_email:
        import re
        match = re.search(r'mailto:([^"]+)"', html_or_email)
        if match:
            return match.group(1)
    
    return html_or_email

def sync_establishments():
    """Sync establishments (schools) from Knack to Supabase"""
    logging.info("Syncing establishments...")
    
    # Get ALL establishments (no filter to ensure Belfast Met etc. are included)
    establishments = fetch_all_knack_records(OBJECT_KEYS['establishments'])
    
    batch = []
    for est in establishments:
        try:
            est_name = est.get('field_44') or est.get('field_44_raw') or ""
            if not est_name or est_name == "EMPTY":
                est_name = est.get('field_11') or est.get('identifier') or f"Establishment {est['id'][:8]}"
            
            establishment_data = {
                'knack_id': est['id'],
                'name': est_name,
                'status': est.get('field_2209', 'Active'),
                'is_australian': est.get('field_2300') == 'Australia',
                'created_at': est.get('field_2', '')
            }
            
            batch.append(establishment_data)
            
            if len(batch) >= BATCH_SIZES['establishments']:
                batch_upsert_with_retry('establishments', batch, 'knack_id')
                batch = []
                
        except Exception as e:
            logging.error(f"Error processing establishment {est.get('id')}: {e}")
    
    if batch:
        batch_upsert_with_retry('establishments', batch, 'knack_id')
    
    logging.info(f"Synced {len(establishments)} establishments")

def sync_students_and_vespa_scores():
    """Sync students and VESPA scores with batch processing"""
    logging.info("Syncing students and VESPA scores...")
    
    # Get establishment mapping
    establishments = supabase.table('establishments').select('id', 'knack_id', 'is_australian').execute()
    est_map = {e['knack_id']: {'id': e['id'], 'is_australian': e.get('is_australian', False)} for e in establishments.data}
    
    student_batch = []
    vespa_batch = []
    student_knack_to_id = {}
    
    # Load existing student mappings
    logging.info("Loading existing student mappings...")
    offset = 0
    limit = 1000
    while True:
        existing = supabase.table('students').select('id', 'knack_id').range(offset, offset + limit - 1).execute()
        if not existing.data:
            break
        for student in existing.data:
            student_knack_to_id[student['knack_id']] = student['id']
        if len(existing.data) < limit:
            break
        offset += limit
    logging.info(f"Loaded {len(student_knack_to_id)} existing student mappings")
    
    # Process VESPA records
    page = 1
    students_processed = set()
    scores_synced = 0
    
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
                    if isinstance(email_value, dict):
                        student_email = email_value.get('address', '') or email_value.get('email', '') or str(email_value)
                    else:
                        student_email = str(email_value) if email_value else ''
                elif isinstance(email_field, str):
                    student_email = email_field
                else:
                    student_email = ''
                
                if not student_email or not isinstance(student_email, str) or student_email == '{}':
                    continue
                
                # Get establishment info
                est_field = record.get('field_133_raw', [])
                est_knack_id = None
                if est_field and isinstance(est_field, list) and len(est_field) > 0:
                    est_item = est_field[0]
                    if isinstance(est_item, dict):
                        est_knack_id = est_item.get('id') or est_item.get('value')
                    else:
                        est_knack_id = est_item
                
                est_info = est_map.get(est_knack_id, {})
                establishment_id = est_info.get('id')
                is_australian = est_info.get('is_australian', False)
                
                # Create/update student if not already processed
                if student_email not in students_processed and record['id'] not in student_knack_to_id:
                    name_field = record.get('field_187_raw', '')
                    if isinstance(name_field, dict):
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
                        'group': record.get('field_223', ''),
                        'year_group': record.get('field_144', ''),
                        'course': record.get('field_2299', ''),
                        'faculty': record.get('field_782', '')
                    }
                    
                    student_batch.append(student_data)
                    students_processed.add(student_email)
                
                # Process VESPA scores for each cycle
                for cycle in [1, 2, 3]:
                    field_offset = (cycle - 1) * 6
                    vision_field = f'field_{155 + field_offset}_raw'
                    
                    if record.get(vision_field) is not None:
                        def clean_score(value):
                            if value == "" or value is None:
                                return None
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return None
                        
                        completion_date = format_date_for_postgres(record.get('field_855'))
                        
                        vespa_data = {
                            'student_knack_id': record['id'],
                            'cycle': cycle,
                            'vision': clean_score(record.get(f'field_{155 + field_offset}_raw')),
                            'effort': clean_score(record.get(f'field_{156 + field_offset}_raw')),
                            'systems': clean_score(record.get(f'field_{157 + field_offset}_raw')),
                            'practice': clean_score(record.get(f'field_{158 + field_offset}_raw')),
                            'attitude': clean_score(record.get(f'field_{159 + field_offset}_raw')),
                            'overall': clean_score(record.get(f'field_{160 + field_offset}_raw')),
                            'completion_date': completion_date,
                            'academic_year': calculate_academic_year(
                                record.get('field_855'),
                                establishment_id,
                                is_australian
                            )
                        }
                        
                        vespa_batch.append(vespa_data)
                        
            except Exception as e:
                logging.error(f"Error processing VESPA record {record.get('id')}: {e}")
        
        # Batch upsert students
        if len(student_batch) >= BATCH_SIZES['students']:
            logging.info(f"Upserting batch of {len(student_batch)} students...")
            if batch_upsert_with_retry('students', student_batch, 'knack_id'):
                # Update mapping - get all IDs in chunks to avoid query limits
                knack_ids = [s['knack_id'] for s in student_batch]
                
                # Process in chunks of 50 to avoid query size limits
                for i in range(0, len(knack_ids), 50):
                    chunk = knack_ids[i:i+50]
                    try:
                        results = supabase.table('students').select('id,knack_id').in_('knack_id', chunk).execute()
                        for student in results.data:
                            student_knack_to_id[student['knack_id']] = student['id']
                    except Exception as e:
                        logging.error(f"Error fetching student IDs for chunk: {e}")
            student_batch = []
        
        # Process vespa scores batch
        if len(vespa_batch) >= BATCH_SIZES['vespa_scores']:
            logging.info(f"Processing batch of {len(vespa_batch)} VESPA scores...")
            valid_scores = []
            for score in vespa_batch:
                student_id = student_knack_to_id.get(score['student_knack_id'])
                if student_id:
                    score['student_id'] = student_id
                    del score['student_knack_id']
                    valid_scores.append(score)
            
            if valid_scores:
                if batch_upsert_with_retry('vespa_scores', valid_scores, 'student_id,cycle'):
                    scores_synced += len(valid_scores)
            vespa_batch = []
        
        page += 1
        time.sleep(0.5)
    
    # Process remaining batches
    if student_batch:
        logging.info(f"Upserting final batch of {len(student_batch)} students...")
        if batch_upsert_with_retry('students', student_batch, 'knack_id'):
            knack_ids = [s['knack_id'] for s in student_batch]
            for i in range(0, len(knack_ids), 50):
                chunk = knack_ids[i:i+50]
                try:
                    results = supabase.table('students').select('id,knack_id').in_('knack_id', chunk).execute()
                    for student in results.data:
                        student_knack_to_id[student['knack_id']] = student['id']
                except Exception as e:
                    logging.error(f"Error fetching student IDs for chunk: {e}")
    
    if vespa_batch:
        logging.info(f"Processing final batch of {len(vespa_batch)} VESPA scores...")
        valid_scores = []
        for score in vespa_batch:
            student_id = student_knack_to_id.get(score['student_knack_id'])
            if student_id:
                score['student_id'] = student_id
                del score['student_knack_id']
                valid_scores.append(score)
        
        if valid_scores:
            if batch_upsert_with_retry('vespa_scores', valid_scores, 'student_id,cycle'):
                scores_synced += len(valid_scores)
    
    logging.info(f"Synced {len(students_processed)} students and {scores_synced} VESPA scores")

def sync_question_responses():
    """Sync psychometric question responses - USING PROVEN APPROACH"""
    logging.info("Syncing question responses...")
    
    # CRITICAL: Clear existing question responses first (this is what works!)
    logging.info("Clearing existing question responses to avoid conflicts...")
    try:
        supabase.table('question_responses').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        logging.info("✅ Cleared existing question responses")
    except Exception as e:
        logging.error(f"Failed to clear question responses: {e}")
        # Continue anyway - upsert will handle conflicts
    
    # Load student mapping
    logging.info("Loading student mappings...")
    student_map = {}
    offset = 0
    limit = 1000
    
    while True:
        students = supabase.table('students').select('id', 'knack_id').range(offset, offset + limit - 1).execute()
        
        for student in students.data:
            student_map[student['knack_id']] = student['id']
        
        logging.info(f"  Loaded batch at offset {offset}: {len(students.data)} students")
        
        if len(students.data) < limit:
            break
        offset += limit
    
    logging.info(f"Total loaded: {len(student_map)} student mappings")
    
    response_batch = []
    responses_synced = 0
    
    # Process in batches
    page = 1
    while True:
        if shutdown_requested:
            logging.info("Shutdown requested, stopping question sync...")
            break
            
        logging.info(f"Processing psychometric records page {page}...")
        data = make_knack_request(OBJECT_KEYS['psychometric'], page=page)
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                # Get Object_10 connection via field_792
                object_10_field = record.get('field_792_raw', [])
                object_10_knack_id = None
                if object_10_field and isinstance(object_10_field, list) and len(object_10_field) > 0:
                    object_10_item = object_10_field[0]
                    if isinstance(object_10_item, dict):
                        object_10_knack_id = object_10_item.get('id') or object_10_item.get('value')
                    else:
                        object_10_knack_id = object_10_item
                
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
                            
                            if response_value not in [None, '', []]:
                                try:
                                    response_int = int(response_value)
                                    
                                    response_data = {
                                        'student_id': student_id,
                                        'cycle': cycle,
                                        'question_id': str(q_detail['questionId']),
                                        'response_value': response_int,
                                        'question_text': q_detail['questionText']
                                    }
                                    
                                    response_batch.append(response_data)
                                    
                                except (ValueError, TypeError):
                                    pass
                                    
            except Exception as e:
                logging.error(f"Error processing psychometric record {record.get('id')}: {e}")
        
        # Batch upsert responses
        if len(response_batch) >= BATCH_SIZES['question_responses']:
            logging.info(f"Upserting batch of {len(response_batch)} question responses...")
            if batch_upsert_with_retry('question_responses', response_batch, 'student_id,cycle,question_id'):
                responses_synced += len(response_batch)
            response_batch = []
        
        page += 1
        time.sleep(0.5)
    
    # Process remaining
    if response_batch:
        logging.info(f"Upserting final batch of {len(response_batch)} question responses...")
        if batch_upsert_with_retry('question_responses', response_batch, 'student_id,cycle,question_id'):
            responses_synced += len(response_batch)
    
    logging.info(f"Synced {responses_synced} question responses")

def sync_staff_admins():
    """Sync staff admins from Knack to Supabase"""
    logging.info("Syncing staff admins...")
    
    staff = fetch_all_knack_records(OBJECT_KEYS['staff_admins'])
    
    batch = []
    for member in staff:
        try:
            email_raw = member.get('field_24') or member.get('field_24_raw', '')
            email = extract_email_from_html(email_raw)
            
            if email:
                staff_data = {
                    'knack_id': member['id'],
                    'email': extract_email_from_html(email_raw),
                    'name': member.get('field_23', ''),
                    'establishment_name': member.get('field_205', ''),
                    'created_at': member.get('field_25', '')
                }
                
                batch.append(staff_data)
                
                if len(batch) >= BATCH_SIZES['staff_admins']:
                    batch_upsert_with_retry('staff_admins', batch, 'knack_id')
                    batch = []
                    
        except Exception as e:
            logging.error(f"Error processing staff admin {member.get('id')}: {e}")
    
    if batch:
        batch_upsert_with_retry('staff_admins', batch, 'knack_id')
    
    logging.info(f"Synced {len(staff)} staff admins")

def sync_super_users():
    """Sync super users from Knack to Supabase"""
    logging.info("Syncing super users...")
    
    users = fetch_all_knack_records(OBJECT_KEYS['super_users'])
    
    batch = []
    for user in users:
        try:
            email_raw = user.get('field_234') or user.get('field_234_raw', '')
            email = extract_email_from_html(email_raw)
            
            if email:
                user_data = {
                    'knack_id': user['id'],
                    'email': extract_email_from_html(email_raw),
                    'name': user.get('field_233', ''),
                    'created_at': user.get('field_235', '')
                }
                
                batch.append(user_data)
                
                if len(batch) >= BATCH_SIZES['super_users']:
                    batch_upsert_with_retry('super_users', batch, 'knack_id')
                    batch = []
                    
        except Exception as e:
            logging.error(f"Error processing super user {user.get('id')}: {e}")
    
    if batch:
        batch_upsert_with_retry('super_users', batch, 'knack_id')
    
    logging.info(f"Synced {len(users)} super users")

def calculate_statistics():
    """Calculate and store statistics"""
    logging.info("Calculating statistics...")
    
    try:
        # Try to use the stored procedure
        result = supabase.rpc('calculate_all_statistics').execute()
        logging.info("Statistics calculated successfully using stored procedure")
        return True
    except Exception as e:
        logging.warning(f"Stored procedure failed: {e}, falling back to manual calculation...")
        
        # Manual calculation fallback
        try:
            # Get all establishments
            establishments = supabase.table('establishments').select('*').execute()
            
            for est in establishments.data:
                est_id = est['id']
                
                # Get students for this establishment
                students = supabase.table('students').select('id').eq('establishment_id', est_id).execute()
                
                if not students.data:
                    continue
                    
                student_ids = [s['id'] for s in students.data]
                
                # Calculate statistics for each cycle and element
                for cycle in [1, 2, 3]:
                    # Process in chunks to avoid query limits
                    for i in range(0, len(student_ids), 200):
                        chunk_ids = student_ids[i:i+200]
                        
                        # Get all scores for this cycle
                        scores = supabase.table('vespa_scores')\
                            .select('vision, effort, systems, practice, attitude, overall')\
                            .in_('student_id', chunk_ids)\
                            .eq('cycle', cycle)\
                            .execute()
                        
                        if not scores.data:
                            continue
                        
                        # Calculate stats for each element
                        for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                            values = [s[element] for s in scores.data if s[element] is not None]
                            
                            if values:
                                mean = sum(values) / len(values)
                                variance = sum((x - mean) ** 2 for x in values) / len(values)
                                std_dev = variance ** 0.5
                                
                                stats_data = {
                                    'establishment_id': est_id,
                                    'cycle': cycle,
                                    'element': element,
                                    'mean': round(mean, 2),
                                    'std_dev': round(std_dev, 2),
                                    'count': len(values),
                                    'academic_year': str(datetime.now().year)
                                }
                                
                                supabase.table('school_statistics').upsert(
                                    stats_data,
                                    on_conflict='establishment_id,cycle,academic_year,element'
                                ).execute()
            
            logging.info("Statistics calculated successfully using manual method")
            return True
            
        except Exception as e:
            logging.error(f"Failed to calculate statistics: {e}")
            return False

def main():
    """Main sync function"""
    start_time = datetime.now()
    
    # Create sync log
    sync_log = {
        'sync_type': 'full_sync',
        'started_at': start_time.isoformat(),
        'status': 'running',
        'records_processed': 0
    }
    
    log_result = supabase.table('sync_logs').insert(sync_log).execute()
    log_id = log_result.data[0]['id'] if log_result.data else None
    
    try:
        # Keep system awake
        keep_system_awake()
        
        # Run sync operations
        sync_establishments()
        sync_students_and_vespa_scores()
        sync_question_responses()  # Now uses the PROVEN approach
        sync_staff_admins()
        sync_super_users()
        calculate_statistics()
        
        # Update sync log
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if log_id:
            supabase.table('sync_logs').update({
                'completed_at': end_time.isoformat(),
                'status': 'completed',
                'metadata': {
                    'duration_seconds': duration,
                    'completed': 'all_syncs'
                }
            }).eq('id', log_id).execute()
        
        logging.info(f"Sync completed successfully in {duration:.2f} seconds")
        
    except Exception as e:
        logging.error(f"Sync failed: {e}")
        
        if log_id:
            supabase.table('sync_logs').update({
                'completed_at': datetime.now().isoformat(),
                'status': 'failed',
                'error_message': str(e)
            }).eq('id', log_id).execute()
        
        raise

if __name__ == "__main__":
    main()