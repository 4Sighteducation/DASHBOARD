#!/usr/bin/env python3
"""
Debug script to check Object_29 data and connections
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

def check_object29():
    """Check Object_29 data structure and connections"""
    print("=" * 60)
    print("CHECKING OBJECT_29 (QUESTION RESPONSES)")
    print("=" * 60)
    
    # Get first page of Object_29
    url = f"https://api.knack.com/v1/objects/object_29/records?page=1&rows_per_page=100"
    response = requests.get(url, headers=headers)
    data = response.json()
    
    print(f"\nTotal Object_29 records: {data.get('total_records', 0)}")
    
    if data.get('records'):
        print(f"\nAnalyzing first {len(data['records'])} records...")
        
        # Count connections
        has_field_792 = 0
        has_email = 0
        has_cycle_data = 0
        cycles_found = {"cycle1": 0, "cycle2": 0, "cycle3": 0}
        
        for record in data['records']:
            # Check field_792 (Object_10 connection)
            if record.get('field_792_raw'):
                has_field_792 += 1
            
            # Check email
            if record.get('field_2732'):
                has_email += 1
            
            # Check cycle indicators
            cycle1 = record.get('field_1953_raw')
            cycle2 = record.get('field_1955_raw')
            cycle3 = record.get('field_1956_raw')
            
            if cycle1 or cycle2 or cycle3:
                has_cycle_data += 1
                
            # Handle different formats - could be int, bool, or dict
            if cycle1:
                if isinstance(cycle1, dict) and cycle1.get('selected'):
                    cycles_found["cycle1"] += 1
                elif cycle1 == 1 or cycle1 == True:
                    cycles_found["cycle1"] += 1
                    
            if cycle2:
                if isinstance(cycle2, dict) and cycle2.get('selected'):
                    cycles_found["cycle2"] += 1
                elif cycle2 == 1 or cycle2 == True:
                    cycles_found["cycle2"] += 1
                    
            if cycle3:
                if isinstance(cycle3, dict) and cycle3.get('selected'):
                    cycles_found["cycle3"] += 1
                elif cycle3 == 1 or cycle3 == True:
                    cycles_found["cycle3"] += 1
        
        print(f"\nConnection Analysis:")
        print(f"  - Has field_792 (Object_10 link): {has_field_792}/{len(data['records'])}")
        print(f"  - Has email (field_2732): {has_email}/{len(data['records'])}")
        print(f"  - Has cycle data: {has_cycle_data}/{len(data['records'])}")
        print(f"\nCycle Distribution:")
        print(f"  - Cycle 1: {cycles_found['cycle1']}")
        print(f"  - Cycle 2: {cycles_found['cycle2']}")
        print(f"  - Cycle 3: {cycles_found['cycle3']}")
        
        # Show sample record structure
        print(f"\nSample record structure:")
        sample = data['records'][0]
        print(f"  - ID: {sample.get('id')}")
        print(f"  - field_792_raw: {sample.get('field_792_raw')}")
        print(f"  - field_2732 (email): {sample.get('field_2732')}")
        print(f"  - field_1953_raw (cycle1): {sample.get('field_1953_raw')}")
        
        # Check how many questions are answered
        question_fields = [f"field_{i}" for i in range(793, 823)]  # Assuming fields 793-822 are questions
        answered_count = sum(1 for field in question_fields if sample.get(f"{field}_raw"))
        print(f"  - Questions answered: {answered_count}/30")

def check_object10():
    """Check Object_10 to understand total possible connections"""
    print("\n" + "=" * 60)
    print("CHECKING OBJECT_10 (VESPA RESULTS)")
    print("=" * 60)
    
    url = f"https://api.knack.com/v1/objects/object_10/records?page=1&rows_per_page=1"
    response = requests.get(url, headers=headers)
    data = response.json()
    
    print(f"\nTotal Object_10 records: {data.get('total_records', 0)}")
    
    # This is the maximum possible connections from Object_29

if __name__ == "__main__":
    check_object29()
    check_object10()
    
    print("\n" + "=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print("\nIf only 17,054 responses were synced, possible reasons:")
    print("1. Many Object_29 records don't have field_792 connections")
    print("2. The Object_10 records they connect to weren't in the student sync")
    print("3. Cycle data filtering is excluding records")
    print("4. Some records have incomplete data")