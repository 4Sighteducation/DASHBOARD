#!/usr/bin/env python3
"""
Diagnose why establishment mappings aren't working
"""

import os
import logging
from supabase import create_client, Client
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def diagnose():
    # 1. Get all establishments from Supabase
    logger.info("Fetching establishments from Supabase...")
    establishments = supabase.table('establishments').select('id, knack_id, name').execute()
    
    logger.info(f"Found {len(establishments.data)} establishments in Supabase")
    
    # Create a set of all knack_ids
    supabase_knack_ids = {est['knack_id'] for est in establishments.data}
    
    # Show sample
    logger.info("\nSample establishments in Supabase:")
    for est in establishments.data[:5]:
        logger.info(f"  {est['name']}: knack_id = {est['knack_id']}")
    
    # 2. Fetch a few staff admins from Knack to see field_201 format
    logger.info("\n" + "="*60)
    logger.info("Fetching sample staff admins from Knack...")
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-KEY': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = "https://api.knack.com/v1/objects/object_5/records?page=1&rows_per_page=10"
    response = requests.get(url, headers=headers)
    data = response.json()
    
    logger.info(f"Fetched {len(data['records'])} staff admin records")
    
    # 3. Analyze field_201 format
    logger.info("\nAnalyzing field_201 (establishment connection) format:")
    
    missing_count = 0
    found_count = 0
    
    for record in data['records']:
        email = record.get('field_86', 'No email')
        logger.info(f"\n--- Staff Admin: {email} ---")
        
        # Check all possible field formats
        field_201 = record.get('field_201')
        field_201_raw = record.get('field_201_raw')
        
        logger.info(f"  field_201: {field_201}")
        logger.info(f"  field_201_raw: {field_201_raw}")
        
        # Try to extract establishment ID
        establishment_knack_id = None
        
        if field_201:
            if isinstance(field_201, list) and len(field_201) > 0:
                establishment_knack_id = field_201[0].get('id')
                logger.info(f"  Extracted from field_201 list: {establishment_knack_id}")
                logger.info(f"  Full field_201[0]: {field_201[0]}")
        
        if field_201_raw:
            if isinstance(field_201_raw, list) and len(field_201_raw) > 0:
                raw_id = field_201_raw[0].get('id')
                logger.info(f"  Extracted from field_201_raw list: {raw_id}")
                if not establishment_knack_id:
                    establishment_knack_id = raw_id
        
        # Check if this ID exists in Supabase
        if establishment_knack_id:
            if establishment_knack_id in supabase_knack_ids:
                logger.info(f"  ✅ FOUND in Supabase establishments!")
                found_count += 1
            else:
                logger.info(f"  ❌ NOT FOUND in Supabase establishments!")
                missing_count += 1
        else:
            logger.info(f"  ⚠️  No establishment connection found")
    
    # 4. Summary
    logger.info("\n" + "="*60)
    logger.info("DIAGNOSIS SUMMARY:")
    logger.info(f"  - Establishments in Supabase: {len(establishments.data)}")
    logger.info(f"  - Staff admins checked: {len(data['records'])}")
    logger.info(f"  - Found mappings: {found_count}")
    logger.info(f"  - Missing mappings: {missing_count}")
    
    # 5. Show all field names in a staff admin record
    if data['records']:
        logger.info("\nAll fields in first staff admin record:")
        first_record = data['records'][0]
        for key, value in first_record.items():
            if 'field_' in key:
                logger.info(f"  {key}: {str(value)[:100]}...")

if __name__ == "__main__":
    diagnose()