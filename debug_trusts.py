#!/usr/bin/env python3
"""
Debug Trust sync issue
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

def check_trusts():
    """Check establishments for trust field"""
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # First check academy_trusts object
    print("Checking object_134 (academy_trusts)...")
    url = "https://api.knack.com/v1/objects/object_134/records"
    response = requests.get(url, headers=headers, params={'page': 1, 'rows_per_page': 10})
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total academy trusts: {data.get('total_records', 0)}")
        if data.get('records'):
            print("\nFirst trust record:")
            record = data['records'][0]
            for field, value in record.items():
                print(f"  {field}: {value}")
    
    # Now check establishments with trust field
    print("\n\nChecking establishments with trusts...")
    
    # Filter for establishments with trust data
    filters = [{
        'field': 'field_3480',
        'operator': 'is not blank'
    }]
    
    url = "https://api.knack.com/v1/objects/object_2/records"
    params = {
        'page': 1,
        'rows_per_page': 10,
        'filters': str(filters).replace("'", '"')
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total establishments with trusts: {data.get('total_records', 0)}")
        
        if data.get('records'):
            print("\nSample establishments with trusts:")
            for record in data['records'][:3]:
                print(f"\nEstablishment: {record.get('field_44', 'N/A')}")
                print(f"  Trust (field_3480): {record.get('field_3480', 'N/A')}")
                print(f"  Trust raw: {record.get('field_3480_raw', 'N/A')}")

if __name__ == "__main__":
    check_trusts()