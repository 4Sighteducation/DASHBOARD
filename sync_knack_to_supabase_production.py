#!/usr/bin/env python3
"""
Production-ready sync script to migrate data from Knack to Supabase
Includes batch processing, all tables, and proper error handling
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
from pathlib import Path
import signal
from typing import List, Dict, Any, Optional

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

# Knack field mappings
OBJECT_KEYS = {
    'establishments': 'object_2',
    'vespa_results': 'object_10',
    'psychometric': 'object_29',
    'staff_admins': 'object_5',
    'super_users': 'object_21',
    'academy_trusts': 'object_134'
}

# Batch sizes for efficient processing
BATCH_SIZES = {
    'establishments': 50,
    'students': 100,
    'vespa_scores': 200,
    'question_responses': 1000,  # Increased to match optimized version that worked
    'staff_admins': 50,
    'super_users': 50
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
        if shutdown_requested:
            logging.info("Shutdown requested during fetch")
            break
            
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

def batch_upsert_with_retry(table: str, data: List[Dict], on_conflict: str, max_retries: int = 3) -> bool:
    """Batch upsert with retry logic"""
    for attempt in range(max_retries):
        try:
            if data:
                result = supabase.table(table).upsert(data, on_conflict=on_conflict).execute()
                return True
        except Exception as e:
            logging.error(f"Batch upsert attempt {attempt + 1} failed for {table}: {e}")
            if attempt == max_retries - 1:
                # Try smaller batches on final attempt
                logging.info(f"Trying smaller batches for {table}")
                for i in range(0, len(data), 10):
                    small_batch = data[i:i+10]
                    try:
                        supabase.table(table).upsert(small_batch, on_conflict=on_conflict).execute()
                    except Exception as batch_error:
                        logging.error(f"Small batch failed: {batch_error}")
                        return False
            time.sleep(1)
    return False

def format_date_for_postgres(date_str: str) -> Optional[str]:
    """Convert UK date format to ISO format for PostgreSQL"""
    if not date_str or not date_str.strip():
        return None
    try:
        # Parse UK format DD/MM/YYYY and convert to YYYY-MM-DD
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        logging.warning(f"Invalid date format: {date_str}")
        return None

def extract_email_from_html(html_or_email: str) -> str:
    """Extract email address from HTML anchor tag or return as-is if plain email"""
    if not html_or_email:
        return ''
    
    # If it starts with <a href, extract the email
    if '<a href="mailto:' in html_or_email:
        # Extract email between mailto: and "
        match = re.search(r'mailto:([^"]+)"', html_or_email)
        if match:
            return match.group(1)
    
    # Otherwise assume it's already a plain email
    return html_or_email.strip()

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
    
    batch = []
    for est in establishments:
        try:
            # Map Knack fields to Supabase schema
            est_name = est.get('field_44') or est.get('field_44_raw') or ""
            if not est_name or est_name == "EMPTY":
                est_name = est.get('field_11') or est.get('identifier') or f"Establishment {est['id'][:8]}"
            
            establishment_data = {
                'knack_id': est['id'],
                'name': est_name,
                'is_australian': est.get('field_3573_raw', '') == 'True'
            }
            
            batch.append(establishment_data)
            
            if len(batch) >= BATCH_SIZES['establishments']:
                batch_upsert_with_retry('establishments', batch, 'knack_id')
                batch = []
                
        except Exception as e:
            logging.error(f"Error processing establishment {est.get('id')}: {e}")
    
    # Process remaining
    if batch:
        batch_upsert_with_retry('establishments', batch, 'knack_id')
    
    logging.info(f"Synced {len(establishments)} establishments")

def sync_students_and_vespa_scores():
    """Sync students and VESPA scores with batch processing"""
    logging.info("Syncing students and VESPA scores...")
    
    # Get establishment mapping - cache this for efficiency
    establishments = supabase.table('establishments').select('id', 'knack_id', 'is_australian').execute()
    est_map = {e['knack_id']: {'id': e['id'], 'is_australian': e.get('is_australian', False)} for e in establishments.data}
    
    student_batch = []
    vespa_batch = []
    student_knack_to_id = {}
    
    # First, get existing student mappings
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
                            'student_knack_id': record['id'],  # Will be converted to student_id later
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
                        # Update the mapping
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
        time.sleep(0.5)  # Rate limiting
    
    # Process remaining batches
    if student_batch:
        logging.info(f"Upserting final batch of {len(student_batch)} students...")
        if batch_upsert_with_retry('students', student_batch, 'knack_id'):
            # Get all IDs in chunks to avoid query limits
            knack_ids = [s['knack_id'] for s in student_batch]
            
            # Process in chunks of 50 to avoid query size limits
            for i in range(0, len(knack_ids), 50):
                chunk = knack_ids[i:i+50]
                try:
                    results = supabase.table('students').select('id,knack_id').in_('knack_id', chunk).execute()
                    # Update the mapping
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

def sync_staff_admins():
    """Sync staff admins from object_5 with batch processing"""
    logging.info("Syncing staff admins...")
    
    try:
        staff_admins = fetch_all_knack_records(OBJECT_KEYS['staff_admins'])
        
        batch = []
        count = 0
        for admin in staff_admins:
            try:
                # Extract email from HTML if needed
                email_raw = admin.get('field_86', '') or admin.get('field_86_raw', '')
                
                admin_data = {
                    'knack_id': admin['id'],
                    'email': extract_email_from_html(email_raw),
                    'name': admin.get('field_85', '') or admin.get('field_85_raw', '')
                }
                
                if admin_data['email']:
                    batch.append(admin_data)
                    count += 1
                
                if len(batch) >= BATCH_SIZES['staff_admins']:
                    batch_upsert_with_retry('staff_admins', batch, 'knack_id')
                    batch = []
                    
            except Exception as e:
                logging.error(f"Error processing staff admin {admin.get('id')}: {e}")
        
        # Process remaining
        if batch:
            batch_upsert_with_retry('staff_admins', batch, 'knack_id')
        
        logging.info(f"Synced {count} staff admins")
        
    except Exception as e:
        logging.error(f"Failed to sync staff admins: {e}")

def sync_super_users():
    """Sync super users from object_21 with batch processing"""
    logging.info("Syncing super users...")
    
    try:
        super_users = fetch_all_knack_records(OBJECT_KEYS['super_users'])
        
        batch = []
        count = 0
        for user in super_users:
            try:
                # Extract email from HTML if needed
                email_raw = user.get('field_86', '') or user.get('field_86_raw', '')
                
                user_data = {
                    'knack_id': user['id'],
                    'email': extract_email_from_html(email_raw),
                    'name': user.get('field_85', '') or user.get('field_85_raw', '')
                }
                
                if user_data['email']:
                    batch.append(user_data)
                    count += 1
                
                if len(batch) >= BATCH_SIZES['super_users']:
                    batch_upsert_with_retry('super_users', batch, 'knack_id')
                    batch = []
                    
            except Exception as e:
                logging.error(f"Error processing super user {user.get('id')}: {e}")
        
        # Process remaining
        if batch:
            batch_upsert_with_retry('super_users', batch, 'knack_id')
        
        logging.info(f"Synced {count} super users")
        
    except Exception as e:
        logging.error(f"Failed to sync super users: {e}")

def sync_question_responses():
    """Sync psychometric question responses with batch processing"""
    logging.info("Syncing question responses...")
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        question_mapping = json.load(f)
    
    # Get ALL student mappings
    logging.info("Loading all students for mapping...")
    student_map = {}
    offset = 0
    limit = 1000
    while True:
        students = supabase.table('students').select('id', 'knack_id').range(offset, offset + limit - 1).execute()
        if not students.data:
            break
        
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
        time.sleep(0.5)  # Rate limiting
    
    # Process remaining
    if response_batch:
        logging.info(f"Upserting final batch of {len(response_batch)} question responses...")
        if batch_upsert_with_retry('question_responses', response_batch, 'student_id,cycle,question_id'):
            responses_synced += len(response_batch)
    
    logging.info(f"Synced {responses_synced} question responses")

def calculate_academic_year(date_str, establishment_id=None, is_australian=None):
    """Calculate academic year based on date and establishment location"""
    if not date_str:
        return None
    
    try:
        # Parse date (Knack format: DD/MM/YYYY - UK format)
        date = datetime.strptime(date_str, '%d/%m/%Y')
        
        # Use provided is_australian value, or default to False
        if is_australian is None:
            is_australian = False
        
        if is_australian:
            # Australian: Calendar year
            return str(date.year)
        else:
            # UK: Academic year (Sept-Aug)
            if date.month >= 9:
                return f"{date.year}/{date.year + 1}"
            else:
                return f"{date.year - 1}/{date.year}"
                
    except Exception as e:
        logging.error(f"Error calculating academic year: {e}")
        return None

def calculate_statistics():
    """Calculate and store statistics for schools"""
    logging.info("Calculating statistics...")
    
    try:
        # Try to use the stored procedure first
        result = supabase.rpc('calculate_all_statistics', {}).execute()
        logging.info("Statistics calculated successfully using stored procedure")
        return
    except Exception as e:
        logging.warning(f"Stored procedure failed: {e}, falling back to manual calculation...")
    
    # Manual calculation fallback
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
                        stats_data = {
                            'establishment_id': est['id'],
                            'cycle': cycle,
                            'academic_year': current_year,
                            'element': element,
                            'mean': sum(values) / len(values),
                            'std_dev': stats.stdev(values) if len(values) > 1 else 0,
                            'count': len(values),
                            'percentile_25': stats.quantiles(values, n=4)[0] if len(values) > 1 else values[0],
                            'percentile_50': stats.median(values),
                            'percentile_75': stats.quantiles(values, n=4)[2] if len(values) > 1 else values[0],
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
        if not shutdown_requested:
            sync_establishments()
        
        if not shutdown_requested:
            sync_students_and_vespa_scores()
        
        if not shutdown_requested:
            sync_staff_admins()
        
        if not shutdown_requested:
            sync_super_users()
        
        if not shutdown_requested:
            sync_question_responses()
        
        if not shutdown_requested:
            calculate_statistics()
        
        # Update sync log
        end_time = datetime.now()
        status = 'interrupted' if shutdown_requested else 'completed'
        
        supabase.table('sync_logs').update({
            'status': status,
            'completed_at': end_time.isoformat(),
            'metadata': {
                'duration_seconds': (end_time - start_time).total_seconds(),
                'interrupted': shutdown_requested
            }
        }).eq('id', sync_log_id).execute()
        
        logging.info(f"Sync {status} in {end_time - start_time}")
        
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