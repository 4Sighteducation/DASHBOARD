#!/usr/bin/env python3
"""
Backend-optimized sync script for Heroku deployment
Runs as a scheduled job without user interaction
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
from typing import List, Dict, Any, Optional, Set

# Configure logging for Heroku
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # Heroku captures stdout
)

# Environment variables (from Heroku config)
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
BASE_KNACK_URL = "https://api.knack.com/v1/objects"

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Knack field mappings
OBJECT_KEYS = {
    'establishments': 'object_2',
    'vespa_results': 'object_10',
    'psychometric': 'object_29',
    'staff_admins': 'object_5',  # Fixed: was object_3, should be object_5
    'super_users': 'object_21',  # Added: for super user access
    'academy_trusts': 'object_134'
}

# Batch sizes optimized for Heroku memory limits
BATCH_SIZES = {
    'establishments': 50,
    'students': 100,
    'vespa_scores': 300,  # Reduced for Heroku memory
    'question_responses': 500
}

# Heroku timeout is 30 minutes for scheduled jobs
HEROKU_TIMEOUT = 28 * 60  # 28 minutes to be safe
start_time = time.time()

def check_timeout():
    """Check if we're approaching Heroku timeout"""
    elapsed = time.time() - start_time
    if elapsed > HEROKU_TIMEOUT:
        logging.warning("Approaching Heroku timeout, stopping gracefully")
        return True
    return False

def make_knack_request(object_key: str, page: int = 1, rows_per_page: int = 1000, filters: Optional[List] = None) -> Dict:
    """Make a request to Knack API with retry logic"""
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
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logging.warning(f"Request timeout on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                raise
        except Exception as e:
            logging.error(f"Knack API error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                raise

def batch_upsert_with_retry(table: str, data: List[Dict], on_conflict: str, max_retries: int = 3) -> bool:
    """Batch upsert with retry logic"""
    for attempt in range(max_retries):
        try:
            if data:
                result = supabase.table(table).upsert(data, on_conflict=on_conflict).execute()
                return True
        except Exception as e:
            logging.error(f"Batch upsert error on {table} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                # If batch fails, try smaller batches
                logging.info(f"Trying smaller batches for {table}")
                batch_size = max(1, len(data) // 4)
                success_count = 0
                for i in range(0, len(data), batch_size):
                    small_batch = data[i:i+batch_size]
                    try:
                        supabase.table(table).upsert(small_batch, on_conflict=on_conflict).execute()
                        success_count += len(small_batch)
                    except Exception as batch_error:
                        logging.error(f"Small batch failed: {batch_error}")
                logging.info(f"Small batches: {success_count}/{len(data)} successful")
                return success_count > 0
    return False

def fetch_all_knack_records(object_key: str, filters: Optional[List] = None, max_pages: Optional[int] = None) -> List[Dict]:
    """Fetch all records from a Knack object with timeout awareness"""
    all_records = []
    page = 1
    total_pages = None
    
    while True:
        if check_timeout():
            logging.warning(f"Timeout reached while fetching {object_key}, returning partial data")
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
            
        if max_pages and page >= max_pages:
            logging.info(f"Reached max pages limit ({max_pages}) for {object_key}")
            break
            
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    logging.info(f"Fetched {len(all_records)} records from {object_key}")
    return all_records

def sync_establishments() -> bool:
    """Sync establishments"""
    logging.info("Syncing establishments...")
    
    # Check if already synced recently
    recent_check = supabase.table('establishments').select('id', count='exact', head=True).execute()
    if hasattr(recent_check, 'count') and recent_check.count > 300:
        logging.info(f"Establishments already synced ({recent_check.count} found), skipping...")
        return True
    
    filters = [{'field': 'field_2209', 'operator': 'is not', 'value': 'Cancelled'}]
    establishments = fetch_all_knack_records(OBJECT_KEYS['establishments'], filters=filters)
    
    batch = []
    for est in establishments:
        try:
            est_name = est.get('field_44') or est.get('field_44_raw') or ""
            if not est_name or est_name == "EMPTY":
                est_name = est.get('field_11') or est.get('identifier') or f"Establishment {est['id'][:8]}"
            
            establishment_data = {
                'knack_id': est['id'],
                'name': est_name,
                # Check field_3573 for Australian schools - only "True" counts
                'is_australian': est.get('field_3573_raw', '') == 'True'
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
    return True

def calculate_academic_year(date_str: str, is_australian: bool = False) -> Optional[str]:
    """Calculate academic year based on date and establishment location"""
    if not date_str or date_str == "":
        return None
    
    try:
        date = datetime.strptime(date_str, '%d/%m/%Y')
        
        if is_australian:
            return str(date.year)
        else:
            if date.month >= 8:
                return f"{date.year}-{str(date.year + 1)[2:]}"
            else:
                return f"{date.year - 1}-{str(date.year)[2:]}"
                
    except Exception as e:
        logging.error(f"Error calculating academic year for {date_str}: {e}")
        return None

def format_date_for_postgres(date_str: str) -> Optional[str]:
    """Convert DD/MM/YYYY to PostgreSQL format YYYY-MM-DD"""
    if not date_str or date_str == "":
        return None
    
    try:
        # Parse UK format date
        date = datetime.strptime(date_str, '%d/%m/%Y')
        # Return PostgreSQL format
        return date.strftime('%Y-%m-%d')
    except Exception as e:
        logging.error(f"Error formatting date {date_str}: {e}")
        return None

def sync_students_and_vespa_scores() -> Dict[str, int]:
    """Sync students and VESPA scores with timeout awareness"""
    logging.info("Syncing students and VESPA scores...")
    
    stats = {'students': 0, 'vespa_scores': 0}
    
    # Get establishment mapping
    establishments = supabase.table('establishments').select('id', 'knack_id', 'is_australian').execute()
    est_map = {e['knack_id']: {'id': e['id'], 'is_australian': e['is_australian']} for e in establishments.data}
    
    # Get existing students to avoid duplicates
    existing_students = supabase.table('students').select('id', 'knack_id').execute()
    student_knack_to_id = {s['knack_id']: s['id'] for s in existing_students.data}
    
    student_batch = []
    vespa_batch = []
    
    page = 1
    max_pages = None
    
    # For Heroku, limit pages if running out of time
    if check_timeout():
        logging.warning("Timeout check failed before starting VESPA sync")
        return stats
    
    while True:
        if check_timeout():
            logging.warning("Timeout during VESPA sync, saving progress...")
            break
            
        # Estimate remaining time and pages
        elapsed = time.time() - start_time
        if elapsed > HEROKU_TIMEOUT * 0.7:  # 70% of timeout
            remaining_time = HEROKU_TIMEOUT - elapsed
            pages_per_minute = page / (elapsed / 60) if elapsed > 0 else 1
            max_pages = page + int(pages_per_minute * (remaining_time / 60))
            logging.info(f"Limited time remaining, capping at page {max_pages}")
            
        logging.info(f"Processing VESPA records page {page}...")
        
        try:
            data = make_knack_request(OBJECT_KEYS['vespa_results'], page=page)
        except Exception as e:
            logging.error(f"Failed to fetch page {page}: {e}")
            break
            
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                # Extract student info (same logic as optimized version)
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
                
                # Process student
                student_knack_id = record['id']
                if student_knack_id not in student_knack_to_id:
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
                
                # Process VESPA scores
                completion_date = record.get('field_855')
                academic_year = calculate_academic_year(completion_date, is_australian)
                
                for cycle in [1, 2, 3]:
                    field_offset = (cycle - 1) * 6
                    vision_field = f'field_{155 + field_offset}_raw'
                    
                    # Check if this cycle has any actual scores
                    def clean_score(value):
                        if value == "" or value is None:
                            return None
                        try:
                            return int(value)
                        except (ValueError, TypeError):
                            return None
                    
                    # Get all scores for this cycle
                    vision = clean_score(record.get(f'field_{155 + field_offset}_raw'))
                    effort = clean_score(record.get(f'field_{156 + field_offset}_raw'))
                    systems = clean_score(record.get(f'field_{157 + field_offset}_raw'))
                    practice = clean_score(record.get(f'field_{158 + field_offset}_raw'))
                    attitude = clean_score(record.get(f'field_{159 + field_offset}_raw'))
                    overall = clean_score(record.get(f'field_{160 + field_offset}_raw'))
                    
                    # Only create record if at least one score exists
                    if any([vision, effort, systems, practice, attitude, overall]):
                        vespa_data = {
                            'student_knack_id': student_knack_id,
                            'cycle': cycle,
                            'vision': vision,
                            'effort': effort,
                            'systems': systems,
                            'practice': practice,
                            'attitude': attitude,
                            'overall': overall,
                            'completion_date': format_date_for_postgres(completion_date),
                            'academic_year': academic_year
                        }
                        
                        vespa_batch.append(vespa_data)
                        
            except Exception as e:
                logging.error(f"Error processing VESPA record {record.get('id')}: {e}")
        
        # Batch upsert students
        if len(student_batch) >= BATCH_SIZES['students']:
            logging.info(f"Upserting batch of {len(student_batch)} students...")
            if batch_upsert_with_retry('students', student_batch, 'knack_id'):
                stats['students'] += len(student_batch)
                
                # Update mapping
                for student in student_batch:
                    result = supabase.table('students').select('id').eq('knack_id', student['knack_id']).execute()
                    if result.data:
                        student_knack_to_id[student['knack_id']] = result.data[0]['id']
            
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
                    stats['vespa_scores'] += len(valid_scores)
            
            vespa_batch = []
        
        page += 1
        
        if max_pages and page > max_pages:
            logging.info(f"Reached max pages limit due to timeout constraints")
            break
            
        time.sleep(0.5)  # Rate limiting
    
    # Process remaining batches
    if student_batch:
        if batch_upsert_with_retry('students', student_batch, 'knack_id'):
            stats['students'] += len(student_batch)
            for student in student_batch:
                result = supabase.table('students').select('id').eq('knack_id', student['knack_id']).execute()
                if result.data:
                    student_knack_to_id[student['knack_id']] = result.data[0]['id']
    
    if vespa_batch:
        valid_scores = []
        for score in vespa_batch:
            student_id = student_knack_to_id.get(score['student_knack_id'])
            if student_id:
                score['student_id'] = student_id
                del score['student_knack_id']
                valid_scores.append(score)
        
        if valid_scores:
            if batch_upsert_with_retry('vespa_scores', valid_scores, 'student_id,cycle'):
                stats['vespa_scores'] += len(valid_scores)
    
    logging.info(f"Synced {stats['students']} new students and {stats['vespa_scores']} VESPA scores")
    return stats

def sync_question_responses() -> int:
    """Sync psychometric question responses"""
    logging.info("Syncing question responses...")
    
    # Skip if no time left
    if check_timeout():
        logging.warning("Skipping question responses sync due to timeout")
        return 0
    
    # Check if question mapping file exists
    try:
        import urllib.request
        # Try to fetch from GitHub or load from environment
        question_mapping_url = os.getenv('QUESTION_MAPPING_URL')
        if question_mapping_url:
            with urllib.request.urlopen(question_mapping_url) as response:
                question_mapping = json.loads(response.read())
        else:
            # Skip if no mapping available
            logging.warning("No question mapping available, skipping psychometric sync")
            return 0
    except Exception as e:
        logging.error(f"Failed to load question mapping: {e}")
        return 0
    
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
    
    response_count = 0
    response_batch = []
    
    # Limit pages based on remaining time
    elapsed = time.time() - start_time
    remaining_time = HEROKU_TIMEOUT - elapsed
    max_pages = int(remaining_time / 60)  # Rough estimate: 1 page per minute
    
    page = 1
    while page <= max_pages:
        if check_timeout():
            break
            
        logging.info(f"Processing psychometric records page {page}...")
        
        try:
            data = make_knack_request(OBJECT_KEYS['psychometric'], page=page)
        except Exception as e:
            logging.error(f"Failed to fetch page {page}: {e}")
            break
            
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                # Get Object_10 connection via field_792 (email-based connection)
                object_10_field = record.get('field_792_raw', [])
                object_10_knack_id = None
                if object_10_field and isinstance(object_10_field, list) and len(object_10_field) > 0:
                    object_10_item = object_10_field[0]
                    if isinstance(object_10_item, dict):
                        object_10_knack_id = object_10_item.get('id') or object_10_item.get('value')
                    else:
                        object_10_knack_id = object_10_item
                
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
                                    # Skip if can't convert to int
                                    pass
                                    
            except Exception as e:
                logging.error(f"Error processing psychometric record {record.get('id')}: {e}")
        
        # Batch insert responses
        if len(response_batch) >= BATCH_SIZES['question_responses']:
            try:
                supabase.table('question_responses').insert(response_batch).execute()
                response_count += len(response_batch)
            except Exception as e:
                logging.error(f"Batch insert failed: {e}")
            
            response_batch = []
        
        page += 1
        time.sleep(0.5)
    
    # Insert remaining responses
    if response_batch:
        try:
            supabase.table('question_responses').insert(response_batch).execute()
            response_count += len(response_batch)
        except Exception as e:
            logging.error(f"Final batch insert failed: {e}")
    
    logging.info(f"Synced {response_count} question responses")
    return response_count

def calculate_statistics() -> bool:
    """Calculate and store statistics"""
    if check_timeout():
        logging.warning("Skipping statistics calculation due to timeout")
        return False
        
    logging.info("Calculating statistics...")
    
    try:
        # Use the stored procedure if available
        result = supabase.rpc('calculate_all_statistics', {}).execute()
        logging.info("Statistics calculation completed")
        return True
    except Exception as e:
        logging.error(f"Statistics calculation failed: {e}")
        return False

def main():
    """Main sync function for backend/scheduled execution"""
    sync_start = datetime.now()
    
    try:
        # Log sync start
        sync_log = {
            'sync_type': 'scheduled_sync',
            'status': 'started',
            'started_at': sync_start.isoformat(),
            'metadata': {'environment': 'heroku'}
        }
        log_result = supabase.table('sync_logs').insert(sync_log).execute()
        sync_log_id = log_result.data[0]['id']
        
        # Track what was completed
        completed_steps = []
        stats = {'students': 0, 'vespa_scores': 0, 'question_responses': 0}
        
        # Run sync operations
        if sync_establishments():
            completed_steps.append('establishments')
        
        vespa_stats = sync_students_and_vespa_scores()
        stats['students'] = vespa_stats['students']
        stats['vespa_scores'] = vespa_stats['vespa_scores']
        if vespa_stats['students'] > 0 or vespa_stats['vespa_scores'] > 0:
            completed_steps.append('vespa_data')
        
        question_count = sync_question_responses()
        stats['question_responses'] = question_count
        if question_count > 0:
            completed_steps.append('questions')
        
        if calculate_statistics():
            completed_steps.append('statistics')
        
        # Update sync log
        end_time = datetime.now()
        duration = (end_time - sync_start).total_seconds()
        
        # Determine if sync was complete or partial
        is_complete = len(completed_steps) >= 3  # At least establishments, vespa, and stats
        
        supabase.table('sync_logs').update({
            'status': 'completed' if is_complete else 'partial',
            'completed_at': end_time.isoformat(),
            'metadata': {
                'duration_seconds': duration,
                'completed_steps': completed_steps,
                'total_students': stats['students'],
                'total_vespa_scores': stats['vespa_scores'],
                'total_question_responses': stats['question_responses'],
                'timeout_reached': check_timeout()
            }
        }).eq('id', sync_log_id).execute()
        
        logging.info(f"Sync {'completed' if is_complete else 'partially completed'} in {duration:.2f} seconds")
        logging.info(f"Completed steps: {', '.join(completed_steps)}")
        logging.info(f"Stats - Students: {stats['students']}, VESPA: {stats['vespa_scores']}, Questions: {stats['question_responses']}")
        
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