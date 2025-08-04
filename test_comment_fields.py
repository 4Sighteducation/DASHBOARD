#!/usr/bin/env python3
"""
Test script to verify Object_10 field mappings before adding comment sync
"""

import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
BASE_KNACK_URL = "https://api.knack.com/v1/objects"

def make_knack_request(object_key, page=1, rows_per_page=5):
    """Make a request to Knack API"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"{BASE_KNACK_URL}/{object_key}/records"
    params = {
        'page': page,
        'rows_per_page': rows_per_page
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def test_object_10_fields():
    """Test and display field mappings from Object_10 (vespa_results)"""
    print("=" * 80)
    print("OBJECT_10 (VESPA RESULTS) FIELD VERIFICATION")
    print("=" * 80)
    
    # Fetch a few records from Object_10
    data = make_knack_request('object_10', page=1, rows_per_page=3)
    records = data.get('records', [])
    
    if not records:
        print("No records found in Object_10")
        return
    
    print(f"\nAnalyzing {len(records)} sample records...\n")
    
    # Field mappings we're checking
    field_mappings = {
        'Student Info': {
            'field_197': 'Email',
            'field_187': 'Name',
            'field_133': 'Establishment',
            'field_223': 'Group',
            'field_144': 'Year Group',
            'field_2299': 'Course',
            'field_782': 'Faculty',
            'field_855': 'Completion Date'
        },
        'Comments - Cycle 1': {
            'field_2302': 'RRC (Reading, Recall, Comprehension)',
            'field_2499': 'Goal'
        },
        'Comments - Cycle 2': {
            'field_2303': 'RRC',
            'field_2493': 'Goal'
        },
        'Comments - Cycle 3': {
            'field_2304': 'RRC',
            'field_2494': 'Goal'
        },
        'VESPA Scores - Cycle 1': {
            'field_155': 'Vision',
            'field_156': 'Effort',
            'field_157': 'Systems',
            'field_158': 'Practice',
            'field_159': 'Attitude',
            'field_160': 'Overall'
        }
    }
    
    # Check each record
    for i, record in enumerate(records):
        print(f"\n{'='*60}")
        print(f"RECORD {i+1} (ID: {record.get('id')})")
        print(f"{'='*60}")
        
        for category, fields in field_mappings.items():
            print(f"\n{category}:")
            print("-" * 40)
            
            for field_id, field_name in fields.items():
                # Check both regular and raw fields
                value = record.get(field_id, 'NOT FOUND')
                raw_value = record.get(f'{field_id}_raw', 'NOT FOUND')
                
                # Format the output
                print(f"\n  {field_name} ({field_id}):")
                
                if value != 'NOT FOUND':
                    # Truncate long values for display
                    display_value = str(value)[:100] + '...' if len(str(value)) > 100 else str(value)
                    print(f"    Regular: {display_value}")
                
                if raw_value != 'NOT FOUND':
                    # Handle different data types
                    if isinstance(raw_value, dict):
                        print(f"    Raw (dict): {json.dumps(raw_value, indent=6)[:200]}...")
                    elif isinstance(raw_value, list):
                        print(f"    Raw (list): {raw_value[:2]}..." if len(raw_value) > 2 else f"    Raw (list): {raw_value}")
                    else:
                        display_raw = str(raw_value)[:100] + '...' if len(str(raw_value)) > 100 else str(raw_value)
                        print(f"    Raw: {display_raw}")
        
        # Check for comment content
        print("\n" + "="*40)
        print("COMMENT CONTENT CHECK:")
        print("-" * 40)
        
        comment_fields = {
            'Cycle 1': ['field_2302', 'field_2499'],
            'Cycle 2': ['field_2303', 'field_2493'],
            'Cycle 3': ['field_2304', 'field_2494']
        }
        
        has_comments = False
        for cycle, fields in comment_fields.items():
            cycle_comments = []
            for field in fields:
                comment = record.get(f'{field}_raw') or record.get(field)
                if comment and str(comment).strip():
                    cycle_comments.append(f"{field}: {str(comment)[:50]}...")
                    has_comments = True
            
            if cycle_comments:
                print(f"\n{cycle}: Found {len(cycle_comments)} comments")
                for comment in cycle_comments:
                    print(f"  - {comment}")
        
        if not has_comments:
            print("\nNo comments found in this record")

    # Summary
    print("\n" + "="*80)
    print("FIELD MAPPING SUMMARY FOR sync_knack_to_supabase.py:")
    print("="*80)
    print("""
From Object_10 (vespa_results):
- field_197_raw: Student Email
- field_187_raw: Student Name (dict with 'full', 'first', 'last')
- field_133_raw: Establishment Reference (list of establishment connections)
- field_223: Group
- field_144: Year Group
- field_2299: Course
- field_782: Faculty
- field_855: Completion Date (DD/MM/YYYY format)

Comments (to be added):
- field_2302_raw: RRC Comment Cycle 1
- field_2303_raw: RRC Comment Cycle 2
- field_2304_raw: RRC Comment Cycle 3
- field_2499_raw: Goal Comment Cycle 1
- field_2493_raw: Goal Comment Cycle 2
- field_2494_raw: Goal Comment Cycle 3

VESPA Scores (already synced):
- Cycle 1: fields 155-160 (Vision, Effort, Systems, Practice, Attitude, Overall)
- Cycle 2: fields 161-166
- Cycle 3: fields 167-172
""")

if __name__ == "__main__":
    try:
        test_object_10_fields()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure your .env file contains:")
        print("- KNACK_APP_ID")
        print("- KNACK_API_KEY")