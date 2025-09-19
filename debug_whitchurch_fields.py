"""
Debug script to find which fields actually contain data in Whitchurch Object_29 records
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

def find_actual_fields():
    """Find which fields actually contain statement score data"""
    
    # Whitchurch High School ID
    establishment_id = '632b24b58823310021000a72'
    
    print(f"Analyzing Whitchurch High School Object_29 records...")
    print(f"Establishment ID: {establishment_id}")
    print("=" * 60)
    
    filters = [
        {
            'field': 'field_1821',  # Establishment connection field
            'operator': 'is',
            'value': establishment_id
        }
    ]
    
    # Get first few records to analyze
    data = make_knack_request('object_29', filters=filters, page=1, rows_per_page=5)
    records = data.get('records', [])
    
    if not records:
        print("No records found!")
        return
    
    print(f"\nAnalyzing {len(records)} records...")
    
    # Find all fields that contain numeric values 1-5 (likely statement scores)
    statement_fields = Counter()
    all_field_samples = {}
    
    for i, record in enumerate(records, 1):
        print(f"\n{'='*60}")
        print(f"RECORD {i}:")
        email = record.get('field_2732', '') or record.get('field_2732_raw', '')
        print(f"Email: {email}")
        
        # Look for fields with values 1-5
        numeric_fields = []
        for field_id, value in record.items():
            # Check _raw fields for numeric values
            if field_id.endswith('_raw') and isinstance(value, (int, float)):
                if 1 <= value <= 5:  # Likely a statement score
                    base_field = field_id.replace('_raw', '')
                    numeric_fields.append((base_field, value))
                    statement_fields[base_field] += 1
                    
                    # Store sample for analysis
                    if base_field not in all_field_samples:
                        all_field_samples[base_field] = []
                    all_field_samples[base_field].append(value)
        
        print(f"Found {len(numeric_fields)} fields with values 1-5")
        
        # Group by field number range to identify cycles
        if numeric_fields:
            # Sort by field number
            sorted_fields = sorted(numeric_fields, key=lambda x: int(x[0].replace('field_', '')))
            
            # Show first and last few to understand range
            print("\nFirst 10 statement fields:")
            for field, value in sorted_fields[:10]:
                print(f"  {field}: {value}")
            
            if len(sorted_fields) > 20:
                print("\n...")
                print("\nLast 10 statement fields:")
                for field, value in sorted_fields[-10:]:
                    print(f"  {field}: {value}")
    
    print(f"\n{'='*60}")
    print("FIELD ANALYSIS SUMMARY")
    print("=" * 60)
    
    # Find fields that appear in all records (likely the actual question fields)
    consistent_fields = [field for field, count in statement_fields.items() if count == len(records)]
    
    print(f"\nFields with statement scores in ALL {len(records)} records: {len(consistent_fields)}")
    
    if consistent_fields:
        # Sort and group by ranges
        sorted_consistent = sorted(consistent_fields, key=lambda x: int(x.replace('field_', '')))
        
        # Try to identify cycles based on field number ranges
        print("\nField ranges (might indicate cycles):")
        
        # Simple grouping by gaps
        groups = []
        current_group = [sorted_consistent[0]]
        
        for i in range(1, len(sorted_consistent)):
            current_num = int(sorted_consistent[i].replace('field_', ''))
            prev_num = int(sorted_consistent[i-1].replace('field_', ''))
            
            if current_num - prev_num > 50:  # Big gap might indicate new cycle
                groups.append(current_group)
                current_group = [sorted_consistent[i]]
            else:
                current_group.append(sorted_consistent[i])
        
        groups.append(current_group)
        
        for i, group in enumerate(groups, 1):
            if group:
                first = group[0]
                last = group[-1]
                print(f"\nGroup {i}: {first} to {last} ({len(group)} fields)")
                print(f"  Sample fields: {', '.join(group[:5])}")
    
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS:")
    print("=" * 60)
    
    if consistent_fields:
        print("\n1. The actual statement score fields appear to be:")
        print(f"   Range: {sorted_consistent[0]} to {sorted_consistent[-1]}")
        print(f"   Total: {len(sorted_consistent)} fields")
        
        print("\n2. These do NOT match the fields in psychometric_question_details.json:")
        print("   Expected: field_1953 to field_2045 (from JSON)")
        print(f"   Actual: {sorted_consistent[0]} to {sorted_consistent[-1]} (from data)")
        
        print("\n3. You need to update the field mappings in psychometric_question_details.json")
        print("   or use a different approach to detect cycles for this establishment.")
    else:
        print("\nNo consistent statement fields found. The data structure might be different")
        print("for this establishment, or there might be no actual statement scores stored.")

if __name__ == "__main__":
    find_actual_fields()

