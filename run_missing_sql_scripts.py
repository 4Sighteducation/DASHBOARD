#!/usr/bin/env python3
"""
Script to run missing SQL scripts in Supabase
This will fix the database schema issues
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_sql_file(filepath, description):
    """Run a SQL file in Supabase"""
    try:
        logging.info(f"Running {description}...")
        with open(filepath, 'r') as f:
            sql_content = f.read()
        
        # Note: Supabase Python client doesn't have direct SQL execution
        # You'll need to run these in Supabase SQL Editor
        logging.info(f"Please run the following SQL in Supabase SQL Editor:")
        logging.info(f"--- START {filepath} ---")
        print(sql_content)
        logging.info(f"--- END {filepath} ---\n")
        
        return True
    except Exception as e:
        logging.error(f"Error reading {filepath}: {e}")
        return False

def check_database_state():
    """Check current state of the database"""
    logging.info("Checking current database state...")
    
    # Check row counts
    tables = ['establishments', 'students', 'vespa_scores', 'question_responses', 
              'staff_admins', 'super_users', 'school_statistics', 'question_statistics', 
              'national_statistics']
    
    for table in tables:
        try:
            result = supabase.table(table).select('id', count='exact').limit(1).execute()
            count = result.count if hasattr(result, 'count') else 'Unknown'
            logging.info(f"{table}: {count} rows")
        except Exception as e:
            logging.error(f"Error checking {table}: {e}")

def main():
    logging.info("=== Supabase Database Fix Script ===")
    
    # Check current state
    check_database_state()
    
    print("\n" + "="*60)
    print("MANUAL STEPS REQUIRED:")
    print("="*60)
    print("\n1. Go to your Supabase project SQL Editor")
    print("2. Run the following SQL scripts in order:\n")
    
    # List SQL files to run
    sql_files = [
        ("add_super_users_table.sql", "Create missing super_users table"),
        ("add_group_column.sql", "Add missing group column to students table"),
        ("create_statistics_function_fixed.sql", "Create calculate_all_statistics function"),
    ]
    
    for sql_file, description in sql_files:
        if os.path.exists(sql_file):
            run_sql_file(sql_file, description)
        else:
            logging.warning(f"File not found: {sql_file}")
    
    print("\n3. After running these SQL scripts, run the sync:")
    print("   python sync_knack_to_supabase.py")
    
    print("\n4. To verify everything worked:")
    print("   python check_sync_status.py")

if __name__ == "__main__":
    main()