#!/usr/bin/env python3
"""
Quick test - sync ONLY 10 Academic Profiles to verify the logic works
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
BASE_KNACK_URL = "https://api.knack.com/v1/objects"

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_academic_year(date_str=None):
    """Simple UK academic year calculation"""
    date = datetime.now() if not date_str else datetime.strptime(date_str, '%d/%m/%Y')
    if date.month >= 8:
        return f"{date.year}/{date.year + 1}"
    else:
        return f"{date.year - 1}/{date.year}"

print("\nQuick Test: Syncing first 10 Academic Profiles\n")

# Get establishments
establishments = supabase.table('establishments').select('id', 'knack_id', 'name').execute()
est_map = {e['knack_id']: e for e in establishments.data}
print(f"Loaded {len(est_map)} establishments")

# Fetch ONLY page 1 of Object_112
headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY
}
response = requests.get(
    f"{BASE_KNACK_URL}/object_112/records",
    headers=headers,
    params={'page': 1, 'rows_per_page': 10, 'format': 'raw'}
)
profiles = response.json().get('records', [])
print(f"Fetched {len(profiles)} profiles for testing\n")

success = 0
errors = 0

for idx, profile in enumerate(profiles, 1):
    try:
        # Get account ID
        account_id = profile.get('field_3064')
        if not account_id:
            print(f"{idx}. SKIP - No account ID")
            continue
        
        # Get email from Object_3
        obj3_response = requests.get(
            f'{BASE_KNACK_URL}/object_3/records/{account_id}',
            headers=headers,
            timeout=30
        )
        
        if obj3_response.status_code != 200:
            print(f"{idx}. SKIP - Object_3 query failed")
            continue
        
        student_email = obj3_response.json().get('field_70', '')
        if not student_email:
            print(f"{idx}. SKIP - No email")
            continue
        
        # Get establishment
        vespa_customer = profile.get('field_3069')
        establishment_knack_id = None
        if vespa_customer and isinstance(vespa_customer, list) and len(vespa_customer) > 0:
            establishment_knack_id = vespa_customer[0].get('id')
        
        establishment_data = est_map.get(establishment_knack_id) if establishment_knack_id else None
        establishment_id = establishment_data['id'] if establishment_data else None
        
        # Parse attendance
        attendance_raw = profile.get('field_3076', '')
        attendance_float = None
        if attendance_raw and str(attendance_raw).strip():
            try:
                attendance_str = str(attendance_raw).replace('%', '').strip()
                attendance_float = float(attendance_str) / 100 if attendance_str else None
            except:
                pass
        
        # Parse prior_attainment
        prior_attainment_raw = profile.get('field_3272')
        prior_attainment = None
        if prior_attainment_raw and str(prior_attainment_raw).strip():
            try:
                prior_attainment = float(prior_attainment_raw)
            except:
                pass
        
        # Create profile
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
            'academic_year': calculate_academic_year(),
            'knack_record_id': profile['id']
        }
        
        # Upsert
        profile_result = supabase.table('academic_profiles').upsert(
            profile_data,
            on_conflict='student_email,academic_year'
        ).execute()
        
        profile_id = profile_result.data[0]['id']
        
        # Count subjects
        subject_count = 0
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
                        
                        subject_count += 1
                except:
                    pass
        
        success += 1
        print(f"{idx}. SUCCESS - {student_email} ({profile_data['student_name']}) - {subject_count} subjects")
        
    except Exception as e:
        errors += 1
        print(f"{idx}. ERROR - {profile.get('id')}: {str(e)[:100]}")

print(f"\nTest Complete:")
print(f"  Success: {success}")
print(f"  Errors:  {errors}")
print(f"\nIf successful, run the full sync: python test_academic_profile_sync.py\n")

