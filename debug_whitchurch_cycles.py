"""
Debug script to analyze Whitchurch High School Object_29 records
and understand why cycles aren't being detected properly
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
from collections import Counter

# Load environment variables
load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
KNACK_API_URL = "https://api.knack.com/v1/objects"

def make_knack_request(object_key: str, filters=None, page: int = 1, rows_per_page: int = 1000):
    """Make a request to Knack API"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"{KNACK_API_URL}/{object_key}/records"
    params = {
        'page': page,
        'rows_per_page': rows_per_page
    }
    
    if filters:
        params['filters'] = json.dumps(filters)
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def analyze_whitchurch():
    """Analyze Whitchurch High School Object_29 records"""
    
    # Whitchurch High School ID from your output
    establishment_id = '632b24b58823310021000a72'
    
    print(f"Fetching Object_29 records for Whitchurch High School...")
    print(f"Establishment ID: {establishment_id}")
    print("=" * 60)
    
    filters = [
        {
            'field': 'field_1821',  # Establishment connection field
            'operator': 'is',
            'value': establishment_id
        }
    ]
    
    # Get first page to analyze structure
    data = make_knack_request('object_29', filters=filters, page=1, rows_per_page=10)
    records = data.get('records', [])
    
    if not records:
        print("No records found!")
        return
    
    print(f"\nAnalyzing first {len(records)} records to understand structure...")
    print("=" * 60)
    
    # Load question mappings
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        questions = json.load(f)
    
    # Get all cycle field IDs
    cycle1_fields = []
    cycle2_fields = []
    cycle3_fields = []
    
    for q in questions:
        if q['vespaCategory'] != 'NA_OUTCOME':
            cycle1_fields.append(q.get('fieldIdCycle1'))
            cycle2_fields.append(q.get('fieldIdCycle2'))
            cycle3_fields.append(q.get('fieldIdCycle3'))
    
    print(f"\nExpected field IDs per cycle:")
    print(f"Cycle 1 fields: {cycle1_fields[:5]}... ({len(cycle1_fields)} total)")
    print(f"Cycle 2 fields: {cycle2_fields[:5]}... ({len(cycle2_fields)} total)")
    print(f"Cycle 3 fields: {cycle3_fields[:5]}... ({len(cycle3_fields)} total)")
    
    # Analyze each record
    for i, record in enumerate(records[:5], 1):
        print(f"\n{'='*60}")
        print(f"RECORD {i}:")
        
        # Get email
        email = record.get('field_2732', '') or record.get('field_2732_raw', '')
        print(f"Email: {email}")
        
        # Check all fields in the record
        all_fields = list(record.keys())
        print(f"Total fields in record: {len(all_fields)}")
        
        # Check each cycle
        for cycle_num, cycle_fields in [(1, cycle1_fields), (2, cycle2_fields), (3, cycle3_fields)]:
            print(f"\n  Cycle {cycle_num} Analysis:")
            
            # Count how many fields have data
            fields_with_data = 0
            sample_values = []
            
            for field_id in cycle_fields:
                if field_id:
                    # Check both regular and _raw versions
                    has_value = False
                    value = None
                    
                    if field_id in record:
                        value = record[field_id]
                        has_value = bool(value)
                    
                    raw_field = f"{field_id}_raw"
                    if raw_field in record:
                        raw_value = record[raw_field]
                        if raw_value:
                            has_value = True
                            value = raw_value
                    
                    if has_value:
                        fields_with_data += 1
                        if len(sample_values) < 3:  # Show first 3 values as examples
                            sample_values.append(f"{field_id}={value}")
            
            print(f"    Fields with data: {fields_with_data}/{len(cycle_fields)}")
            if sample_values:
                print(f"    Sample values: {', '.join(sample_values)}")
            else:
                print(f"    No data found for this cycle")
        
        # Also check the special cycle indicator fields
        print(f"\n  Special cycle fields check:")
        print(f"    field_1953 (Cycle 1 indicator?): {record.get('field_1953', 'NOT PRESENT')}")
        print(f"    field_1955 (Cycle 2 indicator?): {record.get('field_1955', 'NOT PRESENT')}")
        print(f"    field_1956 (Cycle 3 indicator?): {record.get('field_1956', 'NOT PRESENT')}")
    
    # Now analyze ALL records for cycle distribution
    print(f"\n{'='*60}")
    print("FULL DATASET ANALYSIS")
    print("=" * 60)
    
    all_records = []
    page = 1
    
    while True:
        data = make_knack_request('object_29', filters=filters, page=page)
        records = data.get('records', [])
        if not records:
            break
        all_records.extend(records)
        if len(records) < 1000:
            break
        page += 1
    
    print(f"Total records: {len(all_records)}")
    
    # Analyze cycle distribution
    cycle_distribution = Counter()
    
    for record in all_records:
        cycles_with_data = []
        
        for cycle_num, cycle_fields in [(1, cycle1_fields), (2, cycle2_fields), (3, cycle3_fields)]:
            has_data = False
            
            for field_id in cycle_fields:
                if field_id:
                    if record.get(f"{field_id}_raw") or record.get(field_id):
                        has_data = True
                        break
            
            if has_data:
                cycles_with_data.append(str(cycle_num))
        
        if cycles_with_data:
            cycle_key = ','.join(cycles_with_data)
        else:
            cycle_key = 'none'
        
        cycle_distribution[cycle_key] += 1
    
    print(f"\nCycle Distribution:")
    for cycles, count in sorted(cycle_distribution.items()):
        print(f"  Cycles {cycles}: {count} students")
    
    # Count students with 2+ cycles
    students_with_2_plus = sum(count for cycles, count in cycle_distribution.items() 
                              if cycles != 'none' and ',' in cycles)
    print(f"\nStudents with 2+ cycles: {students_with_2_plus}")

if __name__ == "__main__":
    analyze_whitchurch()
