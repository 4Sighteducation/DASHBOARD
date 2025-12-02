import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("SEARCHING FOR: Ruairidh Chassels from Bedales School")
print("=" * 80)

# Search for student
students = client.table('students').select('*').ilike('name', '%Ruairidh%Chassels%').execute()

if not students.data:
    students = client.table('students').select('*').ilike('name', '%Chassels%').execute()

if not students.data:
    students = client.table('students').select('*').ilike('email', '%chassels%').execute()

if students.data:
    for student in students.data:
        print(f"\nSTUDENT FOUND:")
        print(f"  ID: {student['id']}")
        print(f"  Name: {student['name']}")
        print(f"  Email: {student['email']}")
        print(f"  Establishment: {student.get('establishment_id')}")
        print(f"  Knack ID: {student.get('knack_id')}")
        print(f"  Academic Year: {student.get('academic_year')}")
        
        # Get ALL vespa_scores
        print(f"\n{'='*80}")
        print(f"VESPA SCORES FROM SUPABASE:")
        print(f"{'='*80}")
        
        scores = client.table('vespa_scores')\
            .select('*')\
            .eq('student_id', student['id'])\
            .order('created_at', desc=True)\
            .execute()
        
        if scores.data:
            print(f"\nFound {len(scores.data)} score records:")
            for idx, score in enumerate(scores.data):
                print(f"\n  Record {idx+1}:")
                print(f"    ID: {score.get('id')}")
                print(f"    Cycle: {score.get('cycle')}")
                print(f"    Vision: {score.get('vision')}")
                print(f"    Effort: {score.get('effort')}")
                print(f"    Systems: {score.get('systems')}")
                print(f"    Practice: {score.get('practice')}")
                print(f"    Attitude: {score.get('attitude')}")
                print(f"    Overall: {score.get('overall')}")
                print(f"    Completion Date: {score.get('completion_date')}")
                print(f"    Created At: {score.get('created_at')}")
                print(f"    Updated At: {score.get('updated_at')}")
                print(f"    Academic Year: {score.get('academic_year')}")
                
                # Check if created today
                created = score.get('created_at', '')
                if created:
                    created_date = created[:10]
                    today = datetime.now().strftime('%Y-%m-%d')
                    if created_date == today:
                        print(f"    ⚠️ CREATED TODAY: {created_date}")
        else:
            print("  NO SCORES FOUND IN SUPABASE")
        
        # Get responses
        print(f"\n{'='*80}")
        print(f"STUDENT RESPONSES FROM SUPABASE:")
        print(f"{'='*80}")
        
        responses = client.table('student_responses')\
            .select('*')\
            .eq('student_id', student['id'])\
            .order('updated_at', desc=True)\
            .execute()
        
        if responses.data:
            for response in responses.data:
                print(f"\n  Cycle {response.get('cycle')}:")
                print(f"    Created: {response.get('created_at')}")
                print(f"    Updated: {response.get('updated_at')}")
                text = response.get('response_text', '')
                print(f"    Text: {text[:100]}..." if len(text) > 100 else f"    Text: {text}")
        else:
            print("  NO RESPONSES IN SUPABASE")
        
        # Get goals
        print(f"\n{'='*80}")
        print(f"STUDENT GOALS FROM SUPABASE:")
        print(f"{'='*80}")
        
        goals = client.table('student_goals')\
            .select('*')\
            .eq('student_id', student['id'])\
            .order('updated_at', desc=True)\
            .execute()
        
        if goals.data:
            for goal in goals.data:
                print(f"\n  Cycle {goal.get('cycle')}:")
                print(f"    Created: {goal.get('created_at')}")
                print(f"    Updated: {goal.get('updated_at')}")
                text = goal.get('goal_text', '')
                print(f"    Text: {text[:100]}..." if len(text) > 100 else f"    Text: {text}")
        else:
            print("  NO GOALS IN SUPABASE")

else:
    print("STUDENT NOT FOUND IN SUPABASE")
    print("\nTrying to search in students table with more detail...")
    all_bedales = client.table('students').select('id, name, email').execute()
    bedales_students = [s for s in all_bedales.data if 'bedales' in s.get('email', '').lower() or 'chassels' in s.get('name', '').lower()]
    if bedales_students:
        print(f"\nFound {len(bedales_students)} potential matches:")
        for s in bedales_students[:5]:
            print(f"  - {s['name']} ({s['email']})")

print(f"\n{'='*80}")
print("CHECK COMPLETE")
print(f"{'='*80}")
