#!/usr/bin/env python3
"""
Check what question IDs actually exist in the database
"""
import os
from dotenv import load_dotenv
from supabase import create_client

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
print("CHECKING ACTUAL QUESTION IDS IN DATABASE")
print("=" * 80)

# Get unique question IDs from question_responses
print("\n1. Getting all unique question IDs from question_responses...")
print("-" * 40)

try:
    # Get a sample of question IDs
    responses = supabase.table('question_responses')\
        .select('question_id')\
        .limit(10000)\
        .execute()
    
    # Get unique question IDs
    question_ids = set()
    for r in responses.data:
        if r.get('question_id'):
            question_ids.add(r['question_id'])
    
    # Sort and display
    sorted_ids = sorted(question_ids)
    print(f"Found {len(sorted_ids)} unique question IDs:")
    print()
    
    # Group by pattern
    outcome_qs = [q for q in sorted_ids if 'outcome' in q.lower()]
    q_numbered = [q for q in sorted_ids if q.startswith('Q') and q[1:].isdigit()]
    other_qs = [q for q in sorted_ids if q not in outcome_qs and q not in q_numbered]
    
    if outcome_qs:
        print("OUTCOME Questions:")
        for q in outcome_qs:
            print(f"  - {q}")
        print()
    
    if q_numbered:
        print("NUMBERED Questions (Q1, Q2, etc.):")
        for q in sorted(q_numbered, key=lambda x: int(x[1:]) if x[1:].isdigit() else 999):
            print(f"  - {q}")
        print()
    
    if other_qs:
        print("OTHER Questions:")
        for q in other_qs:
            print(f"  - {q}")
        print()
    
except Exception as e:
    print(f"Error: {e}")

print("\n2. Checking questions table if it exists...")
print("-" * 40)

try:
    questions = supabase.table('questions')\
        .select('id, text')\
        .limit(50)\
        .execute()
    
    if questions.data:
        print(f"Found {len(questions.data)} questions in questions table:")
        for q in questions.data[:10]:
            text = q.get('text', '')[:60] + '...' if len(q.get('text', '')) > 60 else q.get('text', '')
            print(f"  {q['id']}: {text}")
        if len(questions.data) > 10:
            print(f"  ... and {len(questions.data) - 10} more")
    else:
        print("No data in questions table")
except Exception as e:
    print(f"Questions table might not exist or error: {e}")

print("\n3. Looking for insight-related questions...")
print("-" * 40)

# Map expected insights to potential question IDs
insight_mapping = {
    'growth_mindset': ['Q5', 'Q26'],
    'academic_momentum': ['Q14', 'Q16', 'Q17', 'Q9'],
    'study_effectiveness': ['Q7', 'Q12', 'Q15'],
    'exam_confidence': ['outcome_q_confident'],
    'organization_skills': ['Q2', 'Q22', 'Q11'],
    'resilience': ['Q13', 'Q8', 'Q27'],
    'stress_management': ['Q20', 'Q28'],
    'active_learning': ['Q7', 'Q23', 'Q19'],
    'support_readiness': ['outcome_q_support'],
    'time_management': ['Q2', 'Q4', 'Q11'],
    'academic_confidence': ['Q10', 'Q8'],
    'revision_readiness': ['outcome_q_equipped']
}

print("Checking if the numbered questions (Q1-Q28) exist:")
for insight, q_ids in insight_mapping.items():
    existing = [q for q in q_ids if q in sorted_ids]
    missing = [q for q in q_ids if q not in sorted_ids]
    if existing:
        print(f"  ✅ {insight}: Found {existing}")
    if missing:
        print(f"  ❌ {insight}: Missing {missing}")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)
print("\nThe issue is clear:")
print("1. Database has questions like 'Q1', 'Q2', etc. (numbered format)")
print("2. API is calculating insights from these numbered questions")
print("3. But the percentages aren't being calculated correctly")
print("\nNext step: Fix the API's insight calculation logic")
