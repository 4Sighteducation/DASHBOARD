#!/usr/bin/env python3
"""
Quick script to check the actual table structure in Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def check_tables():
    """Check what tables and columns exist in Supabase"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("\n" + "="*60)
    print("CHECKING SUPABASE TABLE STRUCTURE")
    print("="*60)
    
    # Try to get a sample from each table
    tables_to_check = [
        'vespa_scores',
        'question_responses',
        'students',
        'establishments',
        'question_statistics',
        'school_statistics'
    ]
    
    for table_name in tables_to_check:
        print(f"\n📊 Checking {table_name}...")
        try:
            # Get one record to see column structure
            result = supabase.table(table_name).select('*').limit(1).execute()
            
            if result.data and len(result.data) > 0:
                columns = list(result.data[0].keys())
                print(f"   Columns: {', '.join(sorted(columns))}")
                
                # Check if academic_year column exists
                if 'academic_year' in columns:
                    print(f"   ✅ Has academic_year column")
                    
                    # Get sample academic years
                    years_result = supabase.table(table_name)\
                        .select('academic_year')\
                        .limit(10)\
                        .execute()
                    
                    sample_years = set()
                    for record in years_result.data:
                        if record.get('academic_year'):
                            sample_years.add(record['academic_year'])
                    
                    if sample_years:
                        print(f"   Sample years: {sorted(sample_years)}")
                else:
                    print(f"   ❌ No academic_year column")
            else:
                print(f"   ⚠️  Table is empty")
                
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                print(f"   ❌ Table does not exist")
            else:
                print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    check_tables()
