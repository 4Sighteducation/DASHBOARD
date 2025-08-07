"""
Simple patch to add automatic materialized view refresh to sync_knack_to_supabase.py
Run this after your regular sync to ensure the view is refreshed
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import subprocess

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def main():
    print("\n" + "="*60)
    print("POST-SYNC MATERIALIZED VIEW REFRESH")
    print("="*60)
    
    # First run the main sync
    print("\n1. Running main sync...")
    result = subprocess.run([sys.executable, "sync_knack_to_supabase.py"], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"⚠ Sync had issues: {result.stderr}")
    else:
        print("✓ Main sync completed")
    
    # Now refresh the materialized view
    print("\n2. Refreshing comparative_metrics materialized view...")
    print("   Note: The sync script's refresh function doesn't work.")
    print("   We need to do it manually via SQL.")
    
    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        # Check current state
        before = supabase.table('comparative_metrics').select('establishment_id', count='exact').execute()
        print(f"   Records before refresh: {before.count}")
    except:
        print("   Could not get count before refresh")
    
    print("\n" + "="*60)
    print("IMPORTANT: Manual step required!")
    print("="*60)
    print("\nThe materialized view MUST be refreshed manually.")
    print("\nOption 1: Run in Supabase SQL Editor:")
    print("  REFRESH MATERIALIZED VIEW comparative_metrics;")
    print("\nOption 2: Run this Python script:")
    print("  python refresh_comparative_view.py")
    print("\nOption 3: Set up the RPC function (one-time setup):")
    print("  Run create_refresh_function.sql in Supabase")
    print("\n" + "="*60)
    
    # Offer to open browser
    response = input("\nWould you like to open Supabase Dashboard now? (y/n): ")
    if response.lower() == 'y':
        import webbrowser
        # Extract project ref from URL
        if SUPABASE_URL:
            # URL format: https://xxxxx.supabase.co
            project_ref = SUPABASE_URL.split('//')[1].split('.')[0]
            dashboard_url = f"https://app.supabase.com/project/{project_ref}/sql"
            webbrowser.open(dashboard_url)
            print(f"\n✓ Opened: {dashboard_url}")
            print("\nPaste this SQL and run it:")
            print("REFRESH MATERIALIZED VIEW comparative_metrics;")

if __name__ == "__main__":
    main()
