#!/usr/bin/env python3
"""
Optimized sync script to migrate data from Knack to Supabase
Features:
- Batch processing to prevent timeouts
- Resume capability from checkpoints
- System sleep prevention
- Graceful shutdown handling
- Optimized database queries
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
from typing import List, Dict, Any, Optional, Set

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
    'staff_admins': 'object_3',
    'academy_trusts': 'object_134'
}

# Checkpoint file for resume capability
CHECKPOINT_FILE = Path('sync_checkpoint.pkl')

# Batch sizes for efficient processing
BATCH_SIZES = {
    'establishments': 50,
    'students': 100,
    'vespa_scores': 500,  # Increased for better performance
    'question_responses': 1000
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
        self.total_students = 0
        self.total_vespa_scores = 0
        self.total_responses = 0
    
    def save(self):
        """Save checkpoint to disk"""
        try:
            with open(CHECKPOINT_FILE, 'wb') as f:
                pickle.dump(self, f)
            logging.info(f"Checkpoint saved: Page {self.vespa_page}, {len(self.students_processed)} students processed")
        except Exception as e:
            logging.error(f"Failed to save checkpoint: {e}")
    
    @classmethod
    def load(cls):
        """Load checkpoint from disk"""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, 'rb') as f:
                    checkpoint = pickle.load(f)
                logging.info(f"Checkpoint loaded: Page {checkpoint.vespa_page}, {len(checkpoint.students_processed)} students processed")
                return checkpoint
            except Exception as e:
                logging.error(f"Failed to load checkpoint: {e}")
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
            logging.info("System sleep prevention enabled (Windows)")
    except Exception as e:
        logging.warning(f"Could not prevent system sleep: {e}")

def restore_system_sleep():
    """Restore normal system sleep behavior"""
    try:
        import ctypes
        if sys.platform == 'win32':
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            logging.info("System sleep prevention disabled")
    except Exception:
        pass

def make_knack_request(object_key: str, page: int = 1, rows_per_page: int = 1000, filters: Optional[List] = None) -> Dict:
    """Make a request to Knack API with better error handling"""
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
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logging.warning(f"Request timeout on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise
        except Exception as e:
            logging.error(f"Knack API error: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise

def batch_upsert_with_retry(table: str, data: List[Dict], on_conflict: str, max_retries: int = 3) -> bool:
    """Batch upsert with retry logic"""
    for attempt in range(max_retries):
        try:
            if data:  # Only upsert if there's data
                result = supabase.table(table).upsert(data, on_conflict=on_conflict).execute()
                return True
        except Exception as e:
            logging.error(f"Batch upsert error on {table} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                # If batch fails, try individual inserts
                logging.info(f"Falling back to individual inserts for {table}")
                success_count = 0
                for item in data:
                    try:
                        supabase.table(table).upsert(item, on_conflict=on_conflict).execute()
                        success_count += 1
                    except Exception as item_error:
                        logging.error(f"Individual insert failed for {table}: {item_error}")
                logging.info(f"Individual inserts: {success_count}/{len(data)} successful")
                return success_count > 0
    return False

def fetch_all_knack_records(object_key: str, filters: Optional[List] = None) -> List[Dict]:
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

def sync_establishments(checkpoint: SyncCheckpoint) -> bool:
    """Sync establishments with batch processing"""
    if checkpoint.establishments_synced:
        logging.info("Establishments already synced, skipping...")
        return True
        
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
    
    # Process in batches
    batch = []
    for est in establishments:
        if shutdown_requested:
            return False
            
        try:
            # Map Knack fields to Supabase schema
            est_name = est.get('field_44') or est.get('field_44_raw') or ""
            if not est_name or est_name == "EMPTY":
                est_name = est.get('field_11') or est.get('identifier') or f"Establishment {est['id'][:8]}"
            
            establishment_data = {
                'knack_id': est['id'],
                'name': est_name,
                'is_australian': est.get('field_3508_raw', False) == 'true'
            }
            
            batch.append(establishment_data)
            
            # Upsert batch when it reaches the batch size
            if len(batch) >= BATCH_SIZES['establishments']:
                batch_upsert_with_retry('establishments', batch, 'knack_id')
                batch = []
                
        except Exception as e:
            logging.error(f"Error processing establishment {est.get('id')}: {e}")
    
    # Upsert remaining batch
    if batch:
        batch_upsert_with_retry('establishments', batch, 'knack_id')
    
    checkpoint.establishments_synced = True
    checkpoint.save()
    logging.info(f"Synced {len(establishments)} establishments")
    return True

def calculate_academic_year(date_str: str, is_australian: bool = False) -> Optional[str]:
    """Calculate academic year based on date and establishment location"""
    if not date_str:
        return None
    
    try:
        # Parse date (Knack format: DD/MM/YYYY - UK format)
        date = datetime.strptime(date_str, '%d/%m/%Y')
        
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
        logging.error(f"Error calculating academic year for {date_str}: {e}")
        return None

def sync_students_and_vespa_scores(checkpoint: SyncCheckpoint) -> bool:
    """Sync students and VESPA scores with optimized batch processing"""
    logging.info("Syncing students and VESPA scores...")
    
    # Get establishment mapping - cache this for efficiency
    establishments = supabase.table('establishments').select('id', 'knack_id', 'is_australian').execute()
    est_map = {e['knack_id']: {'id': e['id'], 'is_australian': e['is_australian']} for e in establishments.data}
    
    # Load checkpoint data
    page = checkpoint.vespa_page
    students_processed = checkpoint.students_processed
    
    if page > 1:
        logging.info(f"Resuming from page {page}, {len(students_processed)} students already processed")
    
    student_batch = []
    vespa_batch = []
    student_knack_to_id = {}
    
    # First, get existing student mappings to avoid duplicates
    existing_students = supabase.table('students').select('id', 'knack_id').execute()
    for student in existing_students.data:
        student_knack_to_id[student['knack_id']] = student['id']
    
    while True:
        if shutdown_requested:
            logging.info("Shutdown requested, saving progress...")
            checkpoint.vespa_page = page
            checkpoint.students_processed = students_processed
            checkpoint.save()
            return False
            
        logging.info(f"Processing VESPA records page {page}...")
        
        try:
            data = make_knack_request(OBJECT_KEYS['vespa_results'], page=page)
        except Exception as e:
            logging.error(f"Failed to fetch page {page}: {e}")
            checkpoint.vespa_page = page
            checkpoint.save()
            return False
            
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
                
                # Ensure email is valid
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
                
                # Process student if not already done
                student_knack_id = record['id']
                if student_knack_id not in student_knack_to_id:
                    # Extract name
                    name_field = record.get('field_187_raw', '')
                    if isinstance(name_field, dict):
                        student_name = name_field.get('full', '') or f"{name_field.get('first', '')} {name_field.get('last', '')}".strip()
                    elif isinstance(name_field, str):
                        student_name = name_field
                    else:
                        student_name = ''
                    
                    student_data = {
                        'knack_id': student_knack_id,
                        'email': student_email,
                        'name': student_name,
                        'establishment_id': establishment_id,
                        'group': record.get('field_223', ''),
                        'year_group': record.get('field_144', ''),
                        'course': record.get('field_2299', ''),
                        'faculty': record.get('field_782', '')
                    }
                    
                    student_batch.append(student_data)
                    students_processed.add(student_knack_id)
                
                # Process VESPA scores for each cycle
                completion_date = record.get('field_855')
                academic_year = calculate_academic_year(completion_date, is_australian)
                
                for cycle in [1, 2, 3]:
                    field_offset = (cycle - 1) * 6
                    vision_field = f'field_{155 + field_offset}_raw'
                    
                    # Check if this cycle has data
                    if record.get(vision_field) is not None:
                        def clean_score(value):
                            if value == "" or value is None:
                                return None
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return None
                        
                        vespa_data = {
                            'student_knack_id': student_knack_id,  # We'll resolve this later
                            'cycle': cycle,
                            'vision': clean_score(record.get(f'field_{155 + field_offset}_raw')),
                            'effort': clean_score(record.get(f'field_{156 + field_offset}_raw')),
                            'systems': clean_score(record.get(f'field_{157 + field_offset}_raw')),
                            'practice': clean_score(record.get(f'field_{158 + field_offset}_raw')),
                            'attitude': clean_score(record.get(f'field_{159 + field_offset}_raw')),
                            'overall': clean_score(record.get(f'field_{160 + field_offset}_raw')),
                            'completion_date': completion_date,
                            'academic_year': academic_year
                        }
                        
                        vespa_batch.append(vespa_data)
                        
            except Exception as e:
                logging.error(f"Error processing VESPA record {record.get('id')}: {e}")
        
        # Batch upsert students when batch is full
        if len(student_batch) >= BATCH_SIZES['students']:
            logging.info(f"Upserting batch of {len(student_batch)} students...")
            if batch_upsert_with_retry('students', student_batch, 'knack_id'):
                checkpoint.total_students += len(student_batch)
                
                # Get the new student IDs
                for student in student_batch:
                    result = supabase.table('students').select('id').eq('knack_id', student['knack_id']).execute()
                    if result.data:
                        student_knack_to_id[student['knack_id']] = result.data[0]['id']
            
            student_batch = []
            checkpoint.save()
        
        # Process vespa scores batch when it's full
        if len(vespa_batch) >= BATCH_SIZES['vespa_scores']:
            logging.info(f"Processing batch of {len(vespa_batch)} VESPA scores...")
            
            # Convert student_knack_id to student_id
            valid_scores = []
            for score in vespa_batch:
                student_id = student_knack_to_id.get(score['student_knack_id'])
                if student_id:
                    score['student_id'] = student_id
                    del score['student_knack_id']
                    valid_scores.append(score)
            
            if valid_scores:
                if batch_upsert_with_retry('vespa_scores', valid_scores, 'student_id,cycle'):
                    checkpoint.total_vespa_scores += len(valid_scores)
            
            vespa_batch = []
            checkpoint.save()
        
        page += 1
        checkpoint.vespa_page = page
        time.sleep(0.5)  # Rate limiting
    
    # Process remaining batches
    if student_batch:
        logging.info(f"Upserting final batch of {len(student_batch)} students...")
        if batch_upsert_with_retry('students', student_batch, 'knack_id'):
            checkpoint.total_students += len(student_batch)
            for student in student_batch:
                result = supabase.table('students').select('id').eq('knack_id', student['knack_id']).execute()
                if result.data:
                    student_knack_to_id[student['knack_id']] = result.data[0]['id']
    
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
                checkpoint.total_vespa_scores += len(valid_scores)
    
    checkpoint.save()
    logging.info(f"Synced {checkpoint.total_students} students and {checkpoint.total_vespa_scores} VESPA scores")
    return True

def sync_question_responses(checkpoint: SyncCheckpoint) -> bool:
    """Sync psychometric question responses with batch processing"""
    logging.info("Syncing question responses...")
    
    # Check if question mapping file exists
    question_file = Path('AIVESPACoach/psychometric_question_details.json')
    if not question_file.exists():
        logging.warning(f"Question mapping file not found: {question_file}")
        return True
    
    # Load question mapping
    with open(question_file, 'r') as f:
        question_mapping = json.load(f)
    
    # Get student mapping
    students = supabase.table('students').select('id', 'knack_id').execute()
    student_map = {s['knack_id']: s['id'] for s in students.data}
    
    page = checkpoint.psychometric_page
    response_batch = []
    
    while True:
        if shutdown_requested:
            logging.info("Shutdown requested, saving progress...")
            checkpoint.psychometric_page = page
            checkpoint.save()
            return False
            
        logging.info(f"Processing psychometric records page {page}...")
        
        try:
            data = make_knack_request(OBJECT_KEYS['psychometric'], page=page)
        except Exception as e:
            logging.error(f"Failed to fetch page {page}: {e}")
            checkpoint.psychometric_page = page
            checkpoint.save()
            return False
            
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                # Get student ID from connection
                student_field = record.get('field_1819_raw', [])
                student_knack_id = None
                if student_field and isinstance(student_field, list) and len(student_field) > 0:
                    student_item = student_field[0]
                    if isinstance(student_item, dict):
                        student_knack_id = student_item.get('id') or student_item.get('value')
                    else:
                        student_knack_id = student_item
                
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
                                    
                                    response_batch.append(response_data)
                                    
            except Exception as e:
                logging.error(f"Error processing psychometric record {record.get('id')}: {e}")
        
        # Batch insert responses
        if len(response_batch) >= BATCH_SIZES['question_responses']:
            logging.info(f"Inserting batch of {len(response_batch)} question responses...")
            # For question_responses, we use insert instead of upsert as there's no unique constraint
            try:
                supabase.table('question_responses').insert(response_batch).execute()
                checkpoint.total_responses += len(response_batch)
            except Exception as e:
                logging.error(f"Batch insert failed: {e}")
                # Try smaller batches
                for i in range(0, len(response_batch), 100):
                    small_batch = response_batch[i:i+100]
                    try:
                        supabase.table('question_responses').insert(small_batch).execute()
                        checkpoint.total_responses += len(small_batch)
                    except Exception as batch_error:
                        logging.error(f"Small batch insert failed: {batch_error}")
            
            response_batch = []
            checkpoint.save()
        
        page += 1
        checkpoint.psychometric_page = page
        time.sleep(0.5)  # Rate limiting
    
    # Insert remaining responses
    if response_batch:
        logging.info(f"Inserting final batch of {len(response_batch)} question responses...")
        try:
            supabase.table('question_responses').insert(response_batch).execute()
            checkpoint.total_responses += len(response_batch)
        except Exception as e:
            logging.error(f"Final batch insert failed: {e}")
    
    checkpoint.save()
    logging.info(f"Synced {checkpoint.total_responses} question responses")
    return True

def calculate_statistics(checkpoint: SyncCheckpoint) -> bool:
    """Calculate and store statistics for schools"""
    if checkpoint.statistics_calculated:
        logging.info("Statistics already calculated, skipping...")
        return True
        
    logging.info("Calculating statistics...")
    
    try:
        # Call the Supabase stored procedure to calculate all statistics
        result = supabase.rpc('calculate_all_statistics').execute()
        logging.info("Statistics calculation completed via stored procedure")
        
        checkpoint.statistics_calculated = True
        checkpoint.save()
        return True
        
    except Exception as e:
        logging.error(f"Error calculating statistics: {e}")
        # Fallback to manual calculation if stored procedure doesn't exist
        logging.info("Falling back to manual statistics calculation...")
        
        # Get all establishments
        establishments = supabase.table('establishments').select('*').execute()
        
        for est in establishments.data:
            if shutdown_requested:
                return False
                
            try:
                # Calculate current academic year
                current_year = calculate_academic_year(
                    datetime.now().strftime('%d/%m/%Y'), 
                    est.get('is_australian', False)
                )
                
                # Get all students for this establishment
                students = supabase.table('students').select('id').eq('establishment_id', est['id']).execute()
                student_ids = [s['id'] for s in students.data]
                
                if not student_ids:
                    continue
                
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
                            stats_data = {
                                'establishment_id': est['id'],
                                'cycle': cycle,
                                'academic_year': current_year,
                                'element': element,
                                'average': sum(values) / len(values),
                                'count': len(values),
                                'min_value': min(values),
                                'max_value': max(values)
                            }
                            
                            supabase.table('school_statistics').upsert(
                                stats_data,
                                on_conflict='establishment_id,cycle,academic_year,element'
                            ).execute()
                            
            except Exception as e:
                logging.error(f"Error calculating statistics for {est['name']}: {e}")
        
        checkpoint.statistics_calculated = True
        checkpoint.save()
        logging.info("Statistics calculation complete")
        return True

def main():
    """Main sync function with checkpoint support"""
    start_time = datetime.now()
    
    # Prevent system sleep
    keep_system_awake()
    
    # Load or create checkpoint
    checkpoint = SyncCheckpoint.load()
    
    try:
        # Log sync start
        if checkpoint.vespa_page == 1 and not checkpoint.establishments_synced:
            sync_log = {
                'sync_type': 'full_sync',
                'status': 'started',
                'started_at': start_time.isoformat()
            }
            log_result = supabase.table('sync_logs').insert(sync_log).execute()
            sync_log_id = log_result.data[0]['id']
        else:
            sync_log = {
                'sync_type': 'resumed_sync',
                'status': 'started',
                'started_at': start_time.isoformat(),
                'metadata': {
                    'resumed_from_page': checkpoint.vespa_page,
                    'students_already_processed': len(checkpoint.students_processed)
                }
            }
            log_result = supabase.table('sync_logs').insert(sync_log).execute()
            sync_log_id = log_result.data[0]['id']
        
        # Run sync operations
        success = True
        
        if success and not checkpoint.establishments_synced:
            success = sync_establishments(checkpoint)
        
        if success:
            success = sync_students_and_vespa_scores(checkpoint)
        
        if success:
            success = sync_question_responses(checkpoint)
        
        if success:
            success = calculate_statistics(checkpoint)
        
        # Update sync log
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            # Clear checkpoint on successful completion
            checkpoint.clear()
            
            supabase.table('sync_logs').update({
                'status': 'completed',
                'completed_at': end_time.isoformat(),
                'metadata': {
                    'duration_seconds': duration,
                    'total_students': checkpoint.total_students,
                    'total_vespa_scores': checkpoint.total_vespa_scores,
                    'total_question_responses': checkpoint.total_responses
                }
            }).eq('id', sync_log_id).execute()
            
            logging.info(f"Sync completed successfully in {duration:.2f} seconds")
            logging.info(f"Total synced - Students: {checkpoint.total_students}, VESPA Scores: {checkpoint.total_vespa_scores}, Question Responses: {checkpoint.total_responses}")
        else:
            supabase.table('sync_logs').update({
                'status': 'interrupted',
                'completed_at': end_time.isoformat(),
                'metadata': {
                    'duration_seconds': duration,
                    'checkpoint_saved': True,
                    'can_resume': True
                }
            }).eq('id', sync_log_id).execute()
            
            logging.info("Sync interrupted but checkpoint saved. Run again to resume.")
        
    except Exception as e:
        logging.error(f"Sync failed: {e}")
        
        # Update sync log with error
        if 'sync_log_id' in locals():
            supabase.table('sync_logs').update({
                'status': 'failed',
                'completed_at': datetime.now().isoformat(),
                'error_message': str(e)
            }).eq('id', sync_log_id).execute()
        
        # Save checkpoint for resume
        checkpoint.save()
        raise
    
    finally:
        # Restore system sleep
        restore_system_sleep()

if __name__ == "__main__":
    main()