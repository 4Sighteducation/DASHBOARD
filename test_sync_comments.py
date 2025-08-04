#!/usr/bin/env python3
"""
Test script to verify student comment syncing from Object_10 to Supabase
"""

import os
import sys
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

def make_knack_request(object_key, page=1, rows_per_page=10):
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

def test_comment_sync():
    """Test syncing comments from Object_10 to Supabase"""
    print("=" * 80)
    print("TESTING STUDENT COMMENT SYNC")
    print("=" * 80)
    
    # First, get student mapping from Supabase
    print("\n1. Loading existing students from Supabase...")
    student_map = {}
    offset = 0
    limit = 1000
    total_students = 0
    
    # Load all students (paginated)
    while True:
        students = supabase.table('students').select('id, knack_id, email').limit(limit).offset(offset).execute()
        if not students.data:
            break
        
        for student in students.data:
            student_map[student['knack_id']] = {
                'id': student['id'],
                'email': student['email']
            }
        
        total_students += len(students.data)
        if len(students.data) < limit:
            break
        offset += limit
    
    print(f"   Found {total_students} students in Supabase")
    
    # Show a few example knack_ids from Supabase
    if student_map:
        print("   Sample Knack IDs in Supabase:")
        for i, (knack_id, _) in enumerate(list(student_map.items())[:5]):
            print(f"     - {knack_id}")
    
    # Fetch records from Object_10
    print("\n2. Fetching records from Object_10...")
    data = make_knack_request('object_10', page=1, rows_per_page=10)
    records = data.get('records', [])
    print(f"   Fetched {len(records)} records from Knack")
    print("   Object_10 record IDs:")
    for i, record in enumerate(records[:5]):
        print(f"     - {record['id']}")
    
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
    
    # Process records and collect comments
    comments_to_sync = []
    records_with_comments = 0
    total_comments = 0
    
    print("\n3. Processing records for comments...")
    for i, record in enumerate(records):
        # Check if this student exists in Supabase
        student_data = student_map.get(record['id'])
        if not student_data:
            print(f"   Record {i+1}: Student not found in Supabase (Knack ID: {record['id']})")
            continue
        
        student_id = student_data['id']
        student_email = student_data.get('email', 'Unknown')
        
        record_comments = []
        
        # Check each comment field
        for mapping in comment_mappings:
            # Try to get comment text from raw field first, then regular field
            comment_text = record.get(mapping['field_raw']) or record.get(mapping['field'])
            
            # Only process if there's actual comment text
            if comment_text and isinstance(comment_text, str) and comment_text.strip():
                comment_data = {
                    'student_id': student_id,
                    'cycle': mapping['cycle'],
                    'comment_type': mapping['type'],
                    'comment_text': comment_text.strip(),
                    'knack_field_id': mapping['field']
                }
                record_comments.append(comment_data)
                comments_to_sync.append(comment_data)
        
        if record_comments:
            records_with_comments += 1
            total_comments += len(record_comments)
            print(f"\n   Record {i+1} ({student_email}):")
            for comment in record_comments:
                preview = comment['comment_text'][:50] + '...' if len(comment['comment_text']) > 50 else comment['comment_text']
                print(f"     - Cycle {comment['cycle']} {comment['comment_type'].upper()}: {preview}")
    
    # Summary
    print(f"\n4. Summary:")
    print(f"   - Records with comments: {records_with_comments}/{len(records)}")
    print(f"   - Total comments found: {total_comments}")
    
    # Ask user if they want to sync
    if comments_to_sync:
        print(f"\n5. Ready to sync {len(comments_to_sync)} comments to Supabase")
        response = input("   Do you want to sync these comments? (yes/no): ")
        
        if response.lower() == 'yes':
            print("\n6. Syncing comments to Supabase...")
            successful = 0
            failed = 0
            
            # Sync in batches
            batch_size = 10
            for i in range(0, len(comments_to_sync), batch_size):
                batch = comments_to_sync[i:i+batch_size]
                try:
                    result = supabase.table('student_comments').upsert(
                        batch,
                        on_conflict='student_id,cycle,comment_type'
                    ).execute()
                    successful += len(batch)
                    print(f"   Batch {i//batch_size + 1}: Synced {len(batch)} comments")
                except Exception as e:
                    failed += len(batch)
                    print(f"   Batch {i//batch_size + 1}: Failed - {e}")
            
            print(f"\n   Sync complete! Successfully synced: {successful}, Failed: {failed}")
            
            # Test the word cloud function
            print("\n7. Testing word cloud function...")
            try:
                # Get word cloud data for all comments
                word_data = supabase.rpc('get_word_cloud_data', {}).execute()
                print(f"   Word cloud data retrieved: {len(word_data.data)} unique words")
                if word_data.data:
                    print("   Top 10 words:")
                    for word in word_data.data[:10]:
                        print(f"     - '{word['word']}': {word['frequency']} occurrences")
            except Exception as e:
                print(f"   Error testing word cloud function: {e}")
        else:
            print("\n   Sync cancelled.")
    else:
        print("\n   No comments found to sync.")

if __name__ == "__main__":
    try:
        test_comment_sync()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()