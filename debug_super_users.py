#!/usr/bin/env python3
"""
Debug Super Users sync issue
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

def check_super_users():
    """Check object_21 for super users"""
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = "https://api.knack.com/v1/objects/object_21/records"
    params = {'page': 1, 'rows_per_page': 10}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total super users: {data.get('total_records', 0)}")
        print(f"Records returned: {len(data.get('records', []))}")
        
        if data.get('records'):
            print("\nFirst super user record:")
            record = data['records'][0]
            for field, value in record.items():
                print(f"  {field}: {value}")
    else:
        print(f"Error fetching super users: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    check_super_users()