#!/usr/bin/env python3
"""
Test script to sync ONLY Academic Profiles from Knack Object_112 to Supabase
This tests the sync_academic_profiles() function without running the full sync
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_academic_profile_sync.log', encoding='utf-8'),
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

def make_knack_request(object_key, page=1, rows_per_page=1000):
    """Make a request to Knack API with pagination"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"{BASE_KNACK_URL}/{object_key}/records"
    params = {
        'page': page,
        'rows_per_page': rows_per_page,
        'format': 'raw'
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=90)
    response.raise_for_status()
    return response.json()

def fetch_all_knack_records(object_key):
    """Fetch all records from a Knack object"""
    all_records = []
    page = 1
    
    while True:
        logging.info(f"Fetching {object_key} page {page}...")
        data = make_knack_request(object_key, page=page)
        
        records = data.get('records', [])
        all_records.extend(records)
        
        total_pages = data.get('total_pages', 1)
        if page >= total_pages or not records:
            break
            
        page += 1
    
    logging.info(f"Fetched {len(all_records)} total records")
    return all_records

def calculate_academic_year(date_str, establishment_id=None, is_australian=False, use_standard_year=None):
    """Calculate academic year based on date"""
    if not date_str:
        date = datetime.now()
    else:
        try:
            date = datetime.strptime(date_str, '%d/%m/%Y')
        except:
            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                date = datetime.now()
    
    # Use standard UK calculation if use_standard_year is None or True
    if use_standard_year is None or use_standard_year == True:
        if date.month >= 8:
            return f"{date.year}/{date.year + 1}"
        else:
            return f"{date.year - 1}/{date.year}"
    elif is_australian:
        # Australian: Calendar year
        return f"{date.year}/{date.year}"
    else:
        # UK: Academic year
        if date.month >= 8:
            return f"{date.year}/{date.year + 1}"
        else:
            return f"{date.year - 1}/{date.year}"

def test_sync_academic_profiles():
    """Test syncing academic profiles from Object_112"""
    logging.info("=" * 80)
    logging.info("TEST: Academic Profile Sync from Knack Object_112")
    logging.info("=" * 80)
    
    start_time = datetime.now()
    
    try:
        # Get counts before
        before_profiles = supabase.table('academic_profiles').select('id', count='exact').execute()
        before_subjects = supabase.table('student_subjects').select('id', count='exact').execute()
        
        logging.info(f"Before sync: {before_profiles.count} profiles, {before_subjects.count} subjects")
        
        # Get establishment mapping
        establishments = supabase.table('establishments').select('id', 'knack_id', 'is_australian', 'use_standard_year').execute()
        est_map = {e['knack_id']: e for e in establishments.data}
        logging.info(f"Loaded {len(est_map)} establishments")
        
        # Fetch all Object_112 records
        logging.info("Fetching Object_112 records...")
        profiles = fetch_all_knack_records('object_112')
        logging.info(f"Found {len(profiles)} profiles in Knack")
        
        profiles_synced = 0
        subjects_synced = 0
        errors = 0
        
        for profile in profiles:
            try:
                # Get account ID from field_3064
                account_id = profile.get('field_3064')
                if not account_id:
                    continue
                
                # Query Object_3 to get email
                obj3_response = requests.get(
                    f'{BASE_KNACK_URL}/object_3/records/{account_id}',
                    headers={
                        'X-Knack-Application-Id': KNACK_APP_ID,
                        'X-Knack-REST-API-Key': KNACK_API_KEY
                    },
                    timeout=30
                )
                
                if obj3_response.status_code != 200:
                    continue
                
                obj3_data = obj3_response.json()
                student_email = obj3_data.get('field_70', '')
                if not student_email:
                    continue
                
                # Get establishment
                vespa_customer = profile.get('field_3069')
                establishment_knack_id = None
                if vespa_customer and isinstance(vespa_customer, list) and len(vespa_customer) > 0:
                    establishment_knack_id = vespa_customer[0].get('id')
                
                establishment_data = est_map.get(establishment_knack_id) if establishment_knack_id else None
                establishment_id = establishment_data['id'] if establishment_data else None
                
                # Calculate academic year
                academic_year = calculate_academic_year(
                    datetime.now().strftime('%d/%m/%Y'),
                    establishment_id,
                    establishment_data.get('is_australian') if establishment_data else False,
                    establishment_data.get('use_standard_year') if establishment_data else None
                )
                
                # Parse attendance
                attendance_raw = profile.get('field_3076', '')
                attendance_float = None
                if attendance_raw and str(attendance_raw).strip():
                    try:
                        attendance_str = str(attendance_raw).replace('%', '').strip()
                        attendance_float = float(attendance_str) / 100 if attendance_str else None
                    except (ValueError, TypeError):
                        pass
                
                # Parse prior_attainment - convert empty strings to None
                prior_attainment_raw = profile.get('field_3272')
                prior_attainment = None
                if prior_attainment_raw and str(prior_attainment_raw).strip():
                    try:
                        prior_attainment = float(prior_attainment_raw)
                    except (ValueError, TypeError):
                        pass
                
                # Create profile record
                profile_data = {
                    'student_email': student_email,
                    'student_name': profile.get('field_3066', ''),
                    'year_group': profile.get('field_3078', ''),
                    'tutor_group': profile.get('field_3077', ''),
                    'attendance': attendance_float,
                    'prior_attainment': prior_attainment,
                    'upn': profile.get('field_3137', ''),
                    'uci': profile.get('field_3136', ''),
                    'centre_number': profile.get('field_3138', ''),
                    'establishment_name': establishment_data.get('name') if establishment_data else 'Unknown',
                    'establishment_id': establishment_id,
                    'academic_year': academic_year,
                    'knack_record_id': profile['id']
                }
                
                # Upsert profile
                profile_result = supabase.table('academic_profiles').upsert(
                    profile_data,
                    on_conflict='student_email,academic_year'
                ).execute()
                
                profile_id = profile_result.data[0]['id']
                profiles_synced += 1
                
                # Log first few for verification
                if profiles_synced <= 3:
                    logging.info(f"  ✓ Synced: {student_email} - {profile_data['student_name']}")
                
                # Process subjects
                for position in range(1, 16):
                    field_key = f'field_{3079 + position}'
                    subject_json_str = profile.get(field_key)
                    
                    if subject_json_str and subject_json_str.strip():
                        try:
                            subject_data = json.loads(subject_json_str)
                            if subject_data.get('subject'):
                                subject_record = {
                                    'profile_id': profile_id,
                                    'subject_name': subject_data.get('subject'),
                                    'exam_type': subject_data.get('examType'),
                                    'exam_board': subject_data.get('examBoard'),
                                    'current_grade': subject_data.get('currentGrade'),
                                    'target_grade': subject_data.get('targetGrade'),
                                    'minimum_expected_grade': subject_data.get('minimumExpectedGrade'),
                                    'subject_target_grade': subject_data.get('subjectTargetGrade'),
                                    'effort_grade': subject_data.get('effortGrade'),
                                    'behaviour_grade': subject_data.get('behaviourGrade'),
                                    'subject_attendance': subject_data.get('subjectAttendance'),
                                    'subject_position': position,
                                    'original_record_id': subject_data.get('originalRecordId')
                                }
                                
                                supabase.table('student_subjects').upsert(
                                    subject_record,
                                    on_conflict='profile_id,subject_position'
                                ).execute()
                                
                                subjects_synced += 1
                                
                        except json.JSONDecodeError:
                            pass
                
                # Progress indicator every 100 profiles
                if profiles_synced % 100 == 0:
                    logging.info(f"  Progress: {profiles_synced}/{len(profiles)} profiles synced...")
                
            except Exception as e:
                logging.error(f"Error syncing profile {profile.get('id')}: {e}")
                errors += 1
        
        # Get final counts
        after_profiles = supabase.table('academic_profiles').select('id', count='exact').execute()
        after_subjects = supabase.table('student_subjects').select('id', count='exact').execute()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Summary
        logging.info("=" * 80)
        logging.info("SYNC COMPLETE")
        logging.info("=" * 80)
        logging.info(f"Duration: {duration}")
        logging.info(f"")
        logging.info(f"Academic Profiles:")
        logging.info(f"  Before: {before_profiles.count}")
        logging.info(f"  After:  {after_profiles.count}")
        logging.info(f"  Synced: {profiles_synced}")
        logging.info(f"  New:    {after_profiles.count - before_profiles.count}")
        logging.info(f"")
        logging.info(f"Student Subjects:")
        logging.info(f"  Before: {before_subjects.count}")
        logging.info(f"  After:  {after_subjects.count}")
        logging.info(f"  Synced: {subjects_synced}")
        logging.info(f"  New:    {after_subjects.count - before_subjects.count}")
        logging.info(f"")
        logging.info(f"Errors: {errors}")
        logging.info("=" * 80)
        
        return True
        
    except Exception as e:
        logging.error(f"Test sync failed: {e}")
        raise

if __name__ == "__main__":
    print("\nTesting Academic Profile Sync (Object_112 -> Supabase)\n")
    test_sync_academic_profiles()
    print("\nTest complete! Check logs above for details.\n")

