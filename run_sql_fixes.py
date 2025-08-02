#!/usr/bin/env python3
"""
Run SQL fixes through Supabase
"""

import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_sql_file(filename):
    """Read and execute SQL from file"""
    logging.info(f"Reading SQL from {filename}")
    
    try:
        with open(filename, 'r') as f:
            sql_content = f.read()
        
        # Split by semicolons but be careful with functions
        # For now, let's execute the whole thing as one statement
        # Note: Supabase's RPC doesn't support running arbitrary SQL, 
        # so we need to use the SQL editor in Supabase dashboard
        
        logging.info("SQL content loaded. Unfortunately, Supabase Python client doesn't support running arbitrary SQL.")
        logging.info("Please run the following SQL in your Supabase SQL Editor:")
        logging.info("https://app.supabase.com/project/qcdcdzfanrlvdcagmwmg/editor")
        logging.info("\n" + "="*60)
        print(sql_content)
        logging.info("="*60 + "\n")
        
        return False
        
    except Exception as e:
        logging.error(f"Error reading SQL file: {e}")
        return False

def test_fixes():
    """Test if the fixes worked"""
    logging.info("\nTesting if fixes are applied...")
    
    # Test 1: Try calculate_all_statistics
    try:
        result = supabase.rpc('calculate_all_statistics', {}).execute()
        logging.info("✓ calculate_all_statistics is now working!")
    except Exception as e:
        logging.error(f"✗ calculate_all_statistics still failing: {e}")
    
    # Test 2: Try get_qla_top_bottom_questions
    try:
        # Get an establishment ID
        est = supabase.table('establishments').select('id').limit(1).execute()
        if est.data:
            result = supabase.rpc('get_qla_top_bottom_questions', {
                'p_establishment_id': est.data[0]['id'],
                'p_cycle': 1
            }).execute()
            logging.info("✓ get_qla_top_bottom_questions is now working!")
            if result.data:
                logging.info(f"  Found {len(result.data)} top/bottom questions")
    except Exception as e:
        logging.error(f"✗ get_qla_top_bottom_questions still failing: {e}")

def main():
    logging.info("SQL Fix Runner")
    logging.info("="*60)
    
    # Show the SQL that needs to be run
    run_sql_file('fix_statistics_procedures.sql')
    
    # Offer to test
    response = input("\nHave you run the SQL in Supabase? (y/n): ")
    if response.lower() == 'y':
        test_fixes()

if __name__ == "__main__":
    main()