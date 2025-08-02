#!/usr/bin/env python3
"""
Sync specific missing establishments to Supabase
"""

import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_specific_establishment(knack_id):
    """Sync a specific establishment by its Knack ID"""
    logging.info(f"Fetching establishment {knack_id} from Knack...")
    
    url = f'https://api.knack.com/v1/objects/object_2/records/{knack_id}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logging.error(f"Failed to fetch establishment: {response.status_code}")
        return False
    
    est = response.json()
    logging.info(f"Found establishment: {est}")
    
    # Map fields (matching sync_establishments logic)
    est_name = est.get('field_44') or est.get('field_44_raw') or ""
    if not est_name or est_name == "EMPTY":
        est_name = est.get('field_11') or est.get('identifier') or f"Establishment {est['id'][:8]}"
    
    establishment_data = {
        'knack_id': est['id'],
        'name': est_name,
        'status': est.get('field_2209', 'Active'),
        'is_australian': est.get('field_2300') == 'Australia',
        'created_at': est.get('field_2', '')
    }
    
    # Upsert to Supabase
    try:
        result = supabase.table('establishments').upsert(
            establishment_data,
            on_conflict='knack_id'
        ).execute()
        logging.info(f"✓ Successfully synced {est_name} to Supabase")
        return True
    except Exception as e:
        logging.error(f"Failed to sync establishment: {e}")
        return False

def fix_year14_students():
    """After syncing establishment, fix Year 14 student links"""
    logging.info("Fixing Year 14 student establishment links...")
    
    # Get the establishment ID from Supabase
    result = supabase.table('establishments').select('id').eq('knack_id', '6171c6311b379d001ecb8966').execute()
    
    if not result.data:
        logging.error("Establishment still not found in Supabase!")
        return
    
    est_id = result.data[0]['id']
    logging.info(f"Belfast Metropolitan College Supabase ID: {est_id}")
    
    # Update all Year 14 students to link to this establishment
    # This assumes Year 14 students are all from this college based on the data
    update_result = supabase.table('students').update({
        'establishment_id': est_id
    }).eq('year_group', '14').execute()
    
    logging.info(f"✓ Updated {len(update_result.data)} Year 14 students with establishment link")

if __name__ == "__main__":
    # Sync Belfast Metropolitan College
    if sync_specific_establishment('6171c6311b379d001ecb8966'):
        # Fix the student links
        fix_year14_students()
    
    logging.info("Done!")