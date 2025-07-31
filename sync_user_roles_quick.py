#!/usr/bin/env python3
"""
Quick script to sync user roles after main sync
Can be run separately without interrupting main sync
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import requests
import json
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize clients
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_knack_records(object_key, page=1):
    """Fetch records from Knack"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"https://api.knack.com/v1/objects/{object_key}/records"
    params = {'page': page, 'rows_per_page': 1000}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def sync_roles():
    """Sync staff admins and super users"""
    
    # First, ensure tables exist
    logging.info("Creating tables if needed...")
    
    # Sync Staff Admins (object_5)
    logging.info("Syncing Staff Admins from object_5...")
    page = 1
    staff_count = 0
    
    while True:
        data = fetch_knack_records('object_5', page)
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                admin_data = {
                    'knack_id': record['id'],
                    'email': record.get('field_86', ''),
                    'name': record.get('field_85', '') or record.get('field_85_raw', '')
                }
                
                if admin_data['email']:
                    supabase.table('staff_admins').upsert(admin_data, on_conflict='knack_id').execute()
                    staff_count += 1
                    
            except Exception as e:
                logging.error(f"Error syncing staff admin: {e}")
        
        page += 1
    
    logging.info(f"Synced {staff_count} staff admins")
    
    # Sync Super Users (object_21)
    logging.info("Syncing Super Users from object_21...")
    page = 1
    super_count = 0
    
    while True:
        data = fetch_knack_records('object_21', page)
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                user_data = {
                    'knack_id': record['id'],
                    'email': record.get('field_86', ''),
                    'name': record.get('field_85', '') or record.get('field_85_raw', '')
                }
                
                if user_data['email']:
                    supabase.table('super_users').upsert(user_data, on_conflict='knack_id').execute()
                    super_count += 1
                    
            except Exception as e:
                logging.error(f"Error syncing super user: {e}")
        
        page += 1
    
    logging.info(f"Synced {super_count} super users")

if __name__ == "__main__":
    # First run the SQL to create tables
    print("Make sure you've run add_super_users_table.sql in Supabase first!")
    print("Starting role sync...")
    sync_roles()
    print("Role sync complete!")