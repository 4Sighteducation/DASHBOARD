#!/usr/bin/env python3
"""
Verify Field Mappings in Object_10 CSV
Check that all fields we need actually exist before import
"""
import pandas as pd

CSV_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"

print("\n" + "=" * 80)
print("OBJECT_10 FIELD MAPPING VERIFICATION")
print("=" * 80)

# Read just the header and first few rows
print("\nReading CSV header and sample rows...")
df = pd.read_csv(CSV_PATH, nrows=10, low_memory=False)

print(f"Total columns in CSV: {len(df.columns)}\n")

# Fields we need to check
fields_to_check = {
    'Student Email': 'field_197_email',
    'Student Name': 'field_187_full',
    'Establishment/School': 'field_133',
    'Year Group': 'field_144',
    'Current Cycle': 'field_146',
    'Vision Current': 'field_147',
    'Effort Current': 'field_148',
    'Systems Current': 'field_149',
    'Practice Current': 'field_150',
    'Attitude Current': 'field_151',
    'Overall Current': 'field_152',
    'Vision C1': 'field_155',
    'Effort C1': 'field_156',
    'Systems C1': 'field_157',
    'Practice C1': 'field_158',
    'Attitude C1': 'field_159',
    'Overall C1': 'field_160',
    'Vision C2': 'field_161',
    'Effort C2': 'field_162',
    'Systems C2': 'field_163',
    'Practice C2': 'field_164',
    'Attitude C2': 'field_165',
    'Overall C2': 'field_166',
    'Vision C3': 'field_167',
    'Effort C3': 'field_168',
    'Systems C3': 'field_169',
    'Practice C3': 'field_170',
    'Attitude C3': 'field_171',
    'Overall C3': 'field_172',
    'Course': 'field_2299',
    'Faculty': 'field_782',
    'Group': 'field_223',
}

print("CHECKING CRITICAL FIELDS:")
print("-" * 80)

missing_fields = []
found_fields = []

for description, field_name in fields_to_check.items():
    if field_name in df.columns:
        # Get sample value
        sample_val = df[field_name].dropna().iloc[0] if df[field_name].count() > 0 else "NULL"
        found_fields.append(field_name)
        print(f"OK  {description:25s} ({field_name:20s}) = {sample_val}")
    else:
        missing_fields.append((description, field_name))
        print(f"MISSING  {description:25s} ({field_name:20s})")

print("\n" + "=" * 80)
print(f"FOUND: {len(found_fields)} fields")
print(f"MISSING: {len(missing_fields)} fields")

if missing_fields:
    print("\n⚠️  MISSING FIELDS - NEED ALTERNATIVES:")
    print("-" * 80)
    for desc, field in missing_fields:
        print(f"\n{desc} ({field}) not found!")
        
        # Try to find similar fields
        if 'establishment' in desc.lower() or 'school' in desc.lower():
            print("  Searching for establishment-related fields...")
            est_fields = [c for c in df.columns if 'field_1' in c and c.startswith('field_1')]
            print(f"  Possible alternatives: {est_fields[:10]}")
            
            # Check for connection fields (usually arrays)
            for col in df.columns:
                if col.startswith('field_') and df[col].astype(str).str.contains('{').any():
                    sample = df[col].iloc[0]
                    if pd.notna(sample) and '{' in str(sample):
                        print(f"    Connection field? {col}: {str(sample)[:100]}")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)

if missing_fields:
    print("\n⚠️  Some fields are missing from the CSV!")
    print("   We need to identify the correct field names before import.")
    print("\n   Please check:")
    for desc, field in missing_fields:
        print(f"   - What field in Object_10 contains: {desc}?")
else:
    print("\n✅ All required fields found in CSV!")
    print("   Safe to proceed with import.")

# Show all column names
print("\n" + "=" * 80)
print("ALL COLUMNS IN CSV (first 50):")
print("=" * 80)
for i, col in enumerate(df.columns[:50], 1):
    non_null = df[col].count()
    print(f"  {i:3d}. {col:30s} ({non_null}/10 non-null)")

print(f"\n... and {len(df.columns) - 50} more columns")

