#!/usr/bin/env python3
"""
Analyze why only 17K responses were synced
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

# Supabase
from supabase import create_client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_sync_mismatch():
    """Figure out why only 17K synced"""
    print("=" * 60)
    print("ANALYZING SYNC MISMATCH")
    print("=" * 60)
    
    # Get all Object_10 IDs from Knack
    print("\n1. Fetching all Object_10 IDs from Knack...")
    knack_object10_ids = set()
    page = 1
    while True:
        url = f"https://api.knack.com/v1/objects/object_10/records?page={page}&rows_per_page=1000"
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if not data.get('records'):
            break
            
        for record in data['records']:
            knack_object10_ids.add(record['id'])
        
        if page >= data.get('total_pages', 1):
            break
        page += 1
    
    print(f"   Found {len(knack_object10_ids)} Object_10 records in Knack")
    
    # Get all student knack_ids from Supabase
    print("\n2. Fetching student knack_ids from Supabase...")
    students = supabase.table('students').select('knack_id').execute()
    supabase_student_knack_ids = set(s['knack_id'] for s in students.data)
    print(f"   Found {len(supabase_student_knack_ids)} students in Supabase")
    
    # Check overlap
    overlap = knack_object10_ids.intersection(supabase_student_knack_ids)
    print(f"\n3. Overlap: {len(overlap)} Object_10 IDs match student knack_ids")
    print(f"   Missing: {len(knack_object10_ids - supabase_student_knack_ids)} Object_10 records not in students table")
    
    # Check question_responses
    print("\n4. Checking question_responses table...")
    response_count = supabase.table('question_responses').select('id', count='exact').execute()
    print(f"   Total question responses: {response_count.count}")
    
    # Get sample of Object_29 records WITHOUT cycles
    print("\n5. Checking Object_29 records without cycle indicators...")
    url = f"https://api.knack.com/v1/objects/object_29/records?page=1&rows_per_page=500"
    response = requests.get(url, headers=headers)
    data = response.json()
    
    no_cycles = 0
    has_any_cycle = 0
    has_all_cycles = 0
    has_field_792 = 0
    
    for record in data.get('records', []):
        c1 = record.get('field_1953_raw')
        c2 = record.get('field_1955_raw')
        c3 = record.get('field_1956_raw')
        
        if record.get('field_792_raw'):
            has_field_792 += 1
        
        if not c1 and not c2 and not c3:
            no_cycles += 1
        elif c1 and c2 and c3:
            has_all_cycles += 1
        else:
            has_any_cycle += 1
    
    print(f"\n   Out of {len(data.get('records', []))} records:")
    print(f"   - No cycle indicators: {no_cycles}")
    print(f"   - Some cycles: {has_any_cycle}")
    print(f"   - All 3 cycles: {has_all_cycles}")
    print(f"   - Has field_792: {has_field_792}")
    
    # Calculate expected responses
    print("\n6. EXPECTED CALCULATIONS:")
    print(f"   - If all Object_29 records synced: {40888} records × 30 questions = ~1.2M responses")
    print(f"   - If only records with cycles: ~20% × 40,888 = ~8,000 records × 30 = ~240K responses")
    print(f"   - Actual synced: 17,054 responses")
    print(f"\n   This suggests: {17054 / 30:.0f} records were processed (~{17054/30/40888*100:.1f}% of Object_29)")

if __name__ == "__main__":
    analyze_sync_mismatch()