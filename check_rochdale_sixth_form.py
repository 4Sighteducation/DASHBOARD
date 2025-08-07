"""
Check for Rochdale Sixth Form College specifically
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("="*70)
print("SEARCHING FOR: Rochdale Sixth Form College")
print("="*70)

# 1. Check establishments table
print("\n1. Checking establishments table...")
establishments = supabase.table('establishments').select('*').execute()

found = None
for est in establishments.data:
    name = est.get('name', '').lower()
    # Check various name patterns
    if 'rochdale' in name:
        print(f"\n✓ FOUND: {est['name']}")
        print(f"  ID: {est['id']}")
        print(f"  Trust: {est.get('trust_name', 'None')}")
        found = est
        break

if not found:
    print("\n✗ NOT FOUND in establishments table")
    print("\nAll establishments containing 'sixth form' or 'college':")
    for est in establishments.data:
        name = est.get('name', '')
        if 'sixth form' in name.lower() or 'college' in name.lower():
            print(f"  - {name}")
else:
    # 2. Check for students
    print(f"\n2. Checking students for {found['name']}...")
    students = supabase.table('students').select('id').eq('establishment_id', found['id']).execute()
    print(f"  Students: {len(students.data)}")
    
    if students.data:
        # 3. Check for VESPA scores
        print("\n3. Checking VESPA scores...")
        student_ids = [s['id'] for s in students.data[:50]]  # Check first 50
        scores = supabase.table('vespa_scores').select('id, cycle').in_('student_id', student_ids).execute()
        print(f"  VESPA scores: {len(scores.data)}")
        if scores.data:
            cycles = set(s['cycle'] for s in scores.data)
            print(f"  Cycles: {sorted(cycles)}")
    
    # 4. Check materialized view
    print(f"\n4. Checking comparative_metrics view...")
    in_view = supabase.table('comparative_metrics')\
        .select('establishment_name')\
        .eq('establishment_id', found['id'])\
        .limit(1)\
        .execute()
    
    if in_view.data:
        print(f"  ✓ IN materialized view as: {in_view.data[0]['establishment_name']}")
    else:
        print(f"  ✗ NOT in materialized view")
        print("\n  TO FIX: Run in Supabase SQL Editor:")
        print("  REFRESH MATERIALIZED VIEW comparative_metrics;")

print("\n" + "="*70)
