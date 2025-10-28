#!/usr/bin/env python3
"""
Check why students are being skipped - establishment mismatch?
"""
import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"

print("Loading establishments from Supabase...")
establishments = supabase.table('establishments').select('knack_id,name').execute()
sb_establishment_ids = {est['knack_id']: est['name'] for est in establishments.data}

print(f"\nEstablishments in Supabase: {len(sb_establishment_ids)}")

print("\nReading CSV sample...")
df = pd.read_csv(CSV_PATH, nrows=1000, low_memory=False)

# Filter for 2024-2025
df['created_date'] = pd.to_datetime(df['created'], errors='coerce')
archive_data = df[
    (df['created_date'] >= '2024-09-01') & 
    (df['created_date'] <= '2025-08-31')
]

print(f"2024-2025 records in sample: {len(archive_data)}")

# Check establishment field
print(f"\nChecking field_133 (establishment)...")
establishments_in_csv = archive_data['field_133'].dropna().unique()

print(f"Unique establishments in CSV: {len(establishments_in_csv)}")

print("\n🔍 Matching Check:")
matched = 0
not_matched = 0
not_matched_ids = []

for est_id in establishments_in_csv[:10]:  # Check first 10
    if str(est_id) in sb_establishment_ids:
        matched += 1
        print(f"   ✓ {est_id} → {sb_establishment_ids[str(est_id)]}")
    else:
        not_matched += 1
        not_matched_ids.append(est_id)
        print(f"   ✗ {est_id} → NOT FOUND in Supabase")

print(f"\n📊 Summary:")
print(f"   Matched: {matched}")
print(f"   Not matched: {not_matched}")

if not_matched > 0:
    print(f"\n⚠️  PROBLEM: Establishment IDs in CSV don't match Supabase!")
    print(f"   CSV might use different ID format or establishments are missing")

