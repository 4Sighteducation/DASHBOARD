"""
Special sync script to force-sync Rochdale College regardless of filters
This is for testing purposes to confirm Rochdale's data exists in Knack
"""
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
KNACK_API_URL = f"https://api.knack.com/v1/objects"

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Knack object keys (same as main sync)
OBJECT_KEYS = {
    'establishments': 'object_3',
    'students': 'object_7',
    'vespa_scores': 'object_6',
    'question_responses': 'object_5'
}

def make_knack_request(object_key, page=1, rows_per_page=1000, filters=None):
    """Make API request to Knack"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-KEY': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    params = {
        'page': page,
        'rows_per_page': rows_per_page
    }
    
    if filters:
        params['filters'] = json.dumps(filters)
    
    response = requests.get(f"{KNACK_API_URL}/{object_key}/records", 
                          headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def find_rochdale_in_knack():
    """Search for Rochdale College in Knack without any filters"""
    logging.info("Searching for Rochdale College in Knack (NO FILTERS)...")
    
    page = 1
    found_rochdale = []
    
    while True:
        try:
            # Get ALL establishments without filters
            data = make_knack_request(OBJECT_KEYS['establishments'], page=page)
            
            if not data.get('records'):
                break
                
            # Search for Rochdale in the results
            for est in data['records']:
                # Check various name fields
                name_fields = ['field_44', 'field_44_raw', 'field_142', 'field_142_raw']
                for field in name_fields:
                    name = est.get(field, '')
                    if name and 'rochdale' in str(name).lower():
                        logging.info(f"FOUND: {name}")
                        logging.info(f"  ID: {est.get('id')}")
                        logging.info(f"  Status: {est.get('field_2209', 'Unknown')}")
                        logging.info(f"  Portal Type: {est.get('field_63', 'Unknown')}")
                        logging.info(f"  Trust: {est.get('field_180', 'Unknown')}")
                        found_rochdale.append(est)
                        break
            
            # Check if more pages
            if data['current_page'] >= data['total_pages']:
                break
                
            page += 1
            
        except Exception as e:
            logging.error(f"Error fetching page {page}: {e}")
            break
    
    if found_rochdale:
        logging.info(f"\n✓ Found {len(found_rochdale)} Rochdale establishment(s) in Knack")
        return found_rochdale
    else:
        logging.warning("\n✗ Rochdale College NOT found in Knack!")
        logging.info("This means either:")
        logging.info("  1. It's named differently")
        logging.info("  2. It doesn't exist in Knack")
        return None

def sync_rochdale_to_supabase(rochdale_data):
    """Force sync Rochdale to Supabase regardless of status"""
    logging.info("\nForce-syncing Rochdale to Supabase...")
    
    for est in rochdale_data:
        try:
            # Prepare establishment data
            est_name = est.get('field_44') or est.get('field_44_raw') or "Rochdale College"
            
            establishment = {
                'id': est['id'],
                'name': est_name,
                'trust_name': est.get('field_180') or est.get('field_180_raw'),
                'created_at': est.get('field_156') or datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Upsert to Supabase
            result = supabase.table('establishments').upsert(establishment).execute()
            logging.info(f"✓ Synced {est_name} to Supabase")
            
            # Now sync students for this establishment
            sync_rochdale_students(est['id'])
            
        except Exception as e:
            logging.error(f"Failed to sync establishment: {e}")

def sync_rochdale_students(establishment_knack_id):
    """Sync students for Rochdale"""
    logging.info(f"Syncing students for establishment {establishment_knack_id}...")
    
    # Filter for students of this establishment
    filters = [{
        'field': 'field_46',  # establishment field in students
        'operator': 'is',
        'value': establishment_knack_id
    }]
    
    page = 1
    total_students = 0
    
    while True:
        try:
            data = make_knack_request(OBJECT_KEYS['students'], page=page, filters=filters)
            
            if not data.get('records'):
                break
                
            for student in data['records']:
                # Map and sync student
                student_data = {
                    'id': student['id'],
                    'establishment_id': establishment_knack_id,
                    'year_group': student.get('field_55'),
                    'faculty': student.get('field_56'),
                    'group': student.get('field_57'),
                    'created_at': student.get('field_163') or datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                supabase.table('students').upsert(student_data).execute()
                total_students += 1
            
            if data['current_page'] >= data['total_pages']:
                break
                
            page += 1
            
        except Exception as e:
            logging.error(f"Error syncing students: {e}")
            break
    
    logging.info(f"✓ Synced {total_students} students")

def main():
    logging.info("="*60)
    logging.info("ROCHDALE COLLEGE FORCE SYNC")
    logging.info("="*60)
    
    # Step 1: Find Rochdale in Knack
    rochdale = find_rochdale_in_knack()
    
    if rochdale:
        # Step 2: Force sync to Supabase
        sync_rochdale_to_supabase(rochdale)
        
        # Step 3: Refresh materialized view
        logging.info("\nRefreshing materialized view...")
        try:
            supabase.rpc('refresh_materialized_view', {'view_name': 'comparative_metrics'}).execute()
            logging.info("✓ View refresh initiated")
        except Exception as e:
            logging.warning(f"Could not refresh view via RPC: {e}")
            logging.info("Run this in Supabase SQL Editor:")
            logging.info("REFRESH MATERIALIZED VIEW comparative_metrics;")
        
        logging.info("\n" + "="*60)
        logging.info("SYNC COMPLETE")
        logging.info("="*60)
        logging.info("Rochdale should now be available for comparative reports!")
        
    else:
        logging.info("\n" + "="*60)
        logging.info("ROCHDALE NOT FOUND IN KNACK")
        logging.info("="*60)
        logging.info("Check the exact name in Knack manually")

if __name__ == "__main__":
    main()
