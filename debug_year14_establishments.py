#!/usr/bin/env python3
"""
Debug script to investigate why Year 14 students have NULL establishment_id
"""

import os
import requests
from dotenv import load_dotenv
import json
from supabase import create_client, Client

load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_year14_establishments():
    """Check Year 14 records and their establishments"""
    print("Debugging Year 14 establishment connections...")
    print("=" * 80)
    
    # Get Year 14 records from Object_10 with establishments
    url = 'https://api.knack.com/v1/objects/object_10/records'
    
    # Search for Year 14 students
    filters = {
        "match": "and",
        "rules": [
            {
                "field": "field_144",  # year_group field
                "operator": "is",
                "value": "14"
            }
        ]
    }
    
    params = {
        'page': 1,
        'rows_per_page': 5,
        'filters': json.dumps(filters),
        'fields': 'field_197,field_197_raw,field_133,field_133_raw,field_187,field_187_raw,field_144'
    }
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    print(f"Found {data.get('total_records', 0)} Year 14 records in Object_10\n")
    
    # Track unique establishment IDs
    est_knack_ids = set()
    
    for i, record in enumerate(data.get('records', []), 1):
        print(f"\nRecord {i} (ID: {record['id']}):")
        print(f"  Year Group: {record.get('field_144', 'N/A')}")
        print(f"  Student Email: {record.get('field_197', 'N/A')}")
        print(f"  Student Name: {record.get('field_187', 'N/A')}")
        print(f"  Establishment Display: {record.get('field_133', 'N/A')}")
        
        # Extract establishment ID
        est_field = record.get('field_133_raw', [])
        if est_field and isinstance(est_field, list) and len(est_field) > 0:
            est_item = est_field[0]
            if isinstance(est_item, dict):
                est_knack_id = est_item.get('id') or est_item.get('value')
                print(f"  ✓ Establishment Knack ID: {est_knack_id}")
                print(f"    Raw structure: {json.dumps(est_item, indent=4)}")
                est_knack_ids.add(est_knack_id)
            else:
                print(f"  ⚠️  Unexpected establishment format: {type(est_item)} - {est_item}")
        else:
            print(f"  ❌ No establishment found in field_133_raw")
    
    # Now check if these establishments exist in Supabase
    print("\n" + "=" * 80)
    print("Checking if these establishments exist in Supabase...")
    
    for est_id in est_knack_ids:
        result = supabase.table('establishments').select('id', 'name', 'knack_id').eq('knack_id', est_id).execute()
        
        if result.data:
            print(f"✓ Found {est_id} in Supabase: {result.data[0]['name']}")
        else:
            print(f"❌ NOT FOUND {est_id} in Supabase - THIS IS THE PROBLEM!")
            
            # Try to find this establishment in Knack
            est_url = f'https://api.knack.com/v1/objects/object_2/records/{est_id}'
            est_response = requests.get(est_url, headers=headers)
            if est_response.status_code == 200:
                est_data = est_response.json()
                print(f"   Found in Knack Object_2: {est_data.get('field_5', 'Unknown name')}")
                print(f"   This establishment needs to be synced to Supabase!")
            else:
                print(f"   Could not fetch from Knack Object_2: {est_response.status_code}")

if __name__ == "__main__":
    check_year14_establishments()