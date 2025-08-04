#!/usr/bin/env python3
"""
Fixed test script for syncing student comments from Object_10
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
BASE_KNACK_URL = "https://api.knack.com/v1/objects"

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def make_knack_request(object_key, page=1, rows_per_page=1000):
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

def find_records_with_comments(max_records=100):
    """Find Object_10 records that have comments"""
    print("Searching for Object_10 records with comments...")
    
    comment_fields = [
        'field_2302', 'field_2302_raw',  # RRC Cycle 1
        'field_2303', 'field_2303_raw',  # RRC Cycle 2  
        'field_2304', 'field_2304_raw',  # RRC Cycle 3
        'field_2499', 'field_2499_raw',  # Goal Cycle 1
        'field_2493', 'field_2493_raw',  # Goal Cycle 2
        'field_2494', 'field_2494_raw'   # Goal Cycle 3
    ]
    
    records_with_comments = []
    page = 1
    
    while len(records_with_comments) < 10:
        data = make_knack_request('object_10', page=page, rows_per_page=100)
        records = data.get('records', [])
        
        if not records:
            break
            
        print(f"  Checking page {page} ({len(records)} records)...")
        
        for record in records:
            has_comment = False
            comments_found = []
            
            for field in comment_fields:
                value = record.get(field)
                if value and isinstance(value, str) and value.strip():
                    has_comment = True
                    field_type = 'RRC' if '230' in field else 'Goal'
                    cycle = 1 if field in ['field_2302', 'field_2302_raw', 'field_2499', 'field_2499_raw'] else (
                            2 if field in ['field_2303', 'field_2303_raw', 'field_2493', 'field_2493_raw'] else 3)
                    comments_found.append(f"Cycle {cycle} {field_type}")
            
            if has_comment:
                records_with_comments.append({
                    'record': record,
                    'comments_found': comments_found
                })
                
                if len(records_with_comments) >= 10:
                    break
        
        page += 1
        if page > 5:  # Don't search forever
            break
    
    print(f"  Found {len(records_with_comments)} records with comments")
    return records_with_comments

def test_comment_sync():
    """Test syncing comments from Object_10 to Supabase"""
    print("=" * 80)
    print("STUDENT COMMENT SYNC TEST")
    print("=" * 80)
    
    # Find records with comments
    records_with_comments = find_records_with_comments()
    
    if not records_with_comments:
        print("\nNo records with comments found!")
        return
    
    # Define comment field mappings
    comment_mappings = [
        # Cycle 1
        {'cycle': 1, 'type': 'rrc', 'field': 'field_2302', 'field_raw': 'field_2302_raw'},
        {'cycle': 1, 'type': 'goal', 'field': 'field_2499', 'field_raw': 'field_2499_raw'},
        # Cycle 2
        {'cycle': 2, 'type': 'rrc', 'field': 'field_2303', 'field_raw': 'field_2303_raw'},
        {'cycle': 2, 'type': 'goal', 'field': 'field_2493', 'field_raw': 'field_2493_raw'},
        # Cycle 3
        {'cycle': 3, 'type': 'rrc', 'field': 'field_2304', 'field_raw': 'field_2304_raw'},
        {'cycle': 3, 'type': 'goal', 'field': 'field_2494', 'field_raw': 'field_2494_raw'},
    ]
    
    # Process records
    comments_to_sync = []
    students_checked = 0
    students_found = 0
    
    print(f"\nProcessing {len(records_with_comments)} records with comments...")
    
    for item in records_with_comments[:5]:  # Process first 5 for testing
        record = item['record']
        object_10_id = record['id']
        
        print(f"\n  Object_10 ID: {object_10_id}")
        print(f"  Comments found in: {', '.join(item['comments_found'])}")
        
        # Look up student in Supabase by Object_10 ID
        student_result = supabase.table('students').select('id, name, email').eq('knack_id', object_10_id).execute()
        students_checked += 1
        
        if not student_result.data:
            print(f"  ✗ Student not found in Supabase")
            continue
            
        student = student_result.data[0]
        student_id = student['id']
        students_found += 1
        print(f"  ✓ Found student: {student['name']} ({student['email']})")
        
        # Extract comments
        record_comments = 0
        for mapping in comment_mappings:
            # Try raw field first, then regular field
            comment_text = record.get(mapping['field_raw']) or record.get(mapping['field'])
            
            if comment_text and isinstance(comment_text, str) and comment_text.strip():
                comment_data = {
                    'student_id': student_id,
                    'cycle': mapping['cycle'],
                    'comment_type': mapping['type'],
                    'comment_text': comment_text.strip(),
                    'knack_field_id': mapping['field']
                }
                comments_to_sync.append(comment_data)
                record_comments += 1
                
                # Show preview
                preview = comment_text[:60] + '...' if len(comment_text) > 60 else comment_text
                print(f"    - Cycle {mapping['cycle']} {mapping['type'].upper()}: {preview}")
        
        print(f"  Total comments for this student: {record_comments}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Students checked: {students_checked}")
    print(f"  Students found in Supabase: {students_found}")
    print(f"  Total comments to sync: {len(comments_to_sync)}")
    
    if comments_to_sync:
        response = input("\nDo you want to sync these comments? (yes/no): ")
        
        if response.lower() == 'yes':
            print("\nSyncing comments to Supabase...")
            try:
                # Sync comments
                result = supabase.table('student_comments').upsert(
                    comments_to_sync,
                    on_conflict='student_id,cycle,comment_type'
                ).execute()
                print(f"✓ Successfully synced {len(comments_to_sync)} comments!")
                
                # Test word cloud function
                print("\nTesting word cloud function...")
                word_data = supabase.rpc('get_word_cloud_data', {
                    'p_comment_type': 'rrc'
                }).execute()
                
                if word_data.data:
                    print(f"✓ RRC Word cloud: {len(word_data.data)} unique words")
                    print("  Top 5 words:")
                    for word in word_data.data[:5]:
                        print(f"    - '{word['word']}': {word['frequency']} times")
                
                # Test goal word cloud
                goal_data = supabase.rpc('get_word_cloud_data', {
                    'p_comment_type': 'goal'
                }).execute()
                
                if goal_data.data:
                    print(f"\n✓ Goal Word cloud: {len(goal_data.data)} unique words")
                    print("  Top 5 words:")
                    for word in goal_data.data[:5]:
                        print(f"    - '{word['word']}': {word['frequency']} times")
                        
            except Exception as e:
                print(f"✗ Error syncing: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    test_comment_sync()