#!/usr/bin/env python3
"""
Verify the completeness and accuracy of the sync
"""

import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

# API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_knack_records():
    """Count total records in Knack Object_29"""
    print("1. Checking Knack Object_29 (Question Responses)...")
    print("=" * 80)
    
    url = 'https://api.knack.com/v1/objects/object_29/records'
    params = {
        'page': 1,
        'rows_per_page': 1
    }
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    total_knack_records = data.get('total_records', 0)
    print(f"Total records in Knack Object_29: {total_knack_records:,}")
    
    # Get a sample to verify structure
    params['rows_per_page'] = 5
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    print("\nSample records structure:")
    for i, record in enumerate(data.get('records', [])[:2], 1):
        print(f"\nRecord {i}:")
        print(f"  ID: {record.get('id')}")
        print(f"  VESPA Link (field_792): {record.get('field_792_raw')}")
        print(f"  Has valid VESPA link: {'Yes' if record.get('field_792_raw') else 'No'}")
    
    return total_knack_records

def check_supabase_records():
    """Analyze records in Supabase"""
    print("\n2. Checking Supabase question_responses...")
    print("=" * 80)
    
    # Total records
    count_result = supabase.table('question_responses').select('*', count='exact', head=True).execute()
    total_records = count_result.count
    print(f"Total records in Supabase: {total_records:,}")
    
    # Unique combinations
    result = supabase.rpc('execute_sql', {
        'query': '''
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT (student_id, cycle, question_id)) as unique_combinations,
                COUNT(*) - COUNT(DISTINCT (student_id, cycle, question_id)) as duplicates
            FROM question_responses
        '''
    }).execute()
    
    if result.data:
        stats = result.data[0]
        print(f"Unique (student, cycle, question) combinations: {stats['unique_combinations']:,}")
        print(f"Duplicate records: {stats['duplicates']:,}")
    
    # Records per cycle
    cycle_result = supabase.rpc('execute_sql', {
        'query': '''
            SELECT cycle, COUNT(*) as count
            FROM question_responses
            GROUP BY cycle
            ORDER BY cycle
        '''
    }).execute()
    
    print("\nRecords per cycle:")
    for row in cycle_result.data:
        print(f"  Cycle {row['cycle']}: {row['count']:,}")
    
    # Check for records with NULL student_id (shouldn't exist)
    null_result = supabase.table('question_responses').select('id', count='exact').is_('student_id', 'null').execute()
    print(f"\nRecords with NULL student_id: {null_result.count}")
    
    return total_records

def check_vespa_to_student_mapping():
    """Verify VESPA to student mapping"""
    print("\n3. Checking VESPA to Student mapping...")
    print("=" * 80)
    
    # Count VESPA records
    vespa_count = supabase.table('vespa_scores').select('*', count='exact', head=True).execute()
    print(f"Total VESPA scores: {vespa_count.count:,}")
    
    # Count students
    student_count = supabase.table('students').select('*', count='exact', head=True).execute()
    print(f"Total students: {student_count.count:,}")
    
    # Check unmapped VESPA records in Object_29
    print("\nChecking for Object_29 records without valid VESPA links...")
    
    # Sample check - get records without field_792
    url = 'https://api.knack.com/v1/objects/object_29/records'
    filters = {
        "match": "and",
        "rules": [
            {
                "field": "field_792",
                "operator": "is",
                "value": ""
            }
        ]
    }
    
    params = {
        'page': 1,
        'rows_per_page': 1,
        'filters': str(filters)
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        orphan_count = data.get('total_records', 0)
        print(f"Object_29 records without VESPA link: {orphan_count:,}")

def estimate_expected_records():
    """Estimate expected number of question responses"""
    print("\n4. Estimating expected question responses...")
    print("=" * 80)
    
    # Get student count
    students = supabase.table('students').select('id', count='exact', head=True).execute()
    student_count = students.count
    
    # Assume 65 questions per cycle, 3 cycles
    questions_per_cycle = 65
    cycles = 3
    
    max_possible = student_count * questions_per_cycle * cycles
    print(f"Students: {student_count:,}")
    print(f"Questions per cycle: {questions_per_cycle}")
    print(f"Cycles: {cycles}")
    print(f"Maximum possible responses: {max_possible:,}")
    
    # More realistic estimate (not all students complete all questions)
    completion_rate = 0.85  # 85% completion rate
    realistic_estimate = int(max_possible * completion_rate)
    print(f"Realistic estimate (85% completion): {realistic_estimate:,}")

def main():
    print("SYNC VERIFICATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        knack_total = check_knack_records()
        supabase_total = check_supabase_records()
        check_vespa_to_student_mapping()
        estimate_expected_records()
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print(f"Knack Object_29 records: {knack_total:,}")
        print(f"Supabase question_responses: {supabase_total:,}")
        
        if supabase_total < knack_total * 0.5:
            print("\n⚠️  WARNING: Supabase has less than 50% of Knack records!")
            print("   This suggests the sync may have stopped early.")
        elif supabase_total > knack_total * 1.5:
            print("\n⚠️  WARNING: Supabase has many more records than Knack!")
            print("   This suggests duplicate data from multiple sync attempts.")
        else:
            print("\n✅ Record counts seem reasonable.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()