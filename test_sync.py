#!/usr/bin/env python3
"""
Test script to verify Knack to Supabase sync setup
Run this before the full sync to ensure everything is configured correctly
"""

import os
from dotenv import load_dotenv
import requests
from supabase import create_client, Client
import json

# Load environment variables
load_dotenv()

def test_knack_connection():
    """Test Knack API connection"""
    print("Testing Knack connection...")
    
    KNACK_APP_ID = os.getenv('KNACK_APP_ID')
    KNACK_API_KEY = os.getenv('KNACK_API_KEY')
    
    if not KNACK_APP_ID or not KNACK_API_KEY:
        print("❌ Knack credentials not found in environment")
        return False
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Test with establishments
    url = "https://api.knack.com/v1/objects/object_2/records?rows_per_page=1"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Knack connection successful - Found {data.get('total_records', 0)} establishments")
        return True
    except Exception as e:
        print(f"❌ Knack connection failed: {e}")
        return False

def test_supabase_connection():
    """Test Supabase connection"""
    print("\nTesting Supabase connection...")
    
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase credentials not found in environment")
        return False
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test table access
        result = supabase.table('establishments').select('count', count='exact').execute()
        print(f"✅ Supabase connection successful - Establishments table has {result.count} records")
        
        # Check other tables
        tables = ['students', 'vespa_scores', 'question_responses', 'school_statistics']
        for table in tables:
            result = supabase.table(table).select('count', count='exact').execute()
            print(f"   - {table}: {result.count} records")
        
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def test_file_access():
    """Test access to required files"""
    print("\nTesting file access...")
    
    files_to_check = [
        'AIVESPACoach/psychometric_question_details.json'
    ]
    
    all_good = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ Found: {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
            all_good = False
    
    return all_good

def test_sample_sync():
    """Test syncing a single establishment"""
    print("\nTesting sample sync...")
    
    try:
        # Get Knack credentials
        KNACK_APP_ID = os.getenv('KNACK_APP_ID')
        KNACK_API_KEY = os.getenv('KNACK_API_KEY')
        headers = {
            'X-Knack-Application-Id': KNACK_APP_ID,
            'X-Knack-REST-API-Key': KNACK_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Fetch one establishment
        url = "https://api.knack.com/v1/objects/object_2/records?rows_per_page=1"
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('records'):
            est = data['records'][0]
            print(f"   Found establishment: {est.get('field_11', 'Unknown')}")
            
            # Try to sync to Supabase
            SUPABASE_URL = os.getenv('SUPABASE_URL')
            SUPABASE_KEY = os.getenv('SUPABASE_KEY')
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            establishment_data = {
                'knack_id': est['id'],
                'name': est.get('field_11', ''),
                'is_australian': est.get('field_3508_raw', False) == 'true'
            }
            
            result = supabase.table('establishments').upsert(establishment_data).execute()
            print("✅ Sample sync successful!")
            return True
        else:
            print("⚠️  No establishments found to test")
            return True
            
    except Exception as e:
        print(f"❌ Sample sync failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("KNACK TO SUPABASE SYNC TEST")
    print("=" * 50)
    
    tests = [
        test_knack_connection(),
        test_supabase_connection(),
        test_file_access(),
        test_sample_sync()
    ]
    
    if all(tests):
        print("\n✅ All tests passed! Ready to run full sync.")
        print("\nTo run the full sync:")
        print("  python sync_knack_to_supabase.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues before running the full sync.")

if __name__ == "__main__":
    main()