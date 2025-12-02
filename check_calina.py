import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Supabase credentials not found")
    exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Search for Calina Allen
print("=" * 80)
print("SEARCHING FOR: Calina Allen from Penglais School")
print("=" * 80)

# Find student
students = client.table('students').select('*').ilike('email', '%calina%').execute()

if not students.data:
    students = client.table('students').select('*').ilike('name', '%Calina%Allen%').execute()

if students.data:
    for student in students.data:
        print(f"\nSTUDENT FOUND:")
        print(f"  ID: {student['id']}")
        print(f"  Name: {student['name']}")
        print(f"  Email: {student['email']}")
        print(f"  Establishment: {student.get('establishment_id')}")
        print(f"  Knack ID: {student.get('knack_id')}")
        
        # Get ALL vespa_scores for this student
        print(f"\n{'='*80}")
        print(f"VESPA SCORES FROM SUPABASE:")
        print(f"{'='*80}")
        
        scores = client.table('vespa_scores')\
            .select('*')\
            .eq('student_id', student['id'])\
            .order('completion_date', desc=True)\
            .execute()
        
        if scores.data:
            print(f"\nFound {len(scores.data)} score records:")
            for idx, score in enumerate(scores.data):
                print(f"\n  Record {idx+1}:")
                print(f"    Cycle: {score.get('cycle')}")
                print(f"    Vision: {score.get('vision')}")
                print(f"    Effort: {score.get('effort')}")
                print(f"    Systems: {score.get('systems')}")
                print(f"    Practice: {score.get('practice')}")
                print(f"    Attitude: {score.get('attitude')}")
                print(f"    Overall: {score.get('overall')}")
                print(f"    Completion Date: {score.get('completion_date')}")
                print(f"    Academic Year: {score.get('academic_year')}")
        else:
            print("  NO SCORES FOUND IN SUPABASE")
        
        # Get responses
        print(f"\n{'='*80}")
        print(f"STUDENT RESPONSES FROM SUPABASE:")
        print(f"{'='*80}")
        
        responses = client.table('student_responses')\
            .select('*')\
            .eq('student_id', student['id'])\
            .execute()
        
        if responses.data:
            for response in responses.data:
                print(f"\n  Cycle {response.get('cycle')}:")
                text = response.get('response_text', '')
                print(f"    Text: {text[:100]}..." if len(text) > 100 else f"    Text: {text}")
        else:
            print("  NO RESPONSES IN SUPABASE")
else:
    print("STUDENT NOT FOUND IN SUPABASE")

print(f"\n{'='*80}")
print("CHECK COMPLETE")
print(f"{'='*80}")
