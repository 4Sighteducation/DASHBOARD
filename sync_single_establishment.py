#!/usr/bin/env python3
"""
SINGLE ESTABLISHMENT REAL-TIME SYNC
====================================

Syncs data for ONE establishment only - designed for on-demand refresh button.
Typically completes in 30-60 seconds for average school.

Usage:
    python sync_single_establishment.py --establishment-id <knack_id>
    
Or call from API endpoint for real-time dashboard refresh.
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
BASE_KNACK_URL = "https://api.knack.com/v1/objects"

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def make_knack_request(object_key, filters=None, page=1, rows_per_page=1000):
    """Make request to Knack API with filters"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"{BASE_KNACK_URL}/{object_key}/records"
    params = {'page': page, 'rows_per_page': rows_per_page}
    
    if filters:
        params['filters'] = json.dumps(filters)
    
    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def get_current_academic_year():
    """Calculate current academic year"""
    now = datetime.now()
    year = now.year
    month = now.month
    
    # UK academic year: Aug 1 - Jul 31
    if month >= 8:
        return f"{year}/{year + 1}"
    else:
        return f"{year - 1}/{year}"


def sync_establishment(establishment_knack_id):
    """
    Sync all current year data for a single establishment
    
    Returns:
        dict: Summary of sync operation
    """
    start_time = datetime.now()
    logging.info(f"Starting sync for establishment: {establishment_knack_id}")
    
    # Get establishment UUID
    est_result = supabase.table('establishments').select('id, name').eq('knack_id', establishment_knack_id).execute()
    
    if not est_result.data:
        raise ValueError(f"Establishment not found: {establishment_knack_id}")
    
    establishment = est_result.data[0]
    est_uuid = establishment['id']
    est_name = establishment['name']
    
    logging.info(f"Establishment: {est_name} (UUID: {est_uuid})")
    
    # Get current academic year
    academic_year = get_current_academic_year()
    logging.info(f"Academic Year: {academic_year}")
    
    # Calculate date boundaries
    now = datetime.now()
    year = now.year
    month = now.month
    
    if month >= 8:  # Aug-Dec
        start_date = f"01/08/{year}"
        end_date = f"31/07/{year + 1}"
    else:  # Jan-Jul
        start_date = f"01/08/{year - 1}"
        end_date = f"31/07/{year}"
    
    # Build filters for this establishment + current academic year
    filters = {
        'match': 'and',
        'rules': [
            {
                'field': 'field_133',  # Establishment
                'operator': 'is',
                'value': establishment_knack_id
            },
            {
                'field': 'field_855',  # Completion date
                'operator': 'is after',
                'value': start_date
            },
            {
                'field': 'field_855',
                'operator': 'is before',
                'value': end_date
            }
        ]
    }
    
    # Fetch Object_10 records for this establishment
    logging.info("Fetching VESPA records from Knack...")
    
    all_records = []
    page = 1
    
    while True:
        data = make_knack_request('object_10', filters=filters, page=page, rows_per_page=1000)
        records = data.get('records', [])
        
        if not records:
            break
        
        all_records.extend(records)
        logging.info(f"Fetched page {page}: {len(records)} records (total: {len(all_records)})")
        
        if len(records) < 1000:
            break
        
        page += 1
    
    logging.info(f"Total records fetched: {len(all_records)}")
    
    # Process students, VESPA scores, and comments
    students_synced = 0
    scores_synced = 0
    comments_synced = 0
    
    student_batch = []
    score_batch = []
    comment_batch = []
    student_email_map = {}
    student_id_map = {}
    
    for record in all_records:
        # Extract email
        email_field = record.get('field_197_raw') or record.get('field_197', {})
        email = email_field.get('email') if isinstance(email_field, dict) else None
        
        if not email:
            continue
        
        # Student data
        student_data = {
            'knack_id': record['id'],
            'email': email.lower(),
            'name': f"{record.get('field_187_raw', {}).get('first', '')} {record.get('field_187_raw', {}).get('last', '')}".strip(),
            'establishment_id': est_uuid,
            'academic_year': academic_year,
            'year_group': str(record.get('field_144_raw', '')),
            'group': str(record.get('field_223_raw', '')) if record.get('field_223_raw') else None,
            'faculty': str(record.get('field_782_raw', '')) if record.get('field_782_raw') else None
        }
        
        student_batch.append(student_data)
        
        # VESPA scores for all 3 cycles
        for cycle in [1, 2, 3]:
            cycle_field = f'field_{145 + cycle}'
            if record.get(cycle_field):
                score_data = {
                    'student_knack_id': record['id'],
                    'cycle': cycle,
                    'academic_year': academic_year,
                    'vision': int(float(record.get(f'field_{146 + (cycle-1)*6}', 0) or 0)),
                    'effort': int(float(record.get(f'field_{147 + (cycle-1)*6}', 0) or 0)),
                    'systems': int(float(record.get(f'field_{148 + (cycle-1)*6}', 0) or 0)),
                    'practice': int(float(record.get(f'field_{149 + (cycle-1)*6}', 0) or 0)),
                    'attitude': int(float(record.get(f'field_{150 + (cycle-1)*6}', 0) or 0)),
                    'overall': int(float(record.get(f'field_{151 + (cycle-1)*6}', 0) or 0))
                }
                score_batch.append(score_data)
        
        # Comments
        comment_mappings = [
            {'cycle': 1, 'type': 'rrc', 'field': 'field_2302_raw'},
            {'cycle': 1, 'type': 'goal', 'field': 'field_2499_raw'},
            {'cycle': 2, 'type': 'rrc', 'field': 'field_2303_raw'},
            {'cycle': 2, 'type': 'goal', 'field': 'field_2493_raw'},
            {'cycle': 3, 'type': 'rrc', 'field': 'field_2304_raw'},
            {'cycle': 3, 'type': 'goal', 'field': 'field_2494_raw'},
        ]
        
        for mapping in comment_mappings:
            comment_text = record.get(mapping['field'])
            if comment_text and isinstance(comment_text, str) and comment_text.strip():
                comment_batch.append({
                    'student_knack_id': record['id'],
                    'cycle': mapping['cycle'],
                    'comment_type': mapping['type'],
                    'comment_text': comment_text.strip(),
                    'academic_year': academic_year
                })
    
    # Upsert students
    logging.info(f"Upserting {len(student_batch)} students...")
    result = supabase.table('students').upsert(
        student_batch,
        on_conflict='email,academic_year'
    ).execute()
    
    # Map student IDs
    for student in result.data:
        student_email_map[student['email']] = student['id']
        student_id_map[student['knack_id']] = student['id']
    
    students_synced = len(result.data)
    
    # Process VESPA scores
    logging.info(f"Processing {len(score_batch)} VESPA scores...")
    vespa_with_ids = []
    
    for score in score_batch:
        student_knack_id = score.pop('student_knack_id')
        student_id = student_id_map.get(student_knack_id)
        if student_id:
            score['student_id'] = student_id
            vespa_with_ids.append(score)
    
    if vespa_with_ids:
        supabase.table('vespa_scores').upsert(
            vespa_with_ids,
            on_conflict='student_id,cycle,academic_year'
        ).execute()
        scores_synced = len(vespa_with_ids)
    
    # Process comments
    logging.info(f"Processing {len(comment_batch)} comments...")
    comments_with_ids = []
    
    for comment in comment_batch:
        student_knack_id = comment.pop('student_knack_id')
        student_id = student_id_map.get(student_knack_id)
        if student_id:
            comment['student_id'] = student_id
            comments_with_ids.append(comment)
    
    if comments_with_ids:
        supabase.table('student_comments').upsert(
            comments_with_ids,
            on_conflict='student_id,cycle,comment_type'
        ).execute()
        comments_synced = len(comments_with_ids)
    
    duration = datetime.now() - start_time
    
    summary = {
        'success': True,
        'establishment_name': est_name,
        'establishment_id': establishment_knack_id,
        'academic_year': academic_year,
        'duration_seconds': duration.total_seconds(),
        'students_synced': students_synced,
        'vespa_scores_synced': scores_synced,
        'comments_synced': comments_synced,
        'timestamp': datetime.now().isoformat()
    }
    
    logging.info(f"\n✅ Sync complete for {est_name}")
    logging.info(f"   Students: {students_synced}")
    logging.info(f"   VESPA Scores: {scores_synced}")
    logging.info(f"   Comments: {comments_synced}")
    logging.info(f"   Duration: {duration}")
    
    return summary


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync single establishment')
    parser.add_argument('--establishment-id', required=True, help='Knack establishment ID')
    args = parser.parse_args()
    
    try:
        summary = sync_establishment(args.establishment_id)
        print("\n" + json.dumps(summary, indent=2))
    except Exception as e:
        logging.error(f"Sync failed: {e}")
        raise


if __name__ == "__main__":
    main()

