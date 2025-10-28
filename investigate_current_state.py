#!/usr/bin/env python3
"""
Quick investigation - what's actually in the database right now?
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n" + "=" * 80)
print("CURRENT DATABASE STATE INVESTIGATION")
print("=" * 80)

# Check all students by academic year
print("\n📊 STUDENTS BY ACADEMIC YEAR:")
all_students = []
offset = 0
while True:
    batch = supabase.table('students').select('academic_year').range(offset, offset + 999).execute()
    if not batch.data:
        break
    all_students.extend(batch.data)
    offset += 1000
    if len(batch.data) < 1000:
        break

from collections import Counter
year_counts = Counter(s.get('academic_year') for s in all_students)
for year in sorted(year_counts.keys(), reverse=True):
    print(f"   {year}: {year_counts[year]:,} students")

print(f"\n   TOTAL: {len(all_students):,} students")

# Check VESPA scores by year
print("\n📊 VESPA SCORES BY ACADEMIC YEAR:")
all_scores = []
offset = 0
while True:
    batch = supabase.table('vespa_scores').select('academic_year,cycle').range(offset, offset + 999).execute()
    if not batch.data:
        break
    all_scores.extend(batch.data)
    offset += 1000
    if len(batch.data) < 1000:
        break

year_counts = Counter(f"{s.get('academic_year')} - Cycle {s.get('cycle')}" for s in all_scores)
for key in sorted(year_counts.keys()):
    print(f"   {key}: {year_counts[key]:,} scores")

print(f"\n   TOTAL: {len(all_scores):,} scores")

# Sample some 2024/2025 students
print("\n📝 SAMPLE 2024/2025 STUDENTS:")
sample = supabase.table('students').select('email,name,knack_id').eq('academic_year', '2024/2025').limit(5).execute()
for i, s in enumerate(sample.data, 1):
    print(f"   {i}. {s.get('email')} - {s.get('name')} (Knack: {s.get('knack_id', 'N/A')})")

print("\n" + "=" * 80)

