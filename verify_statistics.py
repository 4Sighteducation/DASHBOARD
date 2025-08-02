#!/usr/bin/env python3
"""
Verify and compare school vs national statistics
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_statistics():
    """Compare school and national statistics"""
    
    print("=== SCHOOL STATISTICS ===")
    # Get a sample of school statistics
    school_stats = supabase.table('school_statistics')\
        .select('*')\
        .eq('cycle', 1)\
        .eq('element', 'vision')\
        .eq('academic_year', '2024-25')\
        .limit(5)\
        .execute()
    
    print(f"Found {len(school_stats.data)} school statistics for vision, cycle 1, 2024-25")
    for stat in school_stats.data[:3]:
        est = supabase.table('establishments').select('name').eq('id', stat['establishment_id']).execute()
        est_name = est.data[0]['name'] if est.data else 'Unknown'
        print(f"\n{est_name}:")
        print(f"  Mean: {stat['mean']}")
        print(f"  Std Dev: {stat['std_dev']}")
        print(f"  Count: {stat['count']}")
        print(f"  Distribution: {stat['distribution']}")
    
    print("\n\n=== NATIONAL STATISTICS ===")
    # Get national statistics
    national_stats = supabase.table('national_statistics')\
        .select('*')\
        .eq('cycle', 1)\
        .eq('element', 'vision')\
        .eq('academic_year', '2024/2025')\
        .execute()
    
    if national_stats.data:
        nat = national_stats.data[0]
        print(f"National statistics for vision, cycle 1, 2024/2025:")
        print(f"  Mean: {nat['mean']}")
        print(f"  Std Dev: {nat['std_dev']}")
        print(f"  Count: {nat['count']} (total students)")
        print(f"  Distribution: {nat['distribution']}")
        
        # Compare totals
        print(f"\n\n=== COMPARISON ===")
        total_school_count = sum(s['count'] for s in school_stats.data)
        print(f"Sum of school counts (sample): {total_school_count}")
        print(f"National count: {nat['count']}")
        print(f"\nNational mean should be weighted average of all school means")
    else:
        print("No national statistics found")
    
    # Check academic year format
    print("\n\n=== ACADEMIC YEAR FORMAT CHECK ===")
    school_years = supabase.table('school_statistics').select('academic_year').limit(10).execute()
    national_years = supabase.table('national_statistics').select('academic_year').limit(10).execute()
    
    school_year_formats = set(s['academic_year'] for s in school_years.data)
    national_year_formats = set(n['academic_year'] for n in national_years.data)
    
    print(f"School statistics year formats: {school_year_formats}")
    print(f"National statistics year formats: {national_year_formats}")

if __name__ == "__main__":
    verify_statistics()