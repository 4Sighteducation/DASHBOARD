#!/usr/bin/env python3
"""
Test script to verify student lookups by Object_10 ID
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_student_lookup():
    """Test looking up specific students by Object_10 ID"""
    
    # Test with the Object_10 IDs from the failed test
    test_ids = [
        '6878cb46056ae00313857aab',  # This one is shown in your screenshot
        '688d0dc96ac4d603099ae3d7',
        '6880c0aa083a631e17b2808d',
        '687fa8a49767cf0302923860',
        '687f8d6c6b6cd702dd91ec82'
    ]
    
    print("Testing direct student lookups by Object_10 ID (knack_id):")
    print("=" * 60)
    
    for knack_id in test_ids:
        print(f"\nLooking up: {knack_id}")
        try:
            result = supabase.table('students').select('id, knack_id, name, email').eq('knack_id', knack_id).execute()
            if result.data:
                student = result.data[0]
                print(f"  ✓ FOUND: {student['name']} ({student['email']})")
                print(f"    Supabase ID: {student['id']}")
                print(f"    Knack ID: {student['knack_id']}")
            else:
                print(f"  ✗ NOT FOUND")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Also test total count
    print("\n" + "=" * 60)
    print("Checking total student count:")
    try:
        count_result = supabase.table('students').select('id', count='exact').execute()
        print(f"Total students in Supabase: {count_result.count}")
    except Exception as e:
        print(f"Error getting count: {e}")

if __name__ == "__main__":
    test_student_lookup()