#!/usr/bin/env python3
"""
Manually recalculate statistics with proper std_dev and distribution
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def manual_calculate_statistics():
    """Manually calculate statistics with all fields"""
    print("Manually recalculating school statistics with std_dev and distribution...")
    
    # Import the manual calculation function from sync script
    from sync_knack_to_supabase import calculate_statistics, calculate_national_statistics
    
    # Clear existing statistics
    print("Clearing existing statistics...")
    supabase.table('school_statistics').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    supabase.table('national_statistics').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    
    # Run manual calculation
    print("Calculating school statistics...")
    calculate_statistics()
    
    print("Calculating national statistics...")
    calculate_national_statistics()
    
    # Verify the results
    print("\nVerifying results...")
    
    # Check school statistics
    sample = supabase.table('school_statistics').select('*').limit(5).execute()
    print(f"\nSchool statistics sample (5 records):")
    for record in sample.data:
        dist_sum = sum(record['distribution']) if record['distribution'] else 0
        print(f"  - {record['element']}, cycle {record['cycle']}: std_dev={record['std_dev']}, distribution_sum={dist_sum}")
    
    # Check national statistics
    nat_sample = supabase.table('national_statistics').select('*').limit(5).execute()
    print(f"\nNational statistics sample (5 records):")
    for record in nat_sample.data:
        dist_sum = sum(record['distribution']) if record['distribution'] else 0
        print(f"  - {record['element']}, cycle {record['cycle']}: std_dev={record['std_dev']}, distribution_sum={dist_sum}")

if __name__ == "__main__":
    manual_calculate_statistics()