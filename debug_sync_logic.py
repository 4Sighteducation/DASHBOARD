#!/usr/bin/env python3
"""
Debug the actual sync logic to see what's happening
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import sync components
from sync_knack_to_supabase_optimized import (
    make_knack_request, OBJECT_KEYS, supabase
)

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_sync_page():
    """Debug a single page of Object_29 sync"""
    print("=" * 80)
    print("DEBUGGING SYNC LOGIC - PAGE 1")
    print("=" * 80)
    
    # Load question mapping
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        question_mapping = json.load(f)
    
    # Get student mapping
    students = supabase.table('students').select('id', 'knack_id').execute()
    student_map = {s['knack_id']: s['id'] for s in students.data}
    print(f"\nLoaded {len(student_map)} student mappings")
    
    # Fetch page 1 of Object_29
    print("\nFetching Object_29 page 1...")
    data = make_knack_request(OBJECT_KEYS['psychometric'], page=1)
    records = data.get('records', [])
    
    print(f"Records on page: {len(records)}")
    print(f"Total pages: {data.get('total_pages', 0)}")
    print(f"Total records: {data.get('total_records', 0)}")
    
    # Track what happens to each record
    stats = {
        'total_records': 0,
        'no_field_792': 0,
        'no_object10_id': 0,
        'object10_not_in_students': 0,
        'records_with_student': 0,
        'total_responses_created': 0,
        'responses_per_record': []
    }
    
    # Process records like sync does
    for i, record in enumerate(records[:10]):  # First 10 records
        stats['total_records'] += 1
        print(f"\n--- Record {i+1} ---")
        
        # Get Object_10 connection
        object_10_field = record.get('field_792_raw', [])
        if not object_10_field:
            print("  ❌ No field_792_raw")
            stats['no_field_792'] += 1
            continue
            
        # Extract Object_10 ID
        object_10_knack_id = None
        if isinstance(object_10_field, list) and len(object_10_field) > 0:
            object_10_item = object_10_field[0]
            if isinstance(object_10_item, dict):
                object_10_knack_id = object_10_item.get('id') or object_10_item.get('value')
            else:
                object_10_knack_id = object_10_item
                
        if not object_10_knack_id:
            print("  ❌ No Object_10 ID extracted")
            stats['no_object10_id'] += 1
            continue
            
        print(f"  Object_10 ID: {object_10_knack_id}")
        
        # Map to student
        student_id = student_map.get(object_10_knack_id)
        if not student_id:
            print(f"  ❌ Object_10 ID not in student_map")
            stats['object10_not_in_students'] += 1
            continue
            
        print(f"  ✅ Student ID: {student_id}")
        stats['records_with_student'] += 1
        
        # Count responses that would be created
        record_responses = 0
        for cycle in [1, 2, 3]:
            for q_detail in question_mapping[:29]:  # First 29 VESPA questions
                field_id = q_detail.get(f'fieldIdCycle{cycle}')
                if field_id:
                    response_value = record.get(f'{field_id}_raw')
                    
                    if response_value is not None and response_value != '':
                        try:
                            int_value = int(response_value)
                            if int_value > 0:
                                record_responses += 1
                        except:
                            pass
        
        print(f"  Valid responses: {record_responses}")
        stats['responses_per_record'].append(record_responses)
        stats['total_responses_created'] += record_responses
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Records analyzed: {stats['total_records']}")
    print(f"  No field_792: {stats['no_field_792']}")
    print(f"  No Object_10 ID: {stats['no_object10_id']}")
    print(f"  Object_10 not in students: {stats['object10_not_in_students']}")
    print(f"  Records with student mapping: {stats['records_with_student']}")
    print(f"\nResponses:")
    print(f"  Total that should sync: {stats['total_responses_created']}")
    if stats['records_with_student'] > 0:
        avg = stats['total_responses_created'] / stats['records_with_student']
        print(f"  Average per record: {avg:.1f}")

if __name__ == "__main__":
    debug_sync_page()