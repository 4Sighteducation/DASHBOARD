#!/usr/bin/env python3
"""
Find the establishment field in Object_10 CSV
"""
import pandas as pd

CSV_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"

print("\nSearching for establishment field in Object_10...")
print("=" * 80)

# Read sample
df = pd.read_csv(CSV_PATH, nrows=100, low_memory=False)

# Known establishment Knack IDs from your Supabase query
known_establishments = [
    "68762ad8e8f6ae031cc85ad7",  # Alderbrook School
    "66e992c840019a02be8dbc4b",  # Archbishop McGrath
    "6348122e18efc40021de62cd",  # Ashlawn School
    "61680fc13a0bfd001e8ca3ca",  # Ashlyns School
]

print("\nLooking for fields containing known establishment IDs...")

for col in df.columns:
    if not col.startswith('field_'):
        continue
    
    # Check if any cell contains known establishment IDs
    col_str = df[col].astype(str)
    
    for est_id in known_establishments:
        if col_str.str.contains(est_id, regex=False).any():
            print(f"\nFOUND: {col}")
            print(f"  Contains establishment ID: {est_id}")
            # Show sample values
            sample_vals = df[col].dropna().head(5)
            print(f"  Sample values:")
            for val in sample_vals:
                print(f"    {str(val)[:100]}")
            break

# Also check for any array/connection fields
print("\n" + "=" * 80)
print("Checking for array/connection fields (contain curly braces)...")
print("=" * 80)

connection_fields = []
for col in df.columns:
    if col.startswith('field_'):
        col_str = df[col].astype(str)
        if col_str.str.contains(r'\{.*\}', regex=True).any():
            # Count how many non-null
            non_null = df[col].count()
            if non_null > 5:  # At least 5 records have values
                connection_fields.append((col, non_null))

print(f"\nFound {len(connection_fields)} potential connection fields:")
for field, count in connection_fields[:15]:
    sample = df[field].dropna().iloc[0] if df[field].count() > 0 else None
    print(f"  {field:20s} ({count:2d}/100 non-null) = {str(sample)[:80]}")

print("\n" + "=" * 80)
print("LOOKING AT STUDENT KNACK IDs IN DATABASE...")
print("=" * 80)

# You said student knack_ids look like: 66e7558354f37302e45b8f8c
# These are Object_10 record IDs (not establishment IDs)
print("\nStudent knack_ids in Supabase are Object_10 record IDs")
print("This means students table was created FROM Object_10")
print("\nSo in Object_10 CSV:")
print("  'id' column = what becomes student.knack_id in Supabase")
print("  Establishment field = needs to be found")

