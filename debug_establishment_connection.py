#!/usr/bin/env python3
"""
Debug script to understand why establishment_id is NULL in students table
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

def debug_establishment_field():
    """Check how field_133 looks in Object_10 records"""
    print("Debugging establishment connection in Object_10 (VESPA Results)...")
    print("=" * 80)
    
    # Get a few records from Object_10
    url = 'https://api.knack.com/v1/objects/object_10/records'
    params = {
        'page': 1,
        'rows_per_page': 5,
        'fields': 'field_197,field_197_raw,field_133,field_133_raw,field_187,field_187_raw'
    }
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    for i, record in enumerate(data.get('records', []), 1):
        print(f"\nRecord {i} (ID: {record['id']}):")
        print(f"  Student Email (field_197): {record.get('field_197', 'N/A')}")
        print(f"  Student Email Raw: {record.get('field_197_raw', 'N/A')}")
        print(f"  Student Name (field_187): {record.get('field_187', 'N/A')}")
        print(f"  Establishment (field_133): {record.get('field_133', 'N/A')}")
        print(f"  Establishment Raw: {json.dumps(record.get('field_133_raw', 'N/A'), indent=2)}")
        
        # Extract establishment ID if possible
        est_field = record.get('field_133_raw', [])
        if est_field and isinstance(est_field, list) and len(est_field) > 0:
            est_item = est_field[0]
            if isinstance(est_item, dict):
                est_knack_id = est_item.get('id') or est_item.get('value')
                print(f"  ✓ Extracted establishment Knack ID: {est_knack_id}")
            else:
                print(f"  ⚠️  Establishment item is not a dict: {type(est_item)}")
        else:
            print(f"  ❌ No establishment connection found")

if __name__ == "__main__":
    debug_establishment_field()