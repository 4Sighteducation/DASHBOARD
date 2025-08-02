#!/usr/bin/env python3
"""
Debug Object_29 pagination to see why only 1 page is processing
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

def debug_pagination():
    """Check pagination for Object_29"""
    print("=" * 60)
    print("DEBUGGING OBJECT_29 PAGINATION")
    print("=" * 60)
    
    # Test first 3 pages
    for page in range(1, 4):
        print(f"\n--- Page {page} ---")
        url = f"https://api.knack.com/v1/objects/object_29/records?page={page}&rows_per_page=100"
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"Status: {response.status_code}")
            print(f"Total records: {data.get('total_records', 0)}")
            print(f"Total pages: {data.get('total_pages', 0)}")
            print(f"Current page: {data.get('current_page', 0)}")
            print(f"Records on this page: {len(data.get('records', []))}")
            
            # Check if records have field_792
            if data.get('records'):
                has_field_792 = sum(1 for r in data['records'] if r.get('field_792_raw'))
                print(f"Records with field_792: {has_field_792}")
                
                # Check first record structure
                first_record = data['records'][0]
                print(f"\nFirst record ID: {first_record.get('id')}")
                print(f"Has field_792: {'Yes' if first_record.get('field_792_raw') else 'No'}")
                
                # Count responses per record
                response_count = 0
                for field_num in range(1953, 3000):  # Check a wide range
                    if f'field_{field_num}_raw' in first_record and first_record[f'field_{field_num}_raw']:
                        response_count += 1
                print(f"Responses in first record: {response_count}")
        
        except Exception as e:
            print(f"Error on page {page}: {e}")
    
    print("\n" + "=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print("\nIf pages 2+ have no records, the API might be:")
    print("1. Filtering results differently per page")
    print("2. Having a bug with pagination")
    print("3. Requiring different parameters")

if __name__ == "__main__":
    debug_pagination()