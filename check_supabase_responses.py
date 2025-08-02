#!/usr/bin/env python3
"""
Check the current state of question_responses in Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_response_counts():
    """Check various counts and look for anomalies"""
    
    # Total count
    total = supabase.table('question_responses').select('id', count='exact').execute()
    print(f"Total question responses in Supabase: {total.count:,}")
    
    # Count by cycle
    print("\nResponses by cycle:")
    for cycle in [1, 2, 3]:
        cycle_count = supabase.table('question_responses').select('id', count='exact').eq('cycle', cycle).execute()
        print(f"  Cycle {cycle}: {cycle_count.count:,}")
    
    # Check for any duplicate combinations
    print("\nChecking for duplicate student/cycle/question combinations...")
    
    # Get a sample of data to analyze
    duplicate_check = supabase.rpc('check_duplicate_responses', {}).execute() if False else None
    
    # Alternative: Get raw data and check in Python
    print("\nFetching sample data to check for patterns...")
    
    # Get students with the most responses
    students_query = """
    SELECT student_id, COUNT(*) as response_count
    FROM question_responses
    GROUP BY student_id
    HAVING COUNT(*) > 96
    ORDER BY response_count DESC
    LIMIT 10
    """
    
    # Since we can't run raw SQL, let's check differently
    # Get total students
    students = supabase.table('students').select('id', count='exact').execute()
    print(f"\nTotal students: {students.count:,}")
    
    # Expected max responses per student: 32 questions * 3 cycles = 96
    print(f"Expected max responses per student: 96")
    print(f"Expected total responses (if all complete): {students.count * 96:,}")
    print(f"Actual total responses: {total.count:,}")
    print(f"Average responses per student: {total.count / students.count:.1f}")
    
    # Check the last few pages of students to see if there are patterns
    print("\nChecking for specific student anomalies...")
    
    # Get a sample of students and count their responses
    sample_students = supabase.table('students').select('id', 'knack_id').limit(10).execute()
    
    for student in sample_students.data:
        count = supabase.table('question_responses').select('id', count='exact').eq('student_id', student['id']).execute()
        if count.count > 96:
            print(f"  Student {student['knack_id']} has {count.count} responses (> 96!)")

def check_incomplete_sync():
    """Check if there are students without any responses"""
    
    print("\nChecking for students without responses...")
    
    # This would be better as a SQL query but working with Supabase client limitations
    # Get students with no responses
    all_students = supabase.table('students').select('id', 'knack_id').execute()
    
    no_response_count = 0
    sample_no_response = []
    
    for student in all_students.data[:100]:  # Check first 100 as sample
        count = supabase.table('question_responses').select('id', count='exact').eq('student_id', student['id']).execute()
        if count.count == 0:
            no_response_count += 1
            if len(sample_no_response) < 5:
                sample_no_response.append(student['knack_id'])
    
    if no_response_count > 0:
        print(f"Found {no_response_count} students (in first 100) with no responses")
        print(f"Sample knack_ids: {sample_no_response}")

if __name__ == "__main__":
    check_response_counts()
    check_incomplete_sync()