#!/usr/bin/env python3
"""
Debug script to identify duplicate question responses in the sync process
"""

import os
import json
import requests
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

def check_object29_duplicates():
    """Check for any duplicate records or pagination issues in Object_29"""
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    all_records = []
    seen_ids = set()
    duplicate_ids = []
    page = 1
    
    print("Fetching all Object_29 records to check for duplicates...")
    
    while True:
        url = f"https://api.knack.com/v1/objects/object_29/records?page={page}&rows_per_page=1000"
        response = requests.get(url, headers=headers)
        data = response.json()
        
        records = data.get('records', [])
        if not records:
            break
            
        for record in records:
            record_id = record['id']
            if record_id in seen_ids:
                duplicate_ids.append(record_id)
                print(f"DUPLICATE FOUND: Record {record_id} appears multiple times")
            seen_ids.add(record_id)
            all_records.append(record)
        
        print(f"Page {page}: {len(records)} records")
        page += 1
    
    print(f"\nTotal records: {len(all_records)}")
    print(f"Unique records: {len(seen_ids)}")
    print(f"Duplicates: {len(duplicate_ids)}")
    
    # Now check for duplicate email connections
    email_connections = defaultdict(list)
    
    for record in all_records:
        field_792 = record.get('field_792_raw', [])
        if field_792 and isinstance(field_792, list):
            for conn in field_792:
                conn_id = conn.get('id') if isinstance(conn, dict) else conn
                email_connections[conn_id].append(record['id'])
    
    # Find any Object_10 IDs linked to multiple Object_29 records
    multi_linked = {k: v for k, v in email_connections.items() if len(v) > 1}
    
    if multi_linked:
        print(f"\nFound {len(multi_linked)} Object_10 records linked to multiple Object_29 records:")
        for obj10_id, obj29_ids in list(multi_linked.items())[:10]:
            print(f"  Object_10 {obj10_id} -> Object_29: {obj29_ids}")
    
    return all_records, duplicate_ids, multi_linked

def analyze_failed_records():
    """Analyze the specific records that failed"""
    
    failed_record_ids = [
        '66e2da7bf6ad5102db2b41e2',
        '66e2da121de24c02eaa5965b',
        '668d2a7f14515c02cefb5654',
        '66a78884d4815102cc13c45a'
    ]
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    print("\nAnalyzing failed records:")
    
    for record_id in failed_record_ids:
        url = f"https://api.knack.com/v1/objects/object_29/records/{record_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            record = response.json()
            
            # Get the Object_10 connection
            field_792 = record.get('field_792_raw', [])
            obj10_id = None
            if field_792 and isinstance(field_792, list) and len(field_792) > 0:
                obj10_id = field_792[0].get('id') if isinstance(field_792[0], dict) else field_792[0]
            
            print(f"\nRecord {record_id}:")
            print(f"  Object_10 connection: {obj10_id}")
            print(f"  Email display: {record.get('field_792', 'N/A')}")
            
            # Check if this Object_10 ID appears in other records
            if obj10_id:
                search_url = f"https://api.knack.com/v1/objects/object_29/records?filters=[{{\"field\":\"field_792\",\"operator\":\"is\",\"value\":\"{obj10_id}\"}}]"
                search_response = requests.get(search_url, headers=headers)
                if search_response.status_code == 200:
                    matching_records = search_response.json().get('records', [])
                    if len(matching_records) > 1:
                        print(f"  WARNING: Object_10 {obj10_id} is linked to {len(matching_records)} Object_29 records!")
                        for match in matching_records:
                            print(f"    - {match['id']}")

if __name__ == "__main__":
    # First check for duplicates
    records, duplicates, multi_linked = check_object29_duplicates()
    
    # Then analyze the specific failed records
    analyze_failed_records()