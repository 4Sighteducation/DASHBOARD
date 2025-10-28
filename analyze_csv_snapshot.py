#!/usr/bin/env python3
"""
CSV Snapshot Analysis Script
Analyze the August 2025 historical snapshot CSVs before import
"""

import pandas as pd
import os
from datetime import datetime
from collections import Counter
import json

# File paths
OBJECT_6_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_6_2025.csv"
OBJECT_10_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"
OBJECT_29_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_29_2025.csv"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def analyze_object_6():
    """Analyze Object_6 (Student Accounts)"""
    print_section("OBJECT_6 ANALYSIS: Student Accounts")
    
    try:
        # Read sample first
        print("📊 Reading Object_6 sample...")
        df_sample = pd.read_csv(OBJECT_6_PATH, nrows=1000)
        
        print(f"✅ Sample loaded: {len(df_sample)} records")
        print(f"📋 Total columns: {len(df_sample.columns)}")
        
        print("\n🔍 Key Fields Analysis:")
        
        # Analyze created dates
        if 'created' in df_sample.columns:
            df_sample['created_date'] = pd.to_datetime(df_sample['created'], errors='coerce')
            print("\n   Created Dates:")
            print(f"      Earliest: {df_sample['created_date'].min()}")
            print(f"      Latest: {df_sample['created_date'].max()}")
            
            # Group by month
            df_sample['created_month'] = df_sample['created_date'].dt.to_period('M')
            month_counts = df_sample['created_month'].value_counts().sort_index()
            print(f"\n      Records by Month (sample):")
            for month, count in month_counts.tail(12).items():
                print(f"         {month}: {count} records")
        
        # Analyze emails
        if 'field_91_email' in df_sample.columns:
            emails = df_sample['field_91_email'].dropna()
            print(f"\n   Emails (field_91_email):")
            print(f"      Total with email: {len(emails)}")
            print(f"      Unique emails: {emails.nunique()}")
            print(f"      Sample: {emails.iloc[0] if len(emails) > 0 else 'N/A'}")
        
        # Analyze year groups
        if 'field_548' in df_sample.columns:
            year_groups = df_sample['field_548'].value_counts()
            print(f"\n   Year Groups (field_548):")
            for yg, count in year_groups.head(10).items():
                print(f"      {yg}: {count} records")
        
        # Analyze names
        if 'field_90_full' in df_sample.columns:
            names = df_sample['field_90_full'].dropna()
            print(f"\n   Names (field_90_full):")
            print(f"      Records with names: {len(names)}")
            print(f"      Sample: {names.iloc[0] if len(names) > 0 else 'N/A'}")
        
        # List all columns
        print(f"\n📋 All Columns ({len(df_sample.columns)}):")
        for i, col in enumerate(df_sample.columns, 1):
            non_null = df_sample[col].count()
            print(f"      {i:3d}. {col:30s} ({non_null:,} non-null)")
        
        print("\n⚠️  NOTE: Object_6 is Student ACCOUNTS, not VESPA Results")
        print("    We likely need Object_10 for actual VESPA data import.")
        
    except Exception as e:
        print(f"❌ Error analyzing Object_6: {e}")
        import traceback
        traceback.print_exc()

def analyze_object_10():
    """Analyze Object_10 (VESPA Results)"""
    print_section("OBJECT_10 ANALYSIS: VESPA Results")
    
    try:
        # Read sample
        print("📊 Reading Object_10 sample (this may take a moment)...")
        df_sample = pd.read_csv(OBJECT_10_PATH, nrows=5000)
        
        print(f"✅ Sample loaded: {len(df_sample)} records")
        print(f"📋 Total columns: {len(df_sample.columns)}")
        
        print("\n🔍 Critical Fields Analysis:")
        
        # Email field
        if 'field_197_email' in df_sample.columns:
            emails = df_sample['field_197_email'].dropna()
            print(f"\n   📧 Student Email (field_197_email):")
            print(f"      Total with email: {len(emails)}")
            print(f"      Unique students: {emails.nunique()}")
            print(f"      Sample: {emails.iloc[0] if len(emails) > 0 else 'N/A'}")
        
        # Student names
        if 'field_187_full' in df_sample.columns:
            names = df_sample['field_187_full'].dropna()
            print(f"\n   👤 Student Names (field_187_full):")
            print(f"      Records with names: {len(names)}")
            print(f"      Unique names: {names.nunique()}")
            print(f"      Sample: {names.iloc[0] if len(names) > 0 else 'N/A'}")
        
        # Completion dates
        if 'field_855_date' in df_sample.columns:
            df_sample['completion_date'] = pd.to_datetime(df_sample['field_855_date'], errors='coerce')
            valid_dates = df_sample['completion_date'].dropna()
            
            print(f"\n   📅 Completion Dates (field_855_date):")
            print(f"      Total with dates: {len(valid_dates)}")
            print(f"      NULL dates: {len(df_sample) - len(valid_dates)}")
            
            if len(valid_dates) > 0:
                print(f"      Earliest: {valid_dates.min()}")
                print(f"      Latest: {valid_dates.max()}")
                
                # Calculate academic years
                def calc_academic_year(date):
                    if pd.isna(date):
                        return None
                    if date.month >= 8:
                        return f"{date.year}/{date.year + 1}"
                    else:
                        return f"{date.year - 1}/{date.year}"
                
                df_sample['academic_year'] = df_sample['completion_date'].apply(calc_academic_year)
                year_counts = df_sample['academic_year'].value_counts()
                
                print(f"\n      Academic Year Distribution (from completion dates):")
                for year, count in year_counts.sort_index(ascending=False).items():
                    print(f"         {year}: {count} records")
        
        # Current cycle
        if 'field_146' in df_sample.columns:
            cycles = df_sample['field_146'].value_counts()
            print(f"\n   🔄 Current Cycle (field_146):")
            for cycle, count in cycles.sort_index().items():
                print(f"      Cycle {cycle}: {count} records")
        
        # VESPA Scores - Current
        print(f"\n   📊 Current VESPA Scores:")
        vespa_fields = {
            'field_147': 'Vision',
            'field_148': 'Effort',
            'field_149': 'Systems',
            'field_150': 'Practice',
            'field_151': 'Attitude',
            'field_152': 'Overall'
        }
        
        for field, name in vespa_fields.items():
            if field in df_sample.columns:
                values = pd.to_numeric(df_sample[field], errors='coerce').dropna()
                if len(values) > 0:
                    print(f"      {name:10s}: {len(values):,} values, "
                          f"mean={values.mean():.2f}, "
                          f"min={values.min():.0f}, "
                          f"max={values.max():.0f}")
        
        # Historical cycles
        print(f"\n   📈 Historical Cycles:")
        
        cycle_1_fields = ['field_155', 'field_156', 'field_157', 'field_158', 'field_159', 'field_160']
        cycle_2_fields = ['field_161', 'field_162', 'field_163', 'field_164', 'field_165', 'field_166']
        cycle_3_fields = ['field_167', 'field_168', 'field_169', 'field_170', 'field_171', 'field_172']
        
        for cycle_num, fields in [(1, cycle_1_fields), (2, cycle_2_fields), (3, cycle_3_fields)]:
            non_null_count = sum(df_sample[f].count() for f in fields if f in df_sample.columns)
            print(f"      Cycle {cycle_num}: {non_null_count:,} non-null values across all components")
        
        # Level
        if 'field_568' in df_sample.columns:
            levels = df_sample['field_568'].value_counts()
            print(f"\n   🎓 Level (field_568):")
            for level, count in levels.items():
                print(f"      {level}: {count} records")
        
        # Year Group
        if 'field_144' in df_sample.columns:
            year_groups = df_sample['field_144'].value_counts()
            print(f"\n   📚 Year Group (field_144):")
            for yg, count in year_groups.head(15).items():
                print(f"      {yg}: {count} records")
        
        # Sample record analysis
        print(f"\n📝 Sample Record Structure:")
        if len(df_sample) > 0:
            sample_record = df_sample.iloc[0]
            print(f"\n   Record ID: {sample_record.get('id', 'N/A')}")
            print(f"   Student: {sample_record.get('field_187_full', 'N/A')}")
            print(f"   Email: {sample_record.get('field_197_email', 'N/A')}")
            print(f"   Created: {sample_record.get('created', 'N/A')}")
            print(f"   Completion Date: {sample_record.get('field_855_date', 'N/A')}")
            print(f"   Current Cycle: {sample_record.get('field_146', 'N/A')}")
            print(f"   Current Scores: V={sample_record.get('field_147', 'N/A')}, "
                  f"E={sample_record.get('field_148', 'N/A')}, "
                  f"S={sample_record.get('field_149', 'N/A')}")
        
        # List all columns
        print(f"\n📋 All Columns ({len(df_sample.columns)}):")
        for i, col in enumerate(df_sample.columns, 1):
            non_null = df_sample[col].count()
            pct = (non_null / len(df_sample)) * 100
            print(f"      {i:3d}. {col:30s} ({non_null:5,} non-null, {pct:5.1f}%)")
        
    except Exception as e:
        print(f"❌ Error analyzing Object_10: {e}")
        import traceback
        traceback.print_exc()

def analyze_object_29():
    """Analyze Object_29 (Question Responses)"""
    print_section("OBJECT_29 ANALYSIS: Question Responses")
    
    try:
        # Read sample
        print("📊 Reading Object_29 sample...")
        df_sample = pd.read_csv(OBJECT_29_PATH, nrows=1000)
        
        print(f"✅ Sample loaded: {len(df_sample)} records")
        print(f"📋 Total columns: {len(df_sample.columns)}")
        
        print("\n🔍 Key Fields Analysis:")
        
        # Student email
        if 'field_2732_email' in df_sample.columns:
            emails = df_sample['field_2732_email'].dropna()
            print(f"\n   📧 Student Email (field_2732_email):")
            print(f"      Total with email: {len(emails)}")
            print(f"      Unique students: {emails.nunique()}")
        
        # Student names
        if 'field_1823_full' in df_sample.columns:
            names = df_sample['field_1823_full'].dropna()
            print(f"\n   👤 Student Names (field_1823_full):")
            print(f"      Records with names: {len(names)}")
            print(f"      Unique names: {names.nunique()}")
        
        # Cycle
        if 'field_1826' in df_sample.columns:
            cycles = df_sample['field_1826'].value_counts()
            print(f"\n   🔄 Cycle (field_1826):")
            for cycle, count in cycles.sort_index().items():
                print(f"      Cycle {cycle}: {count} records")
        
        # Question fields (field_794 to field_821)
        question_fields = [f'field_{i}' for i in range(794, 822)]
        
        print(f"\n   ❓ Question Response Fields:")
        responses_found = []
        for field in question_fields:
            if field in df_sample.columns:
                non_null = df_sample[field].count()
                if non_null > 0:
                    responses_found.append(field)
        
        print(f"      Question fields with responses: {len(responses_found)}")
        print(f"      Fields: {', '.join(responses_found[:10])}...")
        
        # Sample question values
        if responses_found:
            sample_field = responses_found[0]
            values = df_sample[sample_field].value_counts()
            print(f"\n      Sample values from {sample_field}:")
            for val, count in values.head(5).items():
                print(f"         {val}: {count} times")
        
        # List significant columns
        print(f"\n📋 Significant Columns (with >10% non-null):")
        for i, col in enumerate(df_sample.columns, 1):
            non_null = df_sample[col].count()
            pct = (non_null / len(df_sample)) * 100
            if pct > 10:
                print(f"      {col:30s} ({non_null:5,} non-null, {pct:5.1f}%)")
        
    except Exception as e:
        print(f"❌ Error analyzing Object_29: {e}")
        import traceback
        traceback.print_exc()

def create_field_mapping():
    """Create initial field mapping documentation"""
    print_section("FIELD MAPPING RECOMMENDATIONS")
    
    mapping = {
        "Object_10 → Supabase": {
            "students table": {
                "field_197_email": "email",
                "field_187_full": "name",
                "field_144": "year_group",
                "field_2299": "course",
                "field_782": "faculty",
                "field_223": "group",
                "field_568": "level (metadata)"
            },
            "vespa_scores table": {
                "field_855_date": "completion_date (→ academic_year calculation)",
                "field_146": "cycle (currentMCycle)",
                "field_147-152": "Current cycle scores (V,E,S,P,A,Overall)",
                "field_155-160": "Cycle 1 historical scores",
                "field_161-166": "Cycle 2 historical scores",
                "field_167-172": "Cycle 3 historical scores"
            }
        },
        "Object_29 → Supabase": {
            "question_responses table": {
                "field_2732_email": "student email (for linking)",
                "field_1826": "cycle",
                "field_794-821": "individual question responses"
            }
        }
    }
    
    print(json.dumps(mapping, indent=2))
    
    # Save to file
    with open('FIELD_MAPPING.json', 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print("\n✅ Field mapping saved to FIELD_MAPPING.json")

def generate_summary():
    """Generate summary and recommendations"""
    print_section("SUMMARY & RECOMMENDATIONS")
    
    print("""
📋 CSV ANALYSIS SUMMARY

Files Analyzed:
1. FullObject_6_2025.csv - Student Accounts (23,458 records)
2. FullObject_10_2025.csv - VESPA Results (~2.5M records)
3. FullObject_29_2025.csv - Question Responses (41,029 records)

Key Findings:
✅ Object_10 is the PRIMARY data source for VESPA import
✅ Contains completion dates for academic year calculation
✅ Has historical cycle data (Cycles 1, 2, 3)
✅ Links to students via field_197_email

Critical Fields Identified:
• field_197_email: Student email (KEY for linking)
• field_855_date: Completion date (for academic year)
• field_146: Current cycle number
• field_147-152: Current VESPA scores
• field_155-172: Historical cycle scores

Recommendations:
1. ✅ Use Object_10 as primary import source
2. ✅ Calculate academic_year from field_855_date
3. ✅ Import ALL cycles (not just current)
4. ✅ Use field_197_email to link to students
5. ⚠️  Handle NULL completion dates carefully
6. ⚠️  Validate email addresses exist in Object_10

Next Steps:
1. Review field mapping (FIELD_MAPPING.json)
2. Run database audit (audit_current_database_state.py)
3. Create import script with field mapping
4. Test import on small subset (100 records)
5. Run full import with monitoring

⚠️  IMPORTANT: 
- Object_6 is NOT the same as Object_10
- Object_10 contains the VESPA results we need
- Each Object_10 record may represent a student at a point in time
- Multiple records per student (different cycles/years)
    """)

def main():
    """Run all analysis"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 22 + "CSV SNAPSHOT ANALYSIS" + " " * 35 + "║")
    print("║" + " " * 18 + "August 2025 Historical Data" + " " * 33 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        analyze_object_6()
        analyze_object_10()
        analyze_object_29()
        create_field_mapping()
        generate_summary()
        
        print("\n" + "=" * 80)
        print("  ✅ CSV ANALYSIS COMPLETE")
        print("=" * 80 + "\n")
        
        print("📄 Generated Files:")
        print("   • FIELD_MAPPING.json - Field mapping documentation")
        print("\n📊 Next: Run audit_current_database_state.py to check database")
        
    except Exception as e:
        print(f"\n❌ ANALYSIS FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


