#!/usr/bin/env python3
"""Get accurate counts from Supabase"""
import os
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("\nFetching ALL students...")
all_students = []
offset = 0

while True:
    batch = supabase.table('students').select('academic_year').range(offset, offset + 999).execute()
    if not batch.data:
        break
    all_students.extend(batch.data)
    offset += 1000
    if offset % 5000 == 0:
        print(f"  Fetched {offset}...")
    if len(batch.data) < 1000:
        break

years = Counter(s.get('academic_year') for s in all_students)

print("\nACCURATE STUDENT COUNTS:")
print("=" * 50)
for year in sorted(years.keys(), reverse=True):
    print(f"  {year}: {years[year]:,} students")
print("=" * 50)
print(f"  TOTAL: {len(all_students):,} students\n")

