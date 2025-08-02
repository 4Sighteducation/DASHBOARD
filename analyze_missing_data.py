#!/usr/bin/env python3
"""
Analyze why we're missing 97% of expected responses
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

# Supabase
from supabase import create_client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_sample_record():
    """Deep dive into a single Object_29 record"""
    print("=" * 80)
    print("ANALYZING SAMPLE OBJECT_29 RECORD")
    print("=" * 80)
    
    # Get a record that should have Cycle 1 data
    import urllib.parse
    
    base_url = 'https://api.knack.com/v1/objects/object_29/records'
    filters = [
        {"field": "field_1953", "operator": "is not blank"},
        {"field": "field_792", "operator": "is not blank"}
    ]
    
    params = {
        'page': 1,
        'rows_per_page': 1,
        'filters': json.dumps(filters)
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if not data.get('records'):
        print("No records found with both field_1953 and field_792!")
        return
        
    record = data['records'][0]
    record_id = record.get('id')
    
    print(f"\nRecord ID: {record_id}")
    print(f"Email: {record.get('field_2732', 'No email')}")
    
    # Check Object_10 connection
    field_792 = record.get('field_792_raw', [])
    object_10_id = None
    if field_792 and isinstance(field_792, list):
        obj10 = field_792[0]
        object_10_id = obj10.get('id') if isinstance(obj10, dict) else obj10
        print(f"Object_10 ID: {object_10_id}")
    
    # Check if Object_10 is in students
    students = supabase.table('students').select('id').eq('knack_id', object_10_id).execute()
    if students.data:
        print(f"✅ Object_10 found in students table")
        student_id = students.data[0]['id']
    else:
        print(f"❌ Object_10 NOT found in students table!")
        student_id = None
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        questions = json.load(f)
    
    # Analyze responses
    print("\n" + "-" * 60)
    print("CYCLE 1 ANALYSIS:")
    print("-" * 60)
    
    responses_that_would_sync = 0
    responses_skipped_zero = 0
    responses_skipped_empty = 0
    responses_skipped_no_student = 0
    
    for i, q in enumerate(questions[:32]):  # All 32 questions
        field_key = f"{q['fieldIdCycle1']}_raw"
        value = record.get(field_key)
        
        print(f"\nQ{i+1} ({q['questionId']}) - {field_key}:")
        print(f"  Raw value: {value}")
        
        if value is None or value == '':
            print(f"  ❌ EMPTY - would skip")
            responses_skipped_empty += 1
        else:
            try:
                int_val = int(value)
                if int_val == 0:
                    print(f"  ❌ ZERO - would skip (DB constraint)")
                    responses_skipped_zero += 1
                elif not student_id:
                    print(f"  ❌ No student mapping - would skip")
                    responses_skipped_no_student += 1
                else:
                    print(f"  ✅ Would sync: value = {int_val}")
                    responses_that_would_sync += 1
            except:
                print(f"  ❌ Invalid integer - would skip")
    
    print("\n" + "=" * 80)
    print("SUMMARY FOR THIS RECORD:")
    print("=" * 80)
    print(f"Total questions: 32")
    print(f"Would sync: {responses_that_would_sync}")
    print(f"Skipped (zero): {responses_skipped_zero}")
    print(f"Skipped (empty): {responses_skipped_empty}")
    print(f"Skipped (no student): {responses_skipped_no_student}")
    
    if responses_that_would_sync == 0:
        print("\n🚨 This record would contribute ZERO responses!")

if __name__ == "__main__":
    analyze_sample_record()