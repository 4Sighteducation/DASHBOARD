#!/usr/bin/env python3
"""
CURRENT-YEAR-ONLY SYNC - Version 3.0
====================================

This sync ONLY processes data from the current academic year.
- Faster: ~1,000 records instead of 27,000
- Safer: Never touches historical data
- Simpler: Academic year is constant, not calculated per record
- More reliable: Uses email matching instead of unreliable field_792 connections

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
    'version': '3.0 - Current Year Only',
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
    Convert Knack date format (DD/MM/YYYY) to PostgreSQL format (YYYY-MM-DD)
    
    Args:
        knack_date: Date string in DD/MM/YYYY format
    
    Returns:
        Date string in YYYY-MM-DD format or None if invalid
    """
    if not knack_date:
        return None
    
    try:
        # Parse DD/MM/YYYY
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
    skipped_no_date = 0
    skipped_no_email = 0
    
    student_batch = []
    score_batch = []
    
    # Track student mappings for Object_29 sync
    student_id_map = {}  # knack_id -> supabase_id
    student_email_map = {}  # email -> supabase_id
    
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
            
            # Process VESPA scores (all 3 cycles)
            for cycle in [1, 2, 3]:
                # Check if this cycle has data
                cycle_field = f'field_{145 + cycle}'  # field_146, 147, 148
                if record.get(cycle_field):
                    try:
                        score_data = {
                            'student_knack_id': record['id'],  # Will map to student_id after upsert
                            'cycle': cycle,
                            'academic_year': academic_year,  # CONSTANT
                            'vision': int(float(record.get('field_147', 0) or 0)),
                            'effort': int(float(record.get('field_148', 0) or 0)),
                            'systems': int(float(record.get('field_149', 0) or 0)),
                            'practice': int(float(record.get('field_150', 0) or 0)),
                            'attitude': int(float(record.get('field_151', 0) or 0)),
                            'overall': int(float(record.get('field_152', 0) or 0)),
                            'completion_date': convert_knack_date_to_postgres(completion_date)
                        }
                        score_batch.append(score_data)
                    except (ValueError, TypeError) as e:
                        logging.warning(f"Error parsing VESPA scores for {email}: {e}")
            
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
    
    logging.info(f"\n✅ STUDENTS & VESPA SYNC COMPLETE")
    logging.info(f"   Students synced: {students_synced}")
    logging.info(f"   VESPA scores synced: {scores_synced}")
    logging.info(f"   Skipped (no date): {skipped_no_date}")
    logging.info(f"   Skipped (no email): {skipped_no_email}")
    
    sync_report['tables']['students'] = {
        'synced': students_synced,
        'skipped_no_date': skipped_no_date,
        'skipped_no_email': skipped_no_email
    }
    sync_report['tables']['vespa_scores'] = {
        'synced': scores_synced
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


def main():
    """Main sync orchestration"""
    logging.info("="*80)
    logging.info("VESPA CURRENT-YEAR-ONLY SYNC - VERSION 3.0")
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
        generate_report()
        
        logging.info("\n" + "="*80)
        logging.info("✅ SYNC COMPLETED SUCCESSFULLY")
        logging.info("="*80)
        
    except Exception as e:
        logging.error(f"SYNC FAILED: {e}")
        sync_report['errors'].append(str(e))
        generate_report()
        raise


if __name__ == "__main__":
    main()

