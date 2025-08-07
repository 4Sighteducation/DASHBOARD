"""
Check Rochdale College status in Supabase - Standalone version
This version loads credentials the same way as sync_knack_to_supabase.py
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables (same as sync script)
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Check if credentials exist
if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n" + "="*60)
    print("ERROR: Supabase credentials not found!")
    print("="*60)
    print("\nThe .env file exists (your sync works), but Python can't load it.")
    print("\nTry this instead:")
    print("1. Run the SQL queries directly in Supabase Dashboard")
    print("2. Or set environment variables temporarily:")
    print("\nFor PowerShell:")
    print('$env:SUPABASE_URL = "your-supabase-url"')
    print('$env:SUPABASE_KEY = "your-supabase-key"')
    print("python check_rochdale_status_standalone.py")
    print("\nYou can find these values in your .env file")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print(f"✓ Connected to Supabase")

def search_rochdale():
    """Search for any establishment with Rochdale in the name"""
    print("\n" + "="*60)
    print("SEARCHING FOR ROCHDALE")
    print("="*60)
    
    try:
        # Method 1: Direct name search
        print("\n1. Searching establishments for 'Rochdale'...")
        result = supabase.table('establishments') \
            .select('id, name, trust_name') \
            .ilike('name', '%rochdale%') \
            .execute()
        
        if result.data:
            print(f"   ✓ Found {len(result.data)} establishment(s):")
            for est in result.data:
                print(f"      - {est['name']} (ID: {est['id']})")
            return result.data
        else:
            print("   ✗ No establishments found with 'Rochdale' in name")
            
        # Method 2: Check all colleges
        print("\n2. Checking all establishments with 'College' in name...")
        colleges = supabase.table('establishments') \
            .select('id, name') \
            .ilike('name', '%college%') \
            .execute()
            
        if colleges.data:
            print(f"   Found {len(colleges.data)} colleges:")
            found_rochdale = False
            for est in colleges.data:
                if 'rochdale' in est['name'].lower():
                    print(f"      >>> FOUND: {est['name']} (ID: {est['id']}) <<<")
                    found_rochdale = True
                # Show first 10 colleges for reference
                elif len([e for e in colleges.data[:10]]) <= 10:
                    print(f"      - {est['name']}")
            
            if not found_rochdale:
                print("\n   Note: Rochdale not found in college names")
                print("   Showing first 10 colleges above for reference")
        
        # Method 3: List ALL establishments to find exact name
        print("\n3. Getting full establishment list...")
        all_est = supabase.table('establishments') \
            .select('id, name') \
            .order('name') \
            .execute()
            
        if all_est.data:
            print(f"   Total establishments in database: {len(all_est.data)}")
            # Check various spellings
            possible_names = ['rochdale', 'rochedale', 'rochdale college', 'rochdale collage']
            for est in all_est.data:
                est_lower = est['name'].lower()
                for possible in possible_names:
                    if possible in est_lower:
                        print(f"   >>> MATCH FOUND: {est['name']} (ID: {est['id']})")
                        return [est]
            
            # Show some establishments for context
            print("\n   Sample of establishments (first 20):")
            for est in all_est.data[:20]:
                print(f"      - {est['name']}")
                
        return None
        
    except Exception as e:
        print(f"   ERROR: {e}")
        return None

def check_data_for_establishment(est_id, est_name):
    """Check what data exists for a specific establishment"""
    print(f"\n" + "="*60)
    print(f"CHECKING DATA FOR: {est_name}")
    print(f"ID: {est_id}")
    print("="*60)
    
    try:
        # Check students
        print("\n1. Checking students...")
        students = supabase.table('students') \
            .select('id, year_group, faculty') \
            .eq('establishment_id', est_id) \
            .execute()
        
        if students.data:
            print(f"   ✓ Students found: {len(students.data)}")
            # Get year group distribution
            year_groups = {}
            for s in students.data:
                yg = s.get('year_group', 'Unknown')
                year_groups[yg] = year_groups.get(yg, 0) + 1
            print(f"   Year groups: {year_groups}")
            
            # Check VESPA scores for these students
            student_ids = [s['id'] for s in students.data[:100]]  # Check first 100
            print("\n2. Checking VESPA scores...")
            scores = supabase.table('vespa_scores') \
                .select('id, cycle, overall') \
                .in_('student_id', student_ids) \
                .execute()
                
            if scores.data:
                print(f"   ✓ VESPA scores found: {len(scores.data)}")
                cycles = set(s['cycle'] for s in scores.data)
                print(f"   Cycles with data: {sorted(cycles)}")
            else:
                print(f"   ✗ No VESPA scores found for these students")
                
            # Check question responses
            print("\n3. Checking question responses...")
            responses = supabase.table('question_responses') \
                .select('id, cycle') \
                .in_('student_id', student_ids[:50]) \
                .limit(10) \
                .execute()
                
            if responses.data:
                print(f"   ✓ Question responses found")
                resp_cycles = set(r['cycle'] for r in responses.data)
                print(f"   Cycles with responses: {sorted(resp_cycles)}")
            else:
                print(f"   ✗ No question responses found")
                
        else:
            print(f"   ✗ No students found for this establishment")
            print(f"   This means the establishment exists but has no student data")
            
    except Exception as e:
        print(f"   ERROR checking data: {e}")

def check_in_materialized_view(est_name=None):
    """Check what's in the comparative_metrics materialized view"""
    print(f"\n" + "="*60)
    print("CHECKING MATERIALIZED VIEW")
    print("="*60)
    
    try:
        # Check if Rochdale is in the view
        if est_name:
            print(f"\n1. Searching for '{est_name}' in comparative_metrics view...")
            result = supabase.table('comparative_metrics') \
                .select('establishment_id, establishment_name') \
                .ilike('establishment_name', f'%{est_name}%') \
                .limit(1) \
                .execute()
                
            if result.data:
                print(f"   ✓ FOUND in materialized view as: {result.data[0]['establishment_name']}")
                return True
            else:
                print(f"   ✗ NOT found in materialized view")
        
        # Get view statistics
        print("\n2. Materialized view statistics...")
        
        # Get unique establishments
        all_records = supabase.table('comparative_metrics') \
            .select('establishment_id, establishment_name') \
            .execute()
            
        if all_records.data:
            establishments = {}
            for record in all_records.data:
                est_id = record['establishment_id']
                est_name_mv = record['establishment_name']
                if est_id not in establishments:
                    establishments[est_id] = est_name_mv
            
            print(f"   Total records in view: {len(all_records.data)}")
            print(f"   Unique establishments: {len(establishments)}")
            
            print("\n3. Sample of establishments in view:")
            for i, (est_id, name) in enumerate(list(establishments.items())[:15]):
                print(f"      - {name}")
                if i >= 14:
                    print(f"      ... and {len(establishments) - 15} more")
                    
            # Check for Rochdale variations
            print("\n4. Checking for Rochdale variations in view...")
            found_variations = False
            for est_id, name in establishments.items():
                if 'rochdale' in name.lower() or 'rochedale' in name.lower():
                    print(f"   >>> FOUND VARIATION: {name} (ID: {est_id})")
                    found_variations = True
                    
            if not found_variations:
                print("   No Rochdale variations found in materialized view")
                    
        else:
            print("   WARNING: Materialized view appears to be empty!")
            
        return False
        
    except Exception as e:
        print(f"   ERROR checking view: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("\n" + "="*70)
    print(" ROCHDALE COLLEGE DIAGNOSTIC - COMPREHENSIVE CHECK ")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Search for Rochdale
    rochdale = search_rochdale()
    
    # Step 2: Check data if found
    if rochdale:
        for est in rochdale:
            check_data_for_establishment(est['id'], est['name'])
    
    # Step 3: Check materialized view
    check_in_materialized_view('rochdale')
    
    # Conclusions
    print("\n" + "="*70)
    print(" DIAGNOSIS SUMMARY ")
    print("="*70)
    
    if rochdale:
        print("\n✓ Rochdale exists in establishments table")
        print("\nNEXT STEPS:")
        print("1. If Rochdale has students but no VESPA scores:")
        print("   - The issue is in Knack (no questionnaire responses)")
        print("   - Check if students have completed questionnaires in Knack")
        print("\n2. If Rochdale has VESPA scores but not in view:")
        print("   - Run in Supabase SQL Editor:")
        print("   - REFRESH MATERIALIZED VIEW comparative_metrics;")
        print("\n3. If no students at all:")
        print("   - Check Knack to see if Rochdale has student records")
        print("   - May need to investigate sync filtering logic")
    else:
        print("\n✗ Rochdale NOT found in establishments table!")
        print("\nThis means either:")
        print("1. It's named differently in Knack (check exact spelling)")
        print("2. It's filtered out during sync (check sync logs)")
        print("3. It doesn't exist in Knack yet")
        print("\nACTION: Check Knack directly for the exact establishment name")
    
    print("\n" + "="*70)
    print(" SQL QUERIES TO RUN IN SUPABASE ")
    print("="*70)
    print("\nCopy and run these in Supabase SQL Editor:\n")
    print("-- 1. Search for Rochdale with any spelling")
    print("SELECT id, name, trust_name FROM establishments")
    print("WHERE name ILIKE '%roch%' OR name ILIKE '%college%';")
    print("\n-- 2. Refresh materialized view if needed")
    print("REFRESH MATERIALIZED VIEW comparative_metrics;")
    print("\n-- 3. Check sync logs")
    print("SELECT * FROM sync_logs ORDER BY started_at DESC LIMIT 5;")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        print("\nThis might be a connection issue. Check your credentials.")
