#!/usr/bin/env python3
"""
Detailed debug of why only 17K responses are syncing
"""

import os
import requests
from dotenv import load_dotenv
import json
from collections import defaultdict

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

def analyze_sync():
    """Analyze why sync is missing so many responses"""
    print("=" * 60)
    print("ANALYZING SYNC GAPS")
    print("=" * 60)
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        questions = json.load(f)
    
    # Get students from Supabase
    students = supabase.table('students').select('knack_id').execute()
    student_knack_ids = {s['knack_id'] for s in students.data}
    print(f"\nStudents in Supabase: {len(student_knack_ids)}")
    
    # Analyze a sample of Object_29 records
    print("\nFetching Object_29 records with field_792...")
    url = 'https://api.knack.com/v1/objects/object_29/records?page=1&rows_per_page=100'
    url += '&filters=[{"field":"field_792","operator":"is not blank"}]'
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    print(f"Total Object_29 records with field_792: {data.get('total_records', 0)}")
    
    # Analyze records
    stats = {
        'total_records': 0,
        'has_object10_connection': 0,
        'object10_in_students': 0,
        'responses_per_cycle': defaultdict(int),
        'zero_values': 0,
        'non_zero_values': 0,
        'empty_values': 0,
        'expected_responses': 0,
        'actual_responses': 0
    }
    
    for record in data.get('records', [])[:10]:  # Sample first 10
        stats['total_records'] += 1
        
        # Check Object_10 connection
        field_792 = record.get('field_792_raw', [])
        if field_792:
            stats['has_object10_connection'] += 1
            
            # Extract Object_10 ID
            if isinstance(field_792, list) and field_792:
                obj10_item = field_792[0]
                obj10_id = obj10_item.get('id') if isinstance(obj10_item, dict) else obj10_item
                
                if obj10_id in student_knack_ids:
                    stats['object10_in_students'] += 1
        
        # Count responses per cycle
        for cycle in [1, 2, 3]:
            cycle_responses = 0
            for q in questions[:29]:  # First 29 VESPA questions
                field_key = f"{q[f'fieldIdCycle{cycle}']}_raw"
                value = record.get(field_key)
                
                if value is not None and value != '':
                    try:
                        int_val = int(value)
                        if int_val == 0:
                            stats['zero_values'] += 1
                        else:
                            stats['non_zero_values'] += 1
                            cycle_responses += 1
                    except:
                        pass
                else:
                    stats['empty_values'] += 1
            
            if cycle_responses > 0:
                stats['responses_per_cycle'][f'cycle_{cycle}'] += 1
                stats['actual_responses'] += cycle_responses
        
        # Expected if all fields had values
        stats['expected_responses'] += 29 * 3  # 29 questions × 3 cycles
    
    # Print analysis
    print(f"\nAnalysis of {stats['total_records']} sample records:")
    print(f"  Has Object_10 connection: {stats['has_object10_connection']}")
    print(f"  Object_10 ID found in students: {stats['object10_in_students']}")
    print(f"\nResponse Analysis:")
    print(f"  Expected responses (29q × 3c × {stats['total_records']}rec): {stats['expected_responses']}")
    print(f"  Actual non-zero responses: {stats['actual_responses']}")
    print(f"  Percentage captured: {stats['actual_responses']/stats['expected_responses']*100:.1f}%")
    print(f"\nValue Distribution:")
    print(f"  Zero values (skipped): {stats['zero_values']}")
    print(f"  Non-zero values (kept): {stats['non_zero_values']}")
    print(f"  Empty/null values: {stats['empty_values']}")
    print(f"\nRecords with data per cycle:")
    for cycle, count in stats['responses_per_cycle'].items():
        print(f"  {cycle}: {count}/{stats['total_records']} records")
    
    # Check if we're using correct cycle detection
    print("\n" + "=" * 60)
    print("CYCLE DETECTION CHECK")
    print("=" * 60)
    print("\nChecking Q1 values for cycle detection:")
    
    for i, record in enumerate(data.get('records', [])[:3]):
        print(f"\nRecord {i+1}:")
        print(f"  Q1 Cycle 1 (field_1953): {record.get('field_1953_raw', 'EMPTY')}")
        print(f"  Q1 Cycle 2 (field_1955): {record.get('field_1955_raw', 'EMPTY')}")
        print(f"  Q1 Cycle 3 (field_1956): {record.get('field_1956_raw', 'EMPTY')}")

if __name__ == "__main__":
    analyze_sync()