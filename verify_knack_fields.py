#!/usr/bin/env python3
"""
Verify Knack field mappings by examining actual data
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-KEY': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

def check_object_fields(object_key, object_name):
    """Fetch and display fields for a Knack object"""
    print(f"\n{'='*60}")
    print(f"OBJECT: {object_key} - {object_name}")
    print('='*60)
    
    # Get one sample record
    url = f"https://api.knack.com/v1/objects/{object_key}/records?rows_per_page=1"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['records']:
            record = data['records'][0]
            print("\nField mappings found:")
            print("-" * 40)
            
            # Sort fields by field number
            field_items = [(k, v) for k, v in record.items() if k.startswith('field_')]
            field_items.sort(key=lambda x: int(x[0].split('_')[1].replace('_raw', '')))
            
            for field_key, field_value in field_items:
                if not field_key.endswith('_raw'):
                    # Skip if empty
                    if not field_value or field_value == '':
                        continue
                        
                    # Get raw value if exists
                    raw_key = f"{field_key}_raw"
                    raw_value = record.get(raw_key, '')
                    
                    # Format output
                    print(f"\n{field_key}:")
                    if isinstance(field_value, str) and len(field_value) > 50:
                        print(f"  Display: {field_value[:50]}...")
                    else:
                        print(f"  Display: {field_value}")
                    
                    if raw_value:
                        if isinstance(raw_value, (dict, list)):
                            print(f"  Raw: {json.dumps(raw_value, indent=4)}")
                        else:
                            print(f"  Raw: {raw_value}")
        else:
            print("No records found in this object")
    else:
        print(f"Error fetching data: {response.status_code}")

def main():
    print("KNACK FIELD VERIFICATION TOOL")
    print("=============================")
    
    # Check each important object
    objects_to_check = [
        ('object_2', 'Establishments'),
        ('object_5', 'Staff Admin Roles'),
        ('object_6', 'Students'),
        ('object_10', 'VESPA Results'),
        ('object_21', 'Super Users'),
        ('object_29', 'Question Responses'),
    ]
    
    for obj_key, obj_name in objects_to_check:
        try:
            check_object_fields(obj_key, obj_name)
        except Exception as e:
            print(f"\nError checking {obj_key}: {e}")
    
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()