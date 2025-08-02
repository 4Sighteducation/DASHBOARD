#!/usr/bin/env python3
"""
Verify which field numbers Object_29 actually uses
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

def verify_fields():
    """Check actual field numbers in Object_29"""
    print("=" * 60)
    print("VERIFYING OBJECT_29 FIELD NUMBERS")
    print("=" * 60)
    
    # Get a sample record
    url = "https://api.knack.com/v1/objects/object_29/records?page=1&rows_per_page=1"
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get('records'):
        record = data['records'][0]
        
        # Check for field patterns
        print("\nChecking for field_195x pattern (psychometric_question_details.json):")
        found_195x = []
        for i in range(1953, 1960):
            if f'field_{i}_raw' in record:
                found_195x.append(f'field_{i}')
        print(f"Found: {found_195x}")
        
        print("\nChecking for field_33xx pattern (psychometric_question_output_object_120.json):")
        found_33xx = []
        for i in range(3309, 3320):
            if f'field_{i}_raw' in record:
                found_33xx.append(f'field_{i}')
        print(f"Found: {found_33xx}")
        
        # List all fields with values
        print("\nAll fields with values (first 10):")
        field_count = 0
        for key, value in record.items():
            if key.startswith('field_') and key.endswith('_raw') and value:
                print(f"  {key}: {value}")
                field_count += 1
                if field_count >= 10:
                    break
        
        # Check Q1 Cycle 1 specifically
        print(f"\nQ1 Cycle 1 (field_1953_raw): {record.get('field_1953_raw', 'NOT FOUND')}")
        print(f"Q1 Cycle 1 (field_3309_raw): {record.get('field_3309_raw', 'NOT FOUND')}")

if __name__ == "__main__":
    verify_fields()