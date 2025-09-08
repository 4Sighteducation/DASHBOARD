#!/usr/bin/env python3
"""
More thorough check of question IDs
"""
import os
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print("❌ Missing Supabase credentials")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

print("=" * 80)
print("THOROUGH CHECK OF QUESTION IDS")
print("=" * 80)

# Check for Shrewsbury specifically
establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5'

print("\n1. Getting Shrewsbury students...")
print("-" * 40)

students = supabase.table('students')\
    .select('id')\
    .eq('establishment_id', establishment_id)\
    .limit(5)\
    .execute()

if students.data:
    student_ids = [s['id'] for s in students.data]
    print(f"Using {len(student_ids)} student IDs for testing")
    
    print("\n2. Checking question_responses for these students...")
    print("-" * 40)
    
    # Get all responses for these students
    responses = supabase.table('question_responses')\
        .select('question_id, response_value, academic_year, cycle')\
        .in_('student_id', student_ids)\
        .execute()
    
    if responses.data:
        # Count question IDs
        question_counts = Counter()
        for r in responses.data:
            q_id = r.get('question_id')
            if q_id:
                question_counts[q_id] += 1
        
        print(f"Found {len(responses.data)} total responses")
        print(f"Unique question IDs: {len(question_counts)}")
        print("\nQuestion ID distribution:")
        for q_id, count in sorted(question_counts.items()):
            print(f"  {q_id}: {count} responses")
    else:
        print("No responses found for these students")

print("\n3. Checking ALL question_responses (no filter)...")
print("-" * 40)

# Get distinct question IDs using raw SQL
try:
    result = supabase.rpc('get_distinct_question_ids', {}).execute()
    print(f"Result from RPC: {result.data}")
except:
    # If RPC doesn't exist, try regular query
    print("RPC not available, using regular query...")
    
    # Try paginated approach
    all_question_ids = set()
    offset = 0
    limit = 1000
    
    for page in range(5):  # Check first 5 pages
        responses = supabase.table('question_responses')\
            .select('question_id')\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not responses.data:
            break
            
        for r in responses.data:
            if r.get('question_id'):
                all_question_ids.add(r['question_id'])
        
        offset += limit
        
        print(f"  Page {page + 1}: Found {len(responses.data)} rows, total unique IDs so far: {len(all_question_ids)}")
    
    print(f"\nTotal unique question IDs found: {len(all_question_ids)}")
    print("\nAll question IDs:")
    for q_id in sorted(all_question_ids):
        print(f"  - {q_id}")

print("\n4. Checking questions table structure...")
print("-" * 40)

try:
    # Try with different column names
    for col_name in ['text', 'question_text', 'questionText', 'description', 'question']:
        try:
            questions = supabase.table('questions')\
                .select(f'id, {col_name}')\
                .limit(1)\
                .execute()
            print(f"✅ Column '{col_name}' exists in questions table")
            break
        except:
            continue
    else:
        # Just get all columns
        questions = supabase.table('questions')\
            .select('*')\
            .limit(1)\
            .execute()
        
        if questions.data and len(questions.data) > 0:
            print("Questions table columns:", list(questions.data[0].keys()))
except Exception as e:
    print(f"Error accessing questions table: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
