"""
Standalone script to refresh the comparative_metrics materialized view
Run this after syncs to ensure the view is up to date
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import subprocess
import sys

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase credentials not found in .env")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("="*60)
print("REFRESHING COMPARATIVE_METRICS MATERIALIZED VIEW")
print("="*60)
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# First, check current state
try:
    # Get count before refresh
    result = supabase.table('comparative_metrics').select('establishment_id', count='exact').execute()
    print(f"\nCurrent records in view: {result.count}")
    
    # Check for Rochdale specifically
    rochdale = supabase.table('comparative_metrics')\
        .select('establishment_name')\
        .ilike('establishment_name', '%rochdale%')\
        .execute()
    
    if rochdale.data:
        print(f"Rochdale currently in view: YES")
    else:
        print(f"Rochdale currently in view: NO")
        
except Exception as e:
    print(f"Error checking current state: {e}")

# Try to refresh the view
print("\nAttempting to refresh materialized view...")
print("This may take 1-2 minutes depending on data size...")

try:
    # Method 1: Try RPC function
    supabase.rpc('refresh_materialized_view', {'view_name': 'comparative_metrics'}).execute()
    print("✓ Refresh initiated via RPC")
    success = True
except Exception as e:
    print(f"✗ RPC method failed: {e}")
    success = False
    
    # Method 2: Direct SQL (requires different approach)
    print("\nManual refresh required:")
    print("1. Go to Supabase Dashboard > SQL Editor")
    print("2. Run: REFRESH MATERIALIZED VIEW comparative_metrics;")
    print("\nOr use the Supabase CLI if installed:")
    print("supabase db execute --sql 'REFRESH MATERIALIZED VIEW comparative_metrics;'")

if success:
    # Wait a moment for refresh to complete
    import time
    print("\nWaiting for refresh to complete...")
    time.sleep(5)
    
    # Check if Rochdale is now in the view
    try:
        rochdale_check = supabase.table('comparative_metrics')\
            .select('establishment_name')\
            .ilike('establishment_name', '%rochdale%')\
            .execute()
        
        if rochdale_check.data:
            print("\n✓ SUCCESS! Rochdale Sixth Form College is now in the view!")
            print(f"  Name in view: {rochdale_check.data[0]['establishment_name']}")
        else:
            print("\n⚠ Rochdale still not in view. May need more time or manual refresh.")
            
        # Get new count
        new_result = supabase.table('comparative_metrics').select('establishment_id', count='exact').execute()
        print(f"\nNew total records in view: {new_result.count}")
        
    except Exception as e:
        print(f"Error checking results: {e}")

print("\n" + "="*60)
print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# Create SQL file for manual execution if needed
sql_content = """-- Manual refresh script for comparative_metrics
-- Run this in Supabase SQL Editor if the Python script fails

-- 1. Check current state
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT establishment_id) as unique_establishments
FROM comparative_metrics;

-- 2. Check for Rochdale
SELECT * FROM comparative_metrics 
WHERE establishment_name ILIKE '%rochdale%';

-- 3. Refresh the view (this will take 1-2 minutes)
REFRESH MATERIALIZED VIEW comparative_metrics;

-- 4. Verify Rochdale is now included
SELECT 
    establishment_name,
    COUNT(*) as records
FROM comparative_metrics 
WHERE establishment_name ILIKE '%rochdale%'
GROUP BY establishment_name;

-- 5. Get summary of all establishments
SELECT 
    establishment_name,
    COUNT(DISTINCT cycle) as cycles,
    COUNT(*) as total_records
FROM comparative_metrics
GROUP BY establishment_name
ORDER BY establishment_name;
"""

with open('manual_refresh_comparative_view.sql', 'w') as f:
    f.write(sql_content)
    print("\nCreated manual_refresh_comparative_view.sql for SQL Editor execution")
