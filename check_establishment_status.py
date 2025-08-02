#!/usr/bin/env python3
"""
Check why Belfast Metropolitan College wasn't synced
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

def check_establishment_details(knack_id):
    """Get full details of an establishment to see why it wasn't synced"""
    print(f"Checking establishment {knack_id} details...")
    print("=" * 80)
    
    url = f'https://api.knack.com/v1/objects/object_2/records/{knack_id}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch establishment: {response.status_code}")
        return
    
    est = response.json()
    
    # Print all fields to see what we're dealing with
    print("ALL FIELDS:")
    for field, value in est.items():
        if field.startswith('field_'):
            print(f"  {field}: {value}")
    
    print("\nKEY FIELDS:")
    print(f"  ID: {est.get('id')}")
    print(f"  Name (field_44): {est.get('field_44')}")
    print(f"  Name (field_11): {est.get('field_11')}")
    print(f"  Status (field_2209): {est.get('field_2209')} <-- THIS IS THE KEY!")
    print(f"  Country (field_2300): {est.get('field_2300')}")
    print(f"  Created (field_2): {est.get('field_2')}")
    
    # Check if it would be filtered out
    status = est.get('field_2209', '')
    if status == 'Cancelled':
        print("\n❌ This establishment has status 'Cancelled' - that's why it wasn't synced!")
        print("   The sync_establishments() function filters out Cancelled establishments.")
    else:
        print(f"\n🤔 Status is '{status}' - should have been synced...")

def check_all_establishment_statuses():
    """Check what statuses exist in establishments"""
    print("\n" + "=" * 80)
    print("Checking all establishment statuses in Knack...")
    
    url = 'https://api.knack.com/v1/objects/object_2/records'
    params = {
        'page': 1,
        'rows_per_page': 1000,
        'fields': 'field_44,field_2209'  # name and status
    }
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    # Count statuses
    status_counts = {}
    for record in data.get('records', []):
        status = record.get('field_2209', 'No Status')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\nEstablishment Status Distribution:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count} establishments")

if __name__ == "__main__":
    # Check Belfast Metropolitan College specifically
    check_establishment_details('6171c6311b379d001ecb8966')
    
    # Check overall status distribution
    check_all_establishment_statuses()