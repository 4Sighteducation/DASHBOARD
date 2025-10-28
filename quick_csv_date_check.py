#!/usr/bin/env python3
"""
Quick check of date ranges in the full CSV
"""
import pandas as pd
from datetime import datetime

CSV_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"

print("🔍 Analyzing date ranges in Object_10...")
print("Reading first 50,000 records to get better sample...\n")

# Read larger sample
df = pd.read_csv(CSV_PATH, nrows=50000, low_memory=False)

print(f"✅ Loaded {len(df)} records\n")

# Analyze created dates
print("=" * 70)
print("CREATED DATE ANALYSIS")
print("=" * 70)
df['created_date'] = pd.to_datetime(df['created'], errors='coerce')
created_valid = df['created_date'].dropna()

print(f"Records with created dates: {len(created_valid):,}")
print(f"Earliest: {created_valid.min()}")
print(f"Latest: {created_valid.max()}")

# Group by year-month
df['created_month'] = df['created_date'].dt.to_period('M')
monthly = df['created_month'].value_counts().sort_index()

print(f"\n📅 Records by Month (last 24 months):")
for month in monthly.tail(24).sort_index(ascending=False).items():
    print(f"   {month[0]}: {month[1]:,} records")

# Analyze completion dates
print("\n" + "=" * 70)
print("COMPLETION DATE ANALYSIS (field_855_date)")
print("=" * 70)
df['completion_date'] = pd.to_datetime(df['field_855_date'], errors='coerce')
completion_valid = df['completion_date'].dropna()

print(f"Records with completion dates: {len(completion_valid):,} ({len(completion_valid)/len(df)*100:.1f}%)")
print(f"Records with NULL completion: {len(df) - len(completion_valid):,} ({(len(df)-len(completion_valid))/len(df)*100:.1f}%)")

if len(completion_valid) > 0:
    print(f"Earliest: {completion_valid.min()}")
    print(f"Latest: {completion_valid.max()}")
    
    # Group by year
    df['completion_year'] = df['completion_date'].dt.year
    yearly = df['completion_year'].value_counts().sort_index()
    print(f"\n📅 By Year:")
    for year in yearly.sort_index(ascending=False).items():
        print(f"   {int(year[0]) if not pd.isna(year[0]) else 'NULL'}: {year[1]:,} records")

# Recommendation
print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)

pct_2024_2025 = 0
if len(created_valid) > 0:
    created_2024_2025 = df[(df['created_date'] >= '2024-09-01') & (df['created_date'] <= '2025-08-31')]
    pct_2024_2025 = len(created_2024_2025) / len(df) * 100
    print(f"\n📊 Records created in 2024-2025 academic year:")
    print(f"   (Sept 1, 2024 - Aug 31, 2025)")
    print(f"   Count: {len(created_2024_2025):,} ({pct_2024_2025:.1f}% of sample)")

if pct_2024_2025 > 50:
    print(f"\n✅ This snapshot contains significant 2024-2025 data")
    print(f"   Recommend: Use 'created' date for academic year calculation")
else:
    print(f"\n⚠️  This snapshot contains mostly historical data")
    print(f"   Question: Is this the correct snapshot for 2024-2025 archive?")










