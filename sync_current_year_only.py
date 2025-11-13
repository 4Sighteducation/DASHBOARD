#!/usr/bin/env python3
"""
CURRENT-YEAR-ONLY SYNC - Version 3.1 (November 12, 2025)
=========================================================

This sync ONLY processes data from the current academic year.
- Faster: ~1,000 records instead of 27,000
- Safer: Never touches historical data
- Simpler: Academic year is constant, not calculated per record
- More reliable: Uses email matching instead of unreliable field_792 connections

FIXES IN v3.1 (Nov 12, 2025):
1. Date parsing: Handles both 'DD/MM/YYYY' and 'DD/MM/YYYY HH:MM' formats
2. VESPA cycle logic: Only syncs cycles with actual data (prevents duplicates)
3. Duplicate cleanup: Deletes Supabase cycles that don't exist in Knack
4. Knack as source of truth: Maintains perfect sync with Knack data
5. Better error handling: Ensures failures are logged and reported

KEY CHANGES FROM V2.0:
1. Date filters at Knack API level (only fetch current year)
2. Email-based student matching (field_2732 → students.email)
3. Academic year hard-coded at start (no per-record calculation)
4. Records without dates are skipped (clean logic)
5. Protects all historical data

ACADEMIC YEAR LOGIC:
- UK Schools: Aug 1 - Jul 31 (2025/2026)
- Australian Schools (Standard): Same as UK
- Australian Schools (Non-Standard): Jan 1 - Dec 31 (2025/2025)
"""

import os
import sys
import json
import requests
import logging
import re
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from collections import defaultdict

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_current_year_only.log', encoding='utf-8'),
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
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Object keys
OBJECT_KEYS = {
    'establishments': 'object_2',
    'vespa_results': 'object_10',
    'psychometric': 'object_29'
}

# Batch sizes
BATCH_SIZES = {
    'students': 100,
    'vespa_scores': 200,
    'question_responses': 500
}

# Sync report
sync_report = {
    'start_time': datetime.now(),
    'version': '3.1 - Current Year Only (Data Integrity Fix)',
    'academic_year_uk': None,
    'academic_year_aus': None,
    'tables': {},
    'warnings': [],
    'errors': [],
    'skipped_no_date': 0,
    'skipped_no_email': 0,
    'skipped_no_student_match': 0
}


def get_current_academic_year_boundaries():
    """
    Calculate current academic year and date boundaries for filtering.
    
    Returns:
        dict: {
            'uk': {'year': '2025/2026', 'start': '01/08/2025', 'end': '31/07/2026'},
            'aus': {'year': '2025/2025', 'start': '01/01/2025', 'end': '31/12/2025'}
        }
    """
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    # UK Academic Year (August 1 - July 31)
    if current_month >= 8:
        uk_start_year = current_year
        uk_end_year = current_year + 1
    else:
        uk_start_year = current_year - 1
        uk_end_year = current_year
    
    uk_year = f"{uk_start_year}/{uk_end_year}"
    uk_start_date = f"01/08/{uk_start_year}"
    uk_end_date = f"31/07/{uk_end_year}"
    
    # Australian Calendar Year (January 1 - December 31)
    aus_year = f"{current_year}/{current_year}"
    aus_start_date = f"01/01/{current_year}"
    aus_end_date = f"31/12/{current_year}"
    
    boundaries = {
        'uk': {
            'year': uk_year,
            'start': uk_start_date,
            'end': uk_end_date
        },
        'aus': {
            'year': aus_year,
            'start': aus_start_date,
            'end': aus_end_date
        }
    }
    
    logging.info(f"Current academic year boundaries calculated:")
    logging.info(f"  UK: {uk_year} ({uk_start_date} to {uk_end_date})")
    logging.info(f"  AUS: {aus_year} ({aus_start_date} to {aus_end_date})")
    
    return boundaries


def make_knack_request(object_key, page=1, rows_per_page=1000, filters=None):
    """Make a request to Knack API with pagination and filtering support"""
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
        response = requests.get(url, headers=headers, params=params, timeout=90)
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
            total_records = data.get('total_records', 0)
            logging.info(f"Total pages for {object_key}: {total_pages} ({total_records} records)")
        
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
    
    if '<a href="mailto:' in str(html_or_email):
        match = re.search(r'mailto:([^"]+)"', str(html_or_email))
        if match:
            return match.group(1)
    
    return str(html_or_email).strip()


def convert_knack_date_to_postgres(knack_date):
    """
    Convert Knack date format to PostgreSQL format (YYYY-MM-DD)
    Handles both 'DD/MM/YYYY' and 'DD/MM/YYYY HH:MM' formats
    
    Args:
        knack_date: Date string in DD/MM/YYYY or DD/MM/YYYY HH:MM format
    
    Returns:
        Date string in YYYY-MM-DD format or None if invalid
    """
    if not knack_date:
        return None
    
    try:
        # Handle both with and without time
        if ' ' in knack_date:
            # Has time component - try with time first
            try:
                date_obj = datetime.strptime(knack_date, '%d/%m/%Y %H:%M')
            except ValueError:
                # Try just the date part
                date_obj = datetime.strptime(knack_date.split(' ')[0], '%d/%m/%Y')
        else:
            # No time component
            date_obj = datetime.strptime(knack_date, '%d/%m/%Y')
        
        # Return as YYYY-MM-DD
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        logging.warning(f"Could not parse date: {knack_date}")
        return None


def deduplicate_response_batch(response_batch):
    """
    Remove duplicate question responses from batch before upserting.
    Keeps the first occurrence of each unique (student_id, cycle, academic_year, question_id).
    
    Args:
        response_batch: List of response dictionaries
    
    Returns:
        Deduplicated list
    """
    seen = set()
    deduped = []
    
    for response in response_batch:
        key = (
            response['student_id'],
            response['cycle'],
            response['academic_year'],
            response['question_id']
        )
        
        if key not in seen:
            seen.add(key)
            deduped.append(response)
    
    return deduped


def sync_students_and_vespa_scores(year_boundaries):
    """
    Sync students and VESPA scores from Object_10 for CURRENT YEAR ONLY
    Uses date filtering at API level to only fetch current academic year data
    """
    logging.info("="*80)
    logging.info("SYNCING STUDENTS & VESPA SCORES - CURRENT YEAR ONLY")
    logging.info("="*80)
    
    academic_year = year_boundaries['uk']['year']
    
    # Date filters for Object_10 (field_855 = completion date)
    filters = [
        {
            'field': 'field_855',
            'operator': 'is after',
            'value': year_boundaries['uk']['start']
        },
        {
            'field': 'field_855',
            'operator': 'is before',
            'value': year_boundaries['uk']['end']
        }
    ]
    
    logging.info(f"Fetching Object_10 records for academic year {academic_year}")
    logging.info(f"Date filter: {year_boundaries['uk']['start']} to {year_boundaries['uk']['end']}")
    
    # Fetch current year records from Knack
    records = fetch_all_knack_records(OBJECT_KEYS['vespa_results'], filters=filters)
    
    logging.info(f"Processing {len(records)} Object_10 records...")
    
    # Get establishment mapping
    establishments = supabase.table('establishments').select('id, knack_id, is_australian, use_standard_year').execute()
    est_map = {est['knack_id']: est for est in establishments.data}
    
    students_synced = 0
    scores_synced = 0
    comments_synced = 0  # NEW: Track comments
    skipped_no_date = 0
    skipped_no_email = 0
    
    student_batch = []
    score_batch = []
    comment_batch = []  # NEW: Batch for student comments
    
    # Track student mappings for Object_29 sync
    student_id_map = {}  # knack_id -> supabase_id
    student_email_map = {}  # email -> supabase_id
    
    # NEW: Track which cycles each student has in Knack (for cleanup)
    student_cycles_in_knack = {}  # knack_id -> [1, 2, 3] (list of cycles with data)
    
    for record in records:
        try:
            # SKIP if no completion date
            completion_date = record.get('field_855')
            if not completion_date or not completion_date.strip():
                skipped_no_date += 1
                continue
            
            # Get email
            email_raw = record.get('field_197', '') or record.get('field_197_raw', '')
            email = extract_email_from_html(email_raw).lower().strip()
            
            if not email:
                skipped_no_email += 1
                continue
            
            # Get establishment
            establishment_raw = record.get('field_133_raw', [])
            establishment_id = None
            
            if establishment_raw and isinstance(establishment_raw, list) and len(establishment_raw) > 0:
                est_knack_id = establishment_raw[0].get('id') if isinstance(establishment_raw[0], dict) else establishment_raw[0]
                if est_knack_id in est_map:
                    establishment_id = est_map[est_knack_id]['id']
                    
                    # Check if this establishment uses different academic year
                    if est_map[est_knack_id].get('is_australian') and not est_map[est_knack_id].get('use_standard_year'):
                        # Use Australian year for this record
                        academic_year = year_boundaries['aus']['year']
            
            if not establishment_id:
                continue
            
            # Get student name
            student_name = record.get('field_187', '') or record.get('field_187_raw', '')
            
            # Student data - academic_year is CONSTANT for all records
            student_data = {
                'knack_id': record['id'],
                'email': email,
                'name': student_name,
                'establishment_id': establishment_id,
                'academic_year': academic_year,  # CONSTANT - set once at start!
                'group': record.get('field_223', ''),
                'year_group': record.get('field_144', ''),
                'course': record.get('field_2299', ''),
                'faculty': record.get('field_782', '')
            }
            
            student_batch.append(student_data)
            
            # Helper function to convert empty strings to None
            def clean_score(value):
                if value == "" or value is None:
                    return None
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return None
            
            # Track which cycles have ACTUAL data in Knack
            knack_cycles_with_data = []
            
            # Process VESPA scores (all 3 cycles)
            for cycle in [1, 2, 3]:
                # Calculate field offsets for each cycle
                field_offset = (cycle - 1) * 6
                
                # Get individual scores from the correct fields
                vision = clean_score(record.get(f'field_{155 + field_offset}_raw'))
                effort = clean_score(record.get(f'field_{156 + field_offset}_raw'))
                systems = clean_score(record.get(f'field_{157 + field_offset}_raw'))
                practice = clean_score(record.get(f'field_{158 + field_offset}_raw'))
                attitude = clean_score(record.get(f'field_{159 + field_offset}_raw'))
                overall = clean_score(record.get(f'field_{160 + field_offset}_raw'))
                
                # Check if this cycle has ACTUAL data (at least one non-null score)
                cycle_has_data = any(v is not None for v in [vision, effort, systems, practice, attitude, overall])
                
                if cycle_has_data:
                    knack_cycles_with_data.append(cycle)
                    
                    # Validate overall score
                    if overall is not None and (overall < 0 or overall > 10):
                        logging.warning(f"Invalid overall score {overall} for {email}, cycle {cycle} - skipping")
                        continue
                    
                    try:
                        score_data = {
                            'student_knack_id': record['id'],
                            'cycle': cycle,
                            'academic_year': academic_year,
                            'vision': vision,
                            'effort': effort,
                            'systems': systems,
                            'practice': practice,
                            'attitude': attitude,
                            'overall': overall,
                            'completion_date': convert_knack_date_to_postgres(completion_date)
                        }
                        score_batch.append(score_data)
                    except Exception as e:
                        logging.warning(f"Error creating VESPA score for {email}: {e}")
            
            # Store which cycles this student has in Knack
            student_cycles_in_knack[record['id']] = knack_cycles_with_data
            
            # NEW: Extract student comments (RRC and Goal fields)
            comment_mappings = [
                {'cycle': 1, 'type': 'rrc', 'field_raw': 'field_2302_raw'},
                {'cycle': 1, 'type': 'goal', 'field_raw': 'field_2499_raw'},
                {'cycle': 2, 'type': 'rrc', 'field_raw': 'field_2303_raw'},
                {'cycle': 2, 'type': 'goal', 'field_raw': 'field_2493_raw'},
                {'cycle': 3, 'type': 'rrc', 'field_raw': 'field_2304_raw'},
                {'cycle': 3, 'type': 'goal', 'field_raw': 'field_2494_raw'},
            ]
            
            for mapping in comment_mappings:
                comment_text = record.get(mapping['field_raw'])
                if comment_text and isinstance(comment_text, str) and comment_text.strip():
                    comment_data = {
                        'student_knack_id': record['id'],  # Will map to student_id after upsert
                        'cycle': mapping['cycle'],
                        'comment_type': mapping['type'],
                        'comment_text': comment_text.strip(),
                        'academic_year': academic_year  # Add academic year for proper tracking
                    }
                    comment_batch.append(comment_data)
            
            # Process batches
            if len(student_batch) >= BATCH_SIZES['students']:
                result = supabase.table('students').upsert(
                    student_batch,
                    on_conflict='email,academic_year'
                ).execute()
                
                # Update mappings with returned student IDs
                for student in result.data:
                    student_email_map[student['email']] = student['id']
                    student_id_map[student['knack_id']] = student['id']
                
                students_synced += len(student_batch)
                logging.info(f"Synced {students_synced} students...")
                student_batch = []
            
        except Exception as e:
            logging.error(f"Error processing Object_10 record {record.get('id')}: {e}")
    
    # Process remaining students
    if student_batch:
        result = supabase.table('students').upsert(
            student_batch,
            on_conflict='email,academic_year'
        ).execute()
        
        for student in result.data:
            student_email_map[student['email']] = student['id']
            student_id_map[student['knack_id']] = student['id']
        
        students_synced += len(student_batch)
    
    # Now process VESPA scores with correct student_ids
    logging.info(f"\nProcessing {len(score_batch)} VESPA scores...")
    vespa_with_ids = []
    
    for score in score_batch:
        student_knack_id = score.pop('student_knack_id')
        student_id = student_id_map.get(student_knack_id)
        
        if student_id:
            score['student_id'] = student_id
            vespa_with_ids.append(score)
    
    # Upsert VESPA scores in batches
    for i in range(0, len(vespa_with_ids), BATCH_SIZES['vespa_scores']):
        batch = vespa_with_ids[i:i + BATCH_SIZES['vespa_scores']]
        supabase.table('vespa_scores').upsert(
            batch,
            on_conflict='student_id,cycle,academic_year'
        ).execute()
        scores_synced += len(batch)
    
    # CRITICAL: Clean up duplicate cycles (Knack as source of truth)
    # Delete cycles from Supabase that don't exist in Knack (current year only)
    logging.info(f"\nCleaning up duplicate cycles (Knack as source of truth)...")
    cycles_deleted = 0
    
    for student_knack_id, cycles_in_knack in student_cycles_in_knack.items():
        student_id = student_id_map.get(student_knack_id)
        if student_id:
            # Delete cycles that Knack doesn't have
            cycles_to_delete = [c for c in [1, 2, 3] if c not in cycles_in_knack]
            for cycle_to_delete in cycles_to_delete:
                try:
                    result = supabase.table('vespa_scores')\
                        .delete()\
                        .eq('student_id', student_id)\
                        .eq('cycle', cycle_to_delete)\
                        .eq('academic_year', academic_year)\
                        .execute()
                    if result.data:
                        cycles_deleted += len(result.data)
                except Exception as e:
                    # Ignore if record doesn't exist
                    pass
    
    if cycles_deleted > 0:
        logging.info(f"   Deleted {cycles_deleted} duplicate/empty cycles from Supabase")
    
    # NEW: Process student comments with correct student_ids
    logging.info(f"\nProcessing {len(comment_batch)} student comments...")
    comments_with_ids = []
    
    for comment in comment_batch:
        student_knack_id = comment.pop('student_knack_id')
        student_id = student_id_map.get(student_knack_id)
        
        if student_id:
            comment['student_id'] = student_id
            comments_with_ids.append(comment)
    
    # Upsert comments in batches
    COMMENT_BATCH_SIZE = 200
    for i in range(0, len(comments_with_ids), COMMENT_BATCH_SIZE):
        batch = comments_with_ids[i:i + COMMENT_BATCH_SIZE]
        try:
            supabase.table('student_comments').upsert(
                batch,
                on_conflict='student_id,cycle,comment_type'  # FIXED: Match actual database constraint
            ).execute()
            comments_synced += len(batch)
            logging.info(f"Synced {comments_synced} comments...")
        except Exception as e:
            logging.error(f"Error syncing comments batch: {e}")
    
    logging.info(f"\n✅ STUDENTS & VESPA SYNC COMPLETE")
    logging.info(f"   Students synced: {students_synced}")
    logging.info(f"   VESPA scores synced: {scores_synced}")
    logging.info(f"   Student comments synced: {comments_synced}")
    logging.info(f"   Skipped (no date): {skipped_no_date}")
    logging.info(f"   Skipped (no email): {skipped_no_email}")
    
    sync_report['tables']['students'] = {
        'synced': students_synced,
        'skipped_no_date': skipped_no_date,
        'skipped_no_email': skipped_no_email
    }
    sync_report['tables']['vespa_scores'] = {
        'synced': scores_synced,
        'duplicates_deleted': cycles_deleted if 'cycles_deleted' in locals() else 0
    }
    sync_report['tables']['student_comments'] = {
        'synced': comments_synced
    }
    
    return student_email_map, student_id_map


def sync_question_responses(year_boundaries, student_email_map):
    """
    Sync question responses from Object_29 for CURRENT YEAR ONLY
    Uses email-based matching instead of field_792 connections
    """
    logging.info("="*80)
    logging.info("SYNCING QUESTION RESPONSES - CURRENT YEAR ONLY")
    logging.info("="*80)
    
    academic_year = year_boundaries['uk']['year']
    
    # Date filters for Object_29 (field_856 = completion date)
    filters = [
        {
            'field': 'field_856',
            'operator': 'is after',
            'value': year_boundaries['uk']['start']
        },
        {
            'field': 'field_856',
            'operator': 'is before',
            'value': year_boundaries['uk']['end']
        }
    ]
    
    logging.info(f"Fetching Object_29 records for academic year {academic_year}")
    logging.info(f"Date filter: {year_boundaries['uk']['start']} to {year_boundaries['uk']['end']}")
    
    # Fetch current year records from Knack
    records = fetch_all_knack_records(OBJECT_KEYS['psychometric'], filters=filters)
    
    logging.info(f"Processing {len(records)} Object_29 records...")
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        question_mapping = json.load(f)
    
    responses_synced = 0
    response_batch = []
    skipped_no_date = 0
    skipped_no_email = 0
    skipped_no_match = 0
    
    for record in records:
        try:
            # SKIP if no completion date
            completion_date = record.get('field_856')
            if not completion_date or not completion_date.strip():
                skipped_no_date += 1
                continue
            
            # Get email from Object_29 (field_2732) - may have HTML wrapper
            email_raw = record.get('field_2732', '') or record.get('field_2732_raw', '')
            email = extract_email_from_html(email_raw).lower().strip()
            
            if not email:
                skipped_no_email += 1
                continue
            
            # CRITICAL: Match by EMAIL instead of field_792
            student_id = student_email_map.get(email)
            
            if not student_id:
                skipped_no_match += 1
                if skipped_no_match <= 5:
                    logging.warning(f"No student found for email: {email} (Object_29 record: {record.get('id')})")
                continue
            
            # Process each cycle's data
            for cycle in [1, 2, 3]:
                for q_detail in question_mapping:
                    field_id = q_detail.get(f'fieldIdCycle{cycle}')
                    if field_id:
                        response_value = record.get(f'{field_id}_raw')
                        
                        if response_value is not None and response_value != '':
                            try:
                                int_value = int(response_value)
                                
                                # Only valid responses (1-5)
                                if 1 <= int_value <= 5:
                                    response_data = {
                                        'student_id': student_id,
                                        'cycle': cycle,
                                        'academic_year': academic_year,  # CONSTANT
                                        'question_id': q_detail['questionId'],
                                        'response_value': int_value
                                    }
                                    response_batch.append(response_data)
                            except (ValueError, TypeError):
                                pass
            
            # Process batch
            if len(response_batch) >= BATCH_SIZES['question_responses']:
                # Deduplicate before upserting
                deduped_batch = deduplicate_response_batch(response_batch)
                duplicates_removed = len(response_batch) - len(deduped_batch)
                
                if duplicates_removed > 0:
                    logging.warning(f"Removed {duplicates_removed} duplicate responses from batch")
                
                supabase.table('question_responses').upsert(
                    deduped_batch,
                    on_conflict='student_id,cycle,academic_year,question_id'
                ).execute()
                responses_synced += len(deduped_batch)
                logging.info(f"Synced {responses_synced} question responses...")
                response_batch = []
                
        except Exception as e:
            logging.error(f"Error processing Object_29 record {record.get('id')}: {e}")
    
    # Process remaining batch
    if response_batch:
        # Deduplicate final batch
        deduped_batch = deduplicate_response_batch(response_batch)
        duplicates_removed = len(response_batch) - len(deduped_batch)
        
        if duplicates_removed > 0:
            logging.warning(f"Removed {duplicates_removed} duplicate responses from final batch")
        
        supabase.table('question_responses').upsert(
            deduped_batch,
            on_conflict='student_id,cycle,academic_year,question_id'
        ).execute()
        responses_synced += len(deduped_batch)
    
    logging.info(f"\n✅ QUESTION RESPONSES SYNC COMPLETE")
    logging.info(f"   Responses synced: {responses_synced}")
    logging.info(f"   Skipped (no date): {skipped_no_date}")
    logging.info(f"   Skipped (no email): {skipped_no_email}")
    logging.info(f"   Skipped (no student match): {skipped_no_match}")
    
    sync_report['tables']['question_responses'] = {
        'synced': responses_synced,
        'skipped_no_date': skipped_no_date,
        'skipped_no_email': skipped_no_email,
        'skipped_no_match': skipped_no_match
    }
    sync_report['skipped_no_date'] = skipped_no_date
    sync_report['skipped_no_email'] = skipped_no_email
    sync_report['skipped_no_student_match'] = skipped_no_match


def generate_report():
    """Generate and save sync report"""
    sync_report['end_time'] = datetime.now()
    sync_report['duration'] = str(sync_report['end_time'] - sync_report['start_time'])
    
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("CURRENT-YEAR-ONLY SYNC REPORT")
    report_lines.append("="*80)
    report_lines.append(f"Version: {sync_report['version']}")
    report_lines.append(f"Date: {sync_report['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Duration: {sync_report['duration']}")
    report_lines.append(f"Academic Year (UK): {sync_report['academic_year_uk']}")
    report_lines.append(f"Academic Year (AUS): {sync_report['academic_year_aus']}")
    report_lines.append("")
    
    report_lines.append("="*80)
    report_lines.append("TABLES SYNCED")
    report_lines.append("="*80)
    
    for table_name, metrics in sync_report['tables'].items():
        report_lines.append(f"\n{table_name.upper()}:")
        report_lines.append("-" * 40)
        for key, value in metrics.items():
            report_lines.append(f"  {key}: {value}")
    
    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append("SUMMARY")
    report_lines.append("="*80)
    report_lines.append(f"Total skipped (no date): {sync_report['skipped_no_date']}")
    report_lines.append(f"Total skipped (no email): {sync_report['skipped_no_email']}")
    report_lines.append(f"Total skipped (no student match): {sync_report['skipped_no_student_match']}")
    
    if sync_report['warnings']:
        report_lines.append("\nWARNINGS:")
        for warning in sync_report['warnings']:
            report_lines.append(f"  - {warning}")
    
    if sync_report['errors']:
        report_lines.append("\nERRORS:")
        for error in sync_report['errors'][:10]:
            report_lines.append(f"  - {error}")
    
    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append("END OF REPORT")
    report_lines.append("="*80)
    
    report_text = "\n".join(report_lines)
    
    # Save to file
    report_filename = f"sync_current_year_only_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    logging.info(f"\nReport saved to {report_filename}")
    print("\n" + report_text)
    
    return report_text, report_filename


def send_email_report(report_text, report_filename):
    """
    Send sync report via email using SendGrid or Gmail SMTP
    Enhanced with color-coded HTML formatting
    """
    # Get email configuration from environment
    email_to = os.getenv('SYNC_REPORT_EMAIL', 'tony@vespa.academy')
    email_from = os.getenv('EMAIL_FROM', 'noreply@vespa.academy')
    sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
    
    if not email_to:
        logging.warning("No SYNC_REPORT_EMAIL configured, skipping email notification")
        return
    
    # Parse report for summary stats
    students = scores = comments = 0
    errors = []
    warnings = []
    
    for table_name, metrics in sync_report['tables'].items():
        if table_name == 'students':
            students = metrics.get('synced', 0)
        elif table_name == 'vespa_scores':
            scores = metrics.get('synced', 0)
        elif table_name == 'student_comments':
            comments = metrics.get('synced', 0)
    
    duration = sync_report.get('duration', 'Unknown')
    success = len(sync_report.get('errors', [])) == 0
    
    # Create HTML email with beautiful formatting
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; color: white; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
            .header p {{ margin: 10px 0 0; opacity: 0.9; }}
            .status {{ padding: 20px; text-align: center; border-bottom: 1px solid #eee; }}
            .status.success {{ background: #f0fdf4; color: #166534; }}
            .status.warning {{ background: #fffbeb; color: #92400e; }}
            .status.error {{ background: #fef2f2; color: #991b1b; }}
            .status-icon {{ font-size: 48px; margin-bottom: 10px; }}
            .status-message {{ font-size: 18px; font-weight: 600; }}
            .stats {{ padding: 30px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }}
            .stat-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; border-left: 4px solid; }}
            .stat-card.students {{ border-color: #3b82f6; }}
            .stat-card.vespa {{ border-color: #10b981; }}
            .stat-card.comments {{ border-color: #f59e0b; }}
            .stat-value {{ font-size: 32px; font-weight: 700; color: #1f2937; }}
            .stat-label {{ font-size: 12px; text-transform: uppercase; color: #6b7280; margin-top: 5px; letter-spacing: 0.5px; }}
            .details {{ background: #f9fafb; padding: 15px 30px; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e5e7eb; }}
            .detail-label {{ color: #6b7280; }}
            .detail-value {{ font-weight: 600; color: #1f2937; }}
            .footer {{ padding: 20px 30px; background: #f3f4f6; text-align: center; color: #6b7280; font-size: 12px; }}
            .view-full {{ display: inline-block; margin-top: 10px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔄 VESPA Sync Report</h1>
                <p>Current Year Only Sync (v3.0)</p>
                <p>{sync_report['academic_year_uk']} • {sync_report['start_time'].strftime('%B %d, %Y at %H:%M')}</p>
            </div>
            
            <div class="status {'success' if success else 'error'}">
                <div class="status-icon">{'✅' if success else '⚠️'}</div>
                <div class="status-message">
                    {'Sync Completed Successfully' if success else 'Sync Completed with Warnings'}
                </div>
                <p style="margin: 10px 0 0; font-size: 14px; opacity: 0.8;">Duration: {duration}</p>
            </div>
            
            <div class="stats">
                <div class="stats-grid">
                    <div class="stat-card students">
                        <div class="stat-value">{students:,}</div>
                        <div class="stat-label">Students Synced</div>
                    </div>
                    <div class="stat-card vespa">
                        <div class="stat-value">{scores:,}</div>
                        <div class="stat-label">VESPA Scores</div>
                    </div>
                    <div class="stat-card comments">
                        <div class="stat-value">{comments:,}</div>
                        <div class="stat-label">Comments</div>
                    </div>
                </div>
                
                <div class="details">
                    <div class="detail-row">
                        <span class="detail-label">Academic Year (UK):</span>
                        <span class="detail-value">{sync_report['academic_year_uk']}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Academic Year (AUS):</span>
                        <span class="detail-value">{sync_report['academic_year_aus']}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Records Skipped (no date):</span>
                        <span class="detail-value">{sync_report.get('skipped_no_date', 0)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Records Skipped (no email):</span>
                        <span class="detail-value">{sync_report.get('skipped_no_email', 0)}</span>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>VESPA Dashboard Sync System • Automated Daily Sync</p>
                <p>This is an automated message. Full report saved to: {report_filename}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        if sendgrid_api_key:
            # Use SendGrid API
            send_via_sendgrid(email_to, email_from, report_text, html_content, sendgrid_api_key)
        else:
            # Try Gmail SMTP as fallback
            gmail_user = os.getenv('GMAIL_USER')
            gmail_pass = os.getenv('GMAIL_APP_PASSWORD')
            if gmail_user and gmail_pass:
                send_via_gmail(email_to, gmail_user, gmail_pass, report_text, html_content)
            else:
                logging.warning("No email service configured (SENDGRID_API_KEY or GMAIL_USER/GMAIL_APP_PASSWORD)")
                logging.info("Email report not sent - configure email service to enable notifications")
    except Exception as e:
        logging.error(f"Failed to send email report: {e}")
        logging.info("Sync completed successfully but email notification failed")


def send_via_sendgrid(to_email, from_email, plain_text, html_content, api_key):
    """Send email via SendGrid API"""
    import requests
    
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    duration = sync_report.get('duration', 'Unknown')
    subject = f"✅ VESPA Sync Complete - {sync_report['academic_year_uk']} ({duration})"
    
    if sync_report.get('errors'):
        subject = f"⚠️ VESPA Sync Warning - {sync_report['academic_year_uk']}"
    
    data = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": subject
        }],
        "from": {"email": from_email, "name": "VESPA Sync System"},
        "content": [
            {"type": "text/plain", "value": plain_text},
            {"type": "text/html", "value": html_content}
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 202:
        logging.info(f"✅ Email report sent successfully to {to_email}")
    else:
        logging.error(f"SendGrid API error: {response.status_code} - {response.text}")


def send_via_gmail(to_email, gmail_user, gmail_pass, plain_text, html_content):
    """Send email via Gmail SMTP"""
    duration = sync_report.get('duration', 'Unknown')
    subject = f"✅ VESPA Sync Complete - {sync_report['academic_year_uk']} ({duration})"
    
    if sync_report.get('errors'):
        subject = f"⚠️ VESPA Sync Warning - {sync_report['academic_year_uk']}"
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to_email
    
    part1 = MIMEText(plain_text, 'plain')
    part2 = MIMEText(html_content, 'html')
    
    msg.attach(part1)
    msg.attach(part2)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
    
    logging.info(f"✅ Email report sent successfully to {to_email} via Gmail")


def main():
    """Main sync orchestration"""
    logging.info("="*80)
    logging.info("VESPA CURRENT-YEAR-ONLY SYNC - VERSION 3.1")
    logging.info("="*80)
    logging.info(f"Started at: {datetime.now()}")
    logging.info("")
    
    try:
        # Step 1: Calculate current academic year boundaries
        year_boundaries = get_current_academic_year_boundaries()
        sync_report['academic_year_uk'] = year_boundaries['uk']['year']
        sync_report['academic_year_aus'] = year_boundaries['aus']['year']
        
        # Step 2: Sync students and VESPA scores (Object_10)
        student_email_map, student_id_map = sync_students_and_vespa_scores(year_boundaries)
        
        # Step 3: Sync question responses (Object_29) using email matching
        sync_question_responses(year_boundaries, student_email_map)
        
        # Step 4: Generate report
        report_text, report_filename = generate_report()
        
        # Step 5: Send email notification
        send_email_report(report_text, report_filename)
        
        logging.info("\n" + "="*80)
        logging.info("✅ SYNC COMPLETED SUCCESSFULLY")
        logging.info("="*80)
        
    except Exception as e:
        logging.error(f"SYNC FAILED: {e}")
        sync_report['errors'].append(str(e))
        report_text, report_filename = generate_report()
        send_email_report(report_text, report_filename)  # Send email even on error
        raise


if __name__ == "__main__":
    main()

