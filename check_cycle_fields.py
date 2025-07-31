#!/usr/bin/env python3
"""
Check how cycle fields actually work in Object_29
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

def check_cycles():
    """Understand how cycles are stored"""
    print("=" * 60)
    print("CHECKING CYCLE FIELD STRUCTURE")
    print("=" * 60)
    
    # Get records with field_792 connection
    url = f"https://api.knack.com/v1/objects/object_29/records?page=1&rows_per_page=10&filters=" + \
          '[{"field":"field_792","operator":"is not blank"}]'
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    print(f"\nAnalyzing {len(data.get('records', []))} records with field_792...")
    
    for i, record in enumerate(data.get('records', [])[:3]):  # Just first 3
        print(f"\n--- Record {i+1} ---")
        print(f"ID: {record.get('id')}")
        print(f"Email: {record.get('field_2732', 'No email')}")
        print(f"field_792 (Object_10): {record.get('field_792')}")
        
        # Check cycle fields
        print(f"\nCycle indicators:")
        print(f"  field_1953_raw (C1?): {record.get('field_1953_raw')}")
        print(f"  field_1955_raw (C2?): {record.get('field_1955_raw')}")
        print(f"  field_1956_raw (C3?): {record.get('field_1956_raw')}")
        
        # Count how many question fields have values
        question_count = 0
        for field_num in range(793, 825):  # Checking a range
            field_key = f"field_{field_num}_raw"
            if field_key in record and record[field_key]:
                question_count += 1
        
        print(f"\nQuestions with responses: {question_count}")
        
        # Show a few question values
        print("\nSample question responses:")
        for field_num in [793, 794, 795]:
            field_key = f"field_{field_num}_raw"
            if field_key in record:
                print(f"  {field_key}: {record[field_key]}")
    
    print("\n" + "=" * 60)
    print("HYPOTHESIS:")
    print("=" * 60)
    print("\nMaybe the cycle fields DON'T determine which cycle this is for?")
    print("Maybe ALL Object_29 records should be processed, and the cycle")
    print("is determined by something else (like a date or sequence)?")
    print("\nOr maybe Object_29 records represent a SINGLE cycle each,")
    print("not all 3 cycles in one record?")

if __name__ == "__main__":
    check_cycles()