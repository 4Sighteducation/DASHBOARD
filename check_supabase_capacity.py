#!/usr/bin/env python3
"""
Check Supabase capacity and current usage
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("SUPABASE CAPACITY CHECK")
print("=" * 60)

# Count current records
tables = [
    'establishments',
    'students', 
    'vespa_scores',
    'question_responses',
    'school_statistics',
    'question_statistics'
]

total_records = 0
for table in tables:
    try:
        count = supabase.table(table).select('id', count='exact').execute()
        print(f"\n{table}: {count.count:,} records")
        total_records += count.count
    except:
        print(f"\n{table}: Error counting")

print(f"\nTOTAL CURRENT RECORDS: {total_records:,}")

# Estimate after sync
print("\n" + "=" * 60)
print("ESTIMATED AFTER SYNC:")
print("=" * 60)

# Assuming 25K students, average 1.5 cycles each, 32 questions per cycle
estimated_responses = 25_000 * 1.5 * 32
print(f"Question responses: ~{estimated_responses:,}")
print(f"Total all tables: ~{total_records + estimated_responses:,}")

print("\n" + "=" * 60)
print("CAPACITY ANALYSIS:")
print("=" * 60)
print(f"Free tier limit: 10,000,000 rows")
print(f"Usage after sync: ~{(total_records + estimated_responses)/10_000_000*100:.1f}% of free tier")

# Estimate storage
avg_row_size = 100  # bytes per row estimate
total_size_mb = (total_records + estimated_responses) * avg_row_size / 1_024_000
print(f"\nEstimated storage: ~{total_size_mb:.1f} MB")
print(f"Free tier limit: 500 MB")
print(f"Usage: ~{total_size_mb/500*100:.1f}% of free tier storage")

print("\n✅ You should be WELL within free tier limits!")