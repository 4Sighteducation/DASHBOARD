#!/usr/bin/env python3
"""
Working sync script for staff_admins - uses the correct SUPABASE_KEY
"""

import os
import sys
from datetime import datetime
import logging
from supabase import create_client, Client
import requests
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

# Supabase credentials - USE THE WORKING KEY!
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')  # This is already a service role key!

if not all([KNACK_APP_ID, KNACK_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    logger.error("Missing required environment variables")
    sys.exit(1)

# Initialize Supabase client with the working key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger.info(f"Initialized Supabase client with key length: {len(SUPABASE_KEY)}")

def fetch_staff_admins_from_knack():
    """Fetch all staff admin records from Knack Object_5"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-KEY': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    all_records = []
    page = 1
    
    while True:
        url = f"https://api.knack.com/v1/objects/object_5/records?page={page}&rows_per_page=1000"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if not data['records']:
                break
                
            all_records.extend(data['records'])
            logger.info(f"Fetched page {page} with {len(data['records'])} staff admin records")
            
            page += 1
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error fetching staff admins: {e}")
            break
            
    return all_records

def update_staff_admins_in_supabase(knack_records):
    """Update staff_admins table with establishment relationships"""
    
    # First, get all establishments for mapping
    try:
        establishments = supabase.table('establishments').select('id, knack_id').execute()
        est_map = {est['knack_id']: est['id'] for est in establishments.data}
        logger.info(f"Loaded {len(est_map)} establishments for mapping")
    except Exception as e:
        logger.error(f"Failed to fetch establishments: {e}")
        return 0, 0
    
    updated_count = 0
    error_count = 0
    
    for record in knack_records:
        try:
            # Extract relevant fields
            knack_id = record['id']
            email = record.get('field_86', '')  # Email field
            name = record.get('field_85', '')   # Name field
            
            if not email:
                logger.warning(f"Skipping record {knack_id} - no email")
                continue
            
            # CRITICAL: Get establishment connection
            # field_201 is the connection to establishments (Object_2)
            establishment_knack_id = None
            establishment_id = None
            
            # Check multiple possible field formats
            if 'field_201' in record and record['field_201']:
                if isinstance(record['field_201'], list) and len(record['field_201']) > 0:
                    establishment_knack_id = record['field_201'][0].get('id')
                elif isinstance(record['field_201'], dict):
                    establishment_knack_id = record['field_201'].get('id')
                elif isinstance(record['field_201'], str):
                    establishment_knack_id = record['field_201']
            
            # Also check _raw field
            if not establishment_knack_id and 'field_201_raw' in record and record['field_201_raw']:
                if isinstance(record['field_201_raw'], list) and len(record['field_201_raw']) > 0:
                    establishment_knack_id = record['field_201_raw'][0].get('id')
            
            # Map to Supabase establishment ID
            if establishment_knack_id and establishment_knack_id in est_map:
                establishment_id = est_map[establishment_knack_id]
                logger.debug(f"Mapped establishment {establishment_knack_id} to {establishment_id}")
            else:
                logger.warning(f"No establishment mapping found for staff admin {email}")
            
            # Check if staff admin exists
            existing = supabase.table('staff_admins').select('id').eq('knack_id', knack_id).execute()
            
            staff_admin_data = {
                'knack_id': knack_id,
                'email': email.lower().strip(),  # Normalize email
                'name': name,
                'establishment_id': establishment_id,
                'updated_at': datetime.now().isoformat()
            }
            
            if existing.data:
                # Update existing record
                result = supabase.table('staff_admins').update(staff_admin_data).eq('knack_id', knack_id).execute()
                logger.info(f"Updated staff admin: {email} -> Establishment: {establishment_id}")
            else:
                # Insert new record
                staff_admin_data['created_at'] = datetime.now().isoformat()
                result = supabase.table('staff_admins').insert(staff_admin_data).execute()
                logger.info(f"Inserted staff admin: {email} -> Establishment: {establishment_id}")
            
            if result.data:
                updated_count += 1
            else:
                logger.error(f"No data returned for {email}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Error processing staff admin {record.get('id')}: {e}")
            error_count += 1
            
    return updated_count, error_count

def verify_staff_admin_establishments():
    """Verify that all staff admins have establishments assigned"""
    
    try:
        # Get all staff admins
        staff_admins = supabase.table('staff_admins').select('email, establishment_id').execute()
        
        if not staff_admins.data:
            logger.warning("No staff admins found in Supabase")
            return 0, 0, 0
        
        total = len(staff_admins.data)
        with_establishment = sum(1 for sa in staff_admins.data if sa['establishment_id'])
        without_establishment = total - with_establishment
        
        logger.info(f"\nStaff Admin Establishment Status:")
        logger.info(f"Total staff admins: {total}")
        logger.info(f"With establishment: {with_establishment}")
        logger.info(f"Without establishment: {without_establishment}")
        
        if without_establishment > 0:
            logger.warning(f"\nStaff admins without establishments:")
            for sa in staff_admins.data:
                if not sa['establishment_id']:
                    logger.warning(f"  - {sa['email']}")
        
        return total, with_establishment, without_establishment
        
    except Exception as e:
        logger.error(f"Error verifying staff admins: {e}")
        return 0, 0, 0

def main():
    """Main function to update staff admin establishments"""
    
    logger.info("=" * 60)
    logger.info("Starting staff admin establishment update...")
    logger.info("Using existing SUPABASE_KEY (which is a service role key)")
    logger.info("=" * 60)
    
    # Test authentication first
    try:
        test_result = supabase.table('staff_admins').select('count', count='exact').limit(1).execute()
        logger.info("✅ Authentication successful - can access staff_admins table")
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        return
    
    # Fetch from Knack
    logger.info("\nFetching staff admins from Knack...")
    knack_records = fetch_staff_admins_from_knack()
    logger.info(f"Fetched {len(knack_records)} staff admin records from Knack")
    
    if not knack_records:
        logger.error("No records fetched from Knack. Exiting.")
        return
    
    # Update in Supabase
    logger.info("\nUpdating staff admins in Supabase...")
    updated, errors = update_staff_admins_in_supabase(knack_records)
    logger.info(f"Updated: {updated}, Errors: {errors}")
    
    # Verify results
    logger.info("\nVerifying staff admin establishments...")
    total, with_est, without_est = verify_staff_admin_establishments()
    
    if without_est == 0 and total > 0:
        logger.info("\n✅ All staff admins have establishments assigned!")
    elif total == 0:
        logger.error("\n❌ No staff admins found in Supabase")
    else:
        logger.warning(f"\n⚠️  {without_est} staff admins still need establishment assignments")
    
    logger.info("\n" + "=" * 60)
    logger.info("Update complete!")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()