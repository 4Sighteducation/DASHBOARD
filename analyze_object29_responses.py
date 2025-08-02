#!/usr/bin/env python3
"""
Analyze actual response values in Object_29 records
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

def analyze_responses():
    """Analyze why only 17K responses sync"""
    print("=" * 80)
    print("OBJECT_29 RESPONSE VALUE ANALYSIS")
    print("=" * 80)
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        questions = json.load(f)
    
    # Get sample of Object_29 records WITH field_792
    import urllib.parse
    base_url = 'https://api.knack.com/v1/objects/object_29/records'
    filters = [{"field": "field_792", "operator": "is not blank"}]
    
    params = {
        'page': 1,
        'rows_per_page': 100,
        'filters': json.dumps(filters)
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    response = requests.get(url, headers=headers)
    data = response.json()
    
    print(f"\nTotal Object_29 records with field_792: {data.get('total_records', 0)}")
    print(f"Analyzing {len(data.get('records', []))} sample records...")
    
    # Stats
    stats = {
        'total_possible_responses': 0,
        'responses_by_value': defaultdict(int),
        'empty_responses': 0,
        'zero_responses': 0,
        'valid_responses': 0,
        'records_by_cycle_count': defaultdict(int),
        'responses_per_record': []
    }
    
    # Analyze each record
    for record in data.get('records', []):
        record_responses = 0
        cycles_with_data = set()
        
        # Check all 3 cycles
        for cycle in [1, 2, 3]:
            cycle_has_data = False
            
            # Check first 29 VESPA questions (not outcome questions)
            for q in questions[:29]:
                field_key = f"{q[f'fieldIdCycle{cycle}']}_raw"
                value = record.get(field_key)
                
                stats['total_possible_responses'] += 1
                
                if value is None or value == '':
                    stats['empty_responses'] += 1
                else:
                    try:
                        int_val = int(value)
                        stats['responses_by_value'][int_val] += 1
                        
                        if int_val == 0:
                            stats['zero_responses'] += 1
                        else:
                            stats['valid_responses'] += 1
                            record_responses += 1
                            cycle_has_data = True
                    except:
                        stats['empty_responses'] += 1
            
            if cycle_has_data:
                cycles_with_data.add(cycle)
        
        # Track how many cycles this record has
        stats['records_by_cycle_count'][len(cycles_with_data)] += 1
        stats['responses_per_record'].append(record_responses)
    
    # Print results
    print("\n" + "-" * 60)
    print("RESPONSE VALUE DISTRIBUTION:")
    print("-" * 60)
    
    total_checked = stats['total_possible_responses']
    print(f"Total response fields checked: {total_checked}")
    print(f"  Empty/null: {stats['empty_responses']} ({stats['empty_responses']/total_checked*100:.1f}%)")
    print(f"  Zero values: {stats['zero_responses']} ({stats['zero_responses']/total_checked*100:.1f}%)")
    print(f"  Valid (1-5): {stats['valid_responses']} ({stats['valid_responses']/total_checked*100:.1f}%)")
    
    print("\nValue distribution:")
    for value in sorted(stats['responses_by_value'].keys()):
        count = stats['responses_by_value'][value]
        print(f"  Value {value}: {count} ({count/total_checked*100:.1f}%)")
    
    print("\n" + "-" * 60)
    print("RECORDS BY CYCLE COUNT:")
    print("-" * 60)
    
    total_records = len(data.get('records', []))
    for cycles, count in sorted(stats['records_by_cycle_count'].items()):
        print(f"  {cycles} cycle(s): {count} records ({count/total_records*100:.1f}%)")
    
    # Calculate average responses per record
    avg_responses = sum(stats['responses_per_record']) / len(stats['responses_per_record'])
    print(f"\nAverage valid responses per record: {avg_responses:.1f}")
    
    # Extrapolate
    print("\n" + "=" * 80)
    print("EXTRAPOLATION TO FULL DATASET:")
    print("=" * 80)
    
    total_object29 = data.get('total_records', 0)
    valid_rate = stats['valid_responses'] / total_checked
    
    print(f"\nIf {valid_rate*100:.1f}% valid response rate applies to all {total_object29} records:")
    print(f"  Expected responses: {int(total_object29 * 29 * 1.5 * valid_rate):,}")
    print(f"  Actual synced: 17,062")
    
    if avg_responses < 1:
        print(f"\n🚨 Average responses per record is {avg_responses:.1f}!")
        print("   Most records have NO valid responses!")

if __name__ == "__main__":
    analyze_responses()