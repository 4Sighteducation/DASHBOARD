#!/usr/bin/env python3
"""
Test script for student comments sync functionality
This will test syncing comments from Object_10 to the new student_comments table
"""

import os
import json
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

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

def sync_student_comments_from_record(record, student_id):
    """
    Extract and prepare student comments from an Object_10 record
    Returns a list of comment data to be batch inserted
    """
    comments_batch = []
    
    # Define the comment field mappings
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
    
    for mapping in comment_mappings:
        # Try to get the comment text from raw field first, then regular field
        comment_text = record.get(mapping['field_raw']) or record.get(mapping['field'])
        
        # Only create a record if there's actual comment text
        if comment_text and isinstance(comment_text, str) and comment_text.strip():
            comment_data = {
                'student_id': student_id,
                'cycle': mapping['cycle'],
                'comment_type': mapping['type'],
                'comment_text': comment_text.strip(),
                'knack_field_id': mapping['field']
            }
            comments_batch.append(comment_data)
    
    return comments_batch

def test_comment_sync():
    """Test the comment sync functionality"""
    print("=" * 80)
    print("TESTING STUDENT COMMENTS SYNC")
    print("=" * 80)
    
    # First, check if the student_comments table exists
    try:
        test_query = supabase.table('student_comments').select('id').limit(1).execute()
        print("✓ student_comments table exists")
    except Exception as e:
        print(f"✗ student_comments table not found: {e}")
        print("\nPlease run the SQL script first:")
        print("  psql -h your-supabase-host -U postgres -d postgres < create_student_comments_table.sql")
        return
    
    # Get student mapping
    print("\nLoading student mappings...")
    students = supabase.table('students').select('id, knack_id, email').limit(10).execute()
    student_map = {s['knack_id']: s['id'] for s in students.data}
    print(f"Found {len(student_map)} students in Supabase")
    
    # Fetch some records from Object_10
    print("\nFetching records from Knack Object_10...")
    data = make_knack_request('object_10', page=1, rows_per_page=10)
    records = data.get('records', [])
    print(f"Fetched {len(records)} records")
    
    # Process records and collect comments
    all_comments = []
    records_with_comments = 0
    
    for record in records:
        knack_id = record.get('id')
        student_id = student_map.get(knack_id)
        
        if student_id:
            comments = sync_student_comments_from_record(record, student_id)
            if comments:
                all_comments.extend(comments)
                records_with_comments += 1
                
                # Display first few comments for verification
                if records_with_comments <= 3:
                    print(f"\nRecord {knack_id} has {len(comments)} comments:")
                    for comment in comments:
                        print(f"  - Cycle {comment['cycle']} {comment['comment_type'].upper()}: {comment['comment_text'][:50]}...")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"{'='*60}")
    print(f"Total records processed: {len(records)}")
    print(f"Records with comments: {records_with_comments}")
    print(f"Total comments found: {len(all_comments)}")
    
    # Test inserting comments
    if all_comments:
        print(f"\nTesting insert of {len(all_comments)} comments...")
        try:
            # Insert in small batch for testing
            test_batch = all_comments[:5]
            result = supabase.table('student_comments').upsert(
                test_batch,
                on_conflict='student_id,cycle,comment_type'
            ).execute()
            print(f"✓ Successfully inserted {len(test_batch)} test comments")
            
            # Verify insertion
            verify = supabase.table('student_comments').select('*').limit(5).execute()
            print(f"✓ Verified {len(verify.data)} comments in database")
            
        except Exception as e:
            print(f"✗ Error inserting comments: {e}")
    
    # Test the word cloud function
    print("\n" + "="*60)
    print("TESTING WORD CLOUD FUNCTION:")
    print("="*60)
    
    try:
        # Get word frequencies for all comments
        result = supabase.rpc('get_word_cloud_data', {
            'p_comment_type': 'rrc'
        }).execute()
        
        if result.data:
            print(f"\nTop 10 words in RRC comments:")
            for i, word_data in enumerate(result.data[:10]):
                print(f"  {i+1}. '{word_data['word']}' - {word_data['frequency']} occurrences")
        else:
            print("No word frequency data returned")
            
    except Exception as e:
        print(f"Word cloud function error: {e}")
        print("The function may not be created yet. Run the SQL script first.")

if __name__ == "__main__":
    try:
        test_comment_sync()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure your .env file contains:")
        print("- KNACK_APP_ID")
        print("- KNACK_API_KEY")
        print("- SUPABASE_URL")
        print("- SUPABASE_KEY")