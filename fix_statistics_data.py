#!/usr/bin/env python3
"""
Fix existing statistics data by recalculating with proper distribution and std_dev
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def recalculate_school_statistics():
    """Recalculate school statistics with proper distribution"""
    print("Recalculating school statistics...")
    
    # Clear existing statistics
    supabase.table('school_statistics').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    
    # Call the stored procedure
    try:
        result = supabase.rpc('calculate_all_statistics', {}).execute()
        print("School statistics recalculated successfully")
    except Exception as e:
        print(f"Error calling stored procedure: {e}")
        return False
    
    return True

def recalculate_national_statistics():
    """Recalculate national statistics"""
    print("Recalculating national statistics...")
    
    # Clear existing
    supabase.table('national_statistics').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    
    # Call the function from sync script
    from sync_knack_to_supabase import calculate_national_statistics
    calculate_national_statistics()
    
    print("National statistics recalculated")

def sync_super_users_now():
    """Run super users sync with fixed field mappings"""
    print("Syncing super users...")
    
    from sync_knack_to_supabase import sync_super_users
    sync_super_users()
    
    count = supabase.table('super_users').select('id', count='exact').execute()
    print(f"Super users synced: {count.count}")

def update_trust_ids():
    """Update existing establishments with trust IDs"""
    print("Updating establishment trust IDs...")
    
    from sync_knack_to_supabase import sync_establishments
    sync_establishments()
    
    # Check how many have trusts now
    all_establishments = supabase.table('establishments').select('id', 'trust_id').execute()
    trusts_count = sum(1 for e in all_establishments.data if e['trust_id'] is not None)
    print(f"Establishments with trusts: {trusts_count}")

if __name__ == "__main__":
    print("Fixing existing data issues...\n")
    
    # Fix each issue
    sync_super_users_now()
    print()
    
    update_trust_ids()
    print()
    
    recalculate_school_statistics()
    print()
    
    recalculate_national_statistics()
    print()
    
    print("All fixes completed!")