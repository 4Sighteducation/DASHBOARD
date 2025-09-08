#!/usr/bin/env python3
"""
Check why questionnaire insights are showing 0%
"""
import os
from dotenv import load_dotenv
from supabase import create_client
import json

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
print("CHECKING QUESTIONNAIRE INSIGHTS DATA")
print("=" * 80)

# Load question mapping to understand the insights
print("\n1. Loading Question Mapping...")
print("-" * 40)

try:
    with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
        questions = json.load(f)
        
    # Find insight questions
    insight_questions = {}
    for q in questions:
        if 'insight' in q.get('questionText', '').lower() or 'outcome' in q.get('questionId', ''):
            insight_questions[q['questionId']] = q['questionText']
    
    print(f"Found {len(insight_questions)} insight/outcome questions:")
    for qid, text in list(insight_questions.items())[:5]:
        print(f"  {qid}: {text[:60]}...")
        
except Exception as e:
    print(f"Error loading questions: {e}")

# Check for Shrewsbury
establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5'

print("\n2. Checking Shrewsbury's Question Responses...")
print("-" * 40)

# Get students
students = supabase.table('students')\
    .select('id')\
    .eq('establishment_id', establishment_id)\
    .execute()

if students.data:
    student_ids = [s['id'] for s in students.data]
    print(f"Found {len(student_ids)} students")
    
    # Check for outcome questions specifically
    outcome_question_ids = [
        'outcome_q_confident',
        'outcome_q_equipped', 
        'outcome_q_support',
        'growth_mindset',
        'academic_momentum',
        'study_effectiveness',
        'exam_confidence',
        'organization_skills',
        'resilience',
        'stress_management',
        'active_learning',
        'support_readiness',
        'time_management',
        'academic_confidence'
    ]
    
    print("\n3. Checking Responses for Each Insight Question...")
    print("-" * 40)
    
    for question_id in outcome_question_ids:
        # Check if responses exist
        responses = supabase.table('question_responses')\
            .select('response_value, academic_year, cycle')\
            .in_('student_id', student_ids[:50])\
            .eq('question_id', question_id)\
            .limit(100)\
            .execute()
        
        if responses.data:
            # Group by academic year and cycle
            by_year_cycle = {}
            for r in responses.data:
                key = f"{r.get('academic_year', 'Unknown')} Cycle {r.get('cycle', '?')}"
                if key not in by_year_cycle:
                    by_year_cycle[key] = []
                if r.get('response_value'):
                    by_year_cycle[key].append(r['response_value'])
            
            print(f"\n{question_id}:")
            for key, values in sorted(by_year_cycle.items()):
                if values:
                    avg = sum(values) / len(values)
                    print(f"  {key}: {len(values)} responses, avg={avg:.1f}")
                else:
                    print(f"  {key}: No valid responses")
        else:
            print(f"\n{question_id}: ❌ NO DATA FOUND")

print("\n4. Checking Question Statistics Table...")
print("-" * 40)

# Check if statistics exist for these questions
for question_id in outcome_question_ids[:3]:  # Check first 3
    stats = supabase.table('question_statistics')\
        .select('mean, academic_year, cycle')\
        .eq('establishment_id', establishment_id)\
        .eq('question_id', question_id)\
        .execute()
    
    if stats.data:
        print(f"\n{question_id} statistics:")
        for s in stats.data:
            print(f"  {s['academic_year']} Cycle {s['cycle']}: mean={s['mean']}")
    else:
        print(f"\n{question_id}: No statistics found")

print("\n5. Testing API Endpoint...")
print("-" * 40)

import requests

api_url = "https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/qla"
params = {
    'establishment_id': establishment_id,
    'academic_year': '2025-26',
    'cycle': 1
}

try:
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'insights' in data:
            print(f"✅ API returned {len(data['insights'])} insights")
            for insight in data['insights'][:3]:
                print(f"  {insight.get('category', 'Unknown')}: {insight.get('percentage', 0)}%")
        else:
            print("❌ No insights in API response")
    else:
        print(f"❌ API error: {response.status_code}")
except Exception as e:
    print(f"❌ API call failed: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nPossible causes for 0% insights:")
print("1. Question IDs don't match between Knack and database")
print("2. Responses exist but aren't being aggregated correctly")
print("3. API isn't calculating percentages properly")
print("4. Frontend isn't displaying the data correctly")
