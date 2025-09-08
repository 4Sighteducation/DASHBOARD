#!/usr/bin/env python3
"""
Check if statistics exist for the insight questions
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
print("CHECKING STATISTICS FOR INSIGHT QUESTIONS")
print("=" * 80)

establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5'

# All the insight question IDs
insight_questions = [
    'q5', 'q26',  # growth_mindset
    'q14', 'q16', 'q17', 'q9',  # academic_momentum
    'q7', 'q12', 'q15',  # study_effectiveness
    'q2', 'q22', 'q11',  # organization_skills
    'q13', 'q8', 'q27',  # resilience
    'q20', 'q28',  # stress_management
    'q23', 'q19',  # active_learning (q7 already included)
    'q4',  # time_management (q2, q11 already included)
    'q10',  # academic_confidence (q8 already included)
]

# Remove duplicates
insight_questions = list(set(insight_questions))
insight_questions.sort(key=lambda x: int(x[1:]) if x[1:].isdigit() else 999)

print(f"\n1. Checking question_statistics for {len(insight_questions)} insight questions...")
print("-" * 40)

for question_id in insight_questions:
    stats = supabase.table('question_statistics')\
        .select('mean, count, distribution, academic_year, cycle')\
        .eq('establishment_id', establishment_id)\
        .eq('question_id', question_id)\
        .execute()
    
    if stats.data:
        print(f"\n{question_id}: ✅ {len(stats.data)} statistics found")
        for s in stats.data:
            dist = s.get('distribution', [])
            if dist and len(dist) >= 5:
                agreement = dist[3] + dist[4]  # Scores 4 and 5
                total = sum(dist)
                pct = (agreement / total * 100) if total > 0 else 0
                print(f"  {s['academic_year']} Cycle {s['cycle']}: mean={s['mean']:.2f}, count={s['count']}, agreement={pct:.1f}%")
            else:
                print(f"  {s['academic_year']} Cycle {s['cycle']}: mean={s['mean']:.2f}, count={s['count']}, NO DISTRIBUTION")
    else:
        print(f"\n{question_id}: ❌ NO STATISTICS FOUND")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)
print("\nIf statistics exist but API returns 0%:")
print("- The API query for statistics might be filtering incorrectly")
print("- The distribution array might not be populated")
print("- The calculation logic in the API might have a bug")
