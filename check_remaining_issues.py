#!/usr/bin/env python3
"""
Check if all issues have been resolved
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_all_issues():
    print("=== CHECKING ALL ISSUES ===\n")
    
    # 1. Check Super Users
    print("1. SUPER USERS:")
    super_users = supabase.table('super_users').select('id', count='exact').execute()
    print(f"   Total super users: {super_users.count}")
    if super_users.count > 0:
        samples = supabase.table('super_users').select('name', 'email').limit(3).execute()
        for user in samples.data:
            print(f"   - {user['name']} ({user['email']})")
    
    # 2. Check Trusts
    print("\n2. TRUSTS:")
    trusts = supabase.table('trusts').select('*').execute()
    print(f"   Total trusts: {len(trusts.data)}")
    for trust in trusts.data:
        print(f"   - {trust['name']} (ID: {trust['id']})")
    
    all_establishments = supabase.table('establishments').select('id', 'name', 'trust_id').execute()
    establishments_with_trusts = [e for e in all_establishments.data if e['trust_id'] is not None]
    print(f"   Establishments with trusts: {len(establishments_with_trusts)}")
    for est in establishments_with_trusts[:5]:  # Show first 5
        print(f"     - {est['name']}")
    
    # 3. Check Comparison Cache
    print("\n3. COMPARISON CACHE:")
    try:
        cache = supabase.table('comparison_cache').select('id', count='exact').execute()
        print(f"   Total cached comparisons: {cache.count}")
    except:
        print("   Comparison cache table not found or empty (expected for new system)")
    
    # 4. Check School Statistics
    print("\n4. SCHOOL STATISTICS:")
    stats = supabase.table('school_statistics').select('id', count='exact').execute()
    print(f"   Total statistics records: {stats.count}")
    
    # Check for null std_dev
    sample_stats = supabase.table('school_statistics').select('establishment_id', 'std_dev', 'distribution', 'mean').limit(5).execute()
    null_std_dev = sum(1 for s in sample_stats.data if s['std_dev'] is None)
    null_distribution = sum(1 for s in sample_stats.data if s['distribution'] is None or s['distribution'] == [0]*11)
    
    print(f"   Sample of 5 records:")
    print(f"   - Records with null std_dev: {null_std_dev}")
    print(f"   - Records with null/empty distribution: {null_distribution}")
    
    # 5. Check National Statistics
    print("\n5. NATIONAL STATISTICS:")
    national = supabase.table('national_statistics').select('id', count='exact').execute()
    print(f"   Total national statistics: {national.count}")
    
    # Check distribution
    nat_sample = supabase.table('national_statistics').select('cycle', 'element', 'distribution').limit(5).execute()
    for record in nat_sample.data:
        dist_sum = sum(record['distribution']) if record['distribution'] else 0
        print(f"   - Cycle {record['cycle']}, {record['element']}: distribution sum = {dist_sum}")
    
    # 6. Check current_school_averages view
    print("\n6. CURRENT_SCHOOL_AVERAGES VIEW:")
    try:
        averages = supabase.table('current_school_averages').select('*').limit(5).execute()
        print(f"   Sample records from view:")
        for avg in averages.data:
            print(f"   - {avg.get('establishment_name', 'Unknown')}: mean={avg.get('mean', 'N/A')}, std_dev={avg.get('std_dev', 'NULL')}")
    except Exception as e:
        print(f"   Error reading view: {e}")

if __name__ == "__main__":
    check_all_issues()