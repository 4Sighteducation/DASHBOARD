#!/usr/bin/env python3
"""
Debug specific VESPA records to see what's in the overall fields
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

def check_vespa_record(record_id):
    """Check a specific VESPA record to see all field values"""
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"https://api.knack.com/v1/objects/object_10/records/{record_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        record = response.json()
        
        print(f"\nRecord {record_id}:")
        print(f"Email: {record.get('field_197', 'N/A')}")
        
        # Check all cycle fields
        for cycle in [1, 2, 3]:
            field_offset = (cycle - 1) * 6
            print(f"\nCycle {cycle}:")
            print(f"  Vision (field_{155 + field_offset}): {record.get(f'field_{155 + field_offset}', 'N/A')} | Raw: {record.get(f'field_{155 + field_offset}_raw', 'N/A')}")
            print(f"  Effort (field_{156 + field_offset}): {record.get(f'field_{156 + field_offset}', 'N/A')} | Raw: {record.get(f'field_{156 + field_offset}_raw', 'N/A')}")
            print(f"  Systems (field_{157 + field_offset}): {record.get(f'field_{157 + field_offset}', 'N/A')} | Raw: {record.get(f'field_{157 + field_offset}_raw', 'N/A')}")
            print(f"  Practice (field_{158 + field_offset}): {record.get(f'field_{158 + field_offset}', 'N/A')} | Raw: {record.get(f'field_{158 + field_offset}_raw', 'N/A')}")
            print(f"  Attitude (field_{159 + field_offset}): {record.get(f'field_{159 + field_offset}', 'N/A')} | Raw: {record.get(f'field_{159 + field_offset}_raw', 'N/A')}")
            print(f"  Overall (field_{160 + field_offset}): {record.get(f'field_{160 + field_offset}', 'N/A')} | Raw: {record.get(f'field_{160 + field_offset}_raw', 'N/A')}")
    else:
        print(f"Failed to fetch record {record_id}: {response.status_code}")

if __name__ == "__main__":
    # Check the specific failing records
    failing_records = [
        '66eda18396637802fcc7b8c4',
        '66eda18496637802fcc7b8e7'
    ]
    
    for record_id in failing_records:
        check_vespa_record(record_id)