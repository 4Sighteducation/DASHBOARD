#!/usr/bin/env python3
"""
Test script to verify student comment syncing with specific Object_10 records
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

def fetch_specific_records(object_key, record_ids):
    """Fetch specific records by ID from Knack"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    records = []
    for record_id in record_ids:
        url = f"{BASE_KNACK_URL}/{object_key}/records/{record_id}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                records.append(response.json())
            else:
                print(f"   Failed to fetch record {record_id}: {response.status_code}")
        except Exception as e:
            print(f"   Error fetching record {record_id}: {e}")
    
    return records

def search_for_comments_in_knack(max_pages=5):
    """Search through Object_10 records to find ones with comments"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    comment_fields = ['field_2302', 'field_2303', 'field_2304', 'field_2499', 'field_2493', 'field_2494']
    records_with_comments = []
    
    print(f"\nSearching for records with comments (checking up to {max_pages} pages)...")
    
    for page in range(1, max_pages + 1):
        url = f"{BASE_KNACK_URL}/object_10/records"
        params = {
            'page': page,
            'rows_per_page': 100
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            break
            
        data = response.json()
        records = data.get('records', [])
        
        print(f"   Page {page}: Checking {len(records)} records...")
        
        for record in records:
            has_comment = False
            for field in comment_fields:
                if record.get(field) or record.get(f'{field}_raw'):
                    has_comment = True
                    break
            
            if has_comment:
                records_with_comments.append(record['id'])
        
        if len(records_with_comments) >= 10:
            break
    
    print(f"   Found {len(records_with_comments)} records with comments")
    return records_with_comments[:10]

def test_comment_sync(specific_ids=None):
    """Test syncing comments from Object_10 to Supabase"""
    print("=" * 80)
    print("TESTING STUDENT COMMENT SYNC")
    print("=" * 80)
    
    # First, check if specific IDs were provided
    if specific_ids:
        print(f"\n1. Using specific Object_10 IDs: {specific_ids}")
        records = fetch_specific_records('object_10', specific_ids)
    else:
        # Search for records with comments
        found_ids = search_for_comments_in_knack()
        if found_ids:
            print(f"\n1. Found records with comments: {found_ids[:5]}...")
            records = fetch_specific_records('object_10', found_ids)
        else:
            print("\n1. No records with comments found")
            return
    
    print(f"\n2. Processing {len(records)} records...")
    
    # Define comment field mappings
    comment_mappings = [
        # Cycle 1
        {'cycle': 1, 'type': 'rrc', 'field': 'field_2302', 'field_raw': 'field_2302_raw', 'desc': 'RRC'},
        {'cycle': 1, 'type': 'goal', 'field': 'field_2499', 'field_raw': 'field_2499_raw', 'desc': 'Goal'},
        # Cycle 2
        {'cycle': 2, 'type': 'rrc', 'field': 'field_2303', 'field_raw': 'field_2303_raw', 'desc': 'RRC'},
        {'cycle': 2, 'type': 'goal', 'field': 'field_2493', 'field_raw': 'field_2493_raw', 'desc': 'Goal'},
        # Cycle 3
        {'cycle': 3, 'type': 'rrc', 'field': 'field_2304', 'field_raw': 'field_2304_raw', 'desc': 'RRC'},
        {'cycle': 3, 'type': 'goal', 'field': 'field_2494', 'field_raw': 'field_2494_raw', 'desc': 'Goal'},
    ]
    
    # Process records
    all_comments = []
    
    for i, record in enumerate(records):
        print(f"\n   Record {i+1} (Knack ID: {record['id']}):")
        
        # Extract email to identify the student
        email_field = record.get('field_197_raw', {})
        if isinstance(email_field, dict):
            email = email_field.get('email', '')
        else:
            email = str(email_field) if email_field else ''
        
        print(f"     Email: {email}")
        
        # Check if student exists in Supabase
        if email:
            student_result = supabase.table('students').select('id, knack_id').eq('email', email).execute()
            if student_result.data:
                student_id = student_result.data[0]['id']
                print(f"     Found in Supabase with ID: {student_id}")
                print(f"     Stored Knack ID: {student_result.data[0]['knack_id']}")
            else:
                print(f"     NOT FOUND in Supabase - would need to sync student first")
                # For testing, we'll create a temporary student entry
                student_data = {
                    'knack_id': record['id'],
                    'email': email,
                    'name': record.get('field_187', '') or record.get('field_187_raw', '')
                }
                result = supabase.table('students').insert(student_data).execute()
                student_id = result.data[0]['id']
                print(f"     Created temporary student with ID: {student_id}")
        else:
            print(f"     No email found - skipping")
            continue
        
        # Extract comments
        record_comments = []
        for mapping in comment_mappings:
            # Try raw field first, then regular field
            comment_text = record.get(mapping['field_raw']) or record.get(mapping['field'])
            
            if comment_text and isinstance(comment_text, str) and comment_text.strip():
                preview = comment_text[:60] + '...' if len(comment_text) > 60 else comment_text
                print(f"     Cycle {mapping['cycle']} {mapping['desc']}: {preview}")
                
                comment_data = {
                    'student_id': student_id,
                    'cycle': mapping['cycle'],
                    'comment_type': mapping['type'],
                    'comment_text': comment_text.strip(),
                    'knack_field_id': mapping['field']
                }
                record_comments.append(comment_data)
        
        if record_comments:
            all_comments.extend(record_comments)
        else:
            print(f"     No comments found")
    
    # Summary and sync
    print(f"\n3. Summary: Found {len(all_comments)} total comments")
    
    if all_comments:
        response = input("\n   Do you want to sync these comments? (yes/no): ")
        
        if response.lower() == 'yes':
            print("\n4. Syncing comments to Supabase...")
            try:
                result = supabase.table('student_comments').upsert(
                    all_comments,
                    on_conflict='student_id,cycle,comment_type'
                ).execute()
                print(f"   Successfully synced {len(all_comments)} comments!")
                
                # Test word cloud function
                print("\n5. Testing word cloud function...")
                word_data = supabase.rpc('get_word_cloud_data', {}).execute()
                print(f"   Retrieved {len(word_data.data)} unique words")
                if word_data.data[:5]:
                    print("   Top 5 words:")
                    for word in word_data.data[:5]:
                        print(f"     - '{word['word']}': {word['frequency']} times")
                        
            except Exception as e:
                print(f"   Error syncing: {e}")

if __name__ == "__main__":
    # Check if specific IDs were provided as command line arguments
    if len(sys.argv) > 1:
        specific_ids = sys.argv[1:]
        print(f"Using specific Object_10 IDs: {specific_ids}")
        test_comment_sync(specific_ids)
    else:
        print("Usage: python test_sync_comments_targeted.py [object_10_id1] [object_10_id2] ...")
        print("Or run without arguments to search for records with comments")
        response = input("\nSearch for records with comments? (yes/no): ")
        if response.lower() == 'yes':
            test_comment_sync()