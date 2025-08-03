#!/usr/bin/env python3
"""
Fixed sync script for staff_admins - uses correct field_110 for establishment connection
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

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([KNACK_APP_ID, KNACK_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    logger.error("Missing required environment variables")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger.info("Initialized Supabase client")

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
    with_establishment = 0
    without_establishment = 0
    
    for record in knack_records:
        try:
            # Extract relevant fields
            knack_id = record['id']
            email = record.get('field_86', '')  # Email field
            name = record.get('field_85', '')   # Name field
            
            if not email:
                logger.warning(f"Skipping record {knack_id} - no email")
                continue
            
            # FIXED: Get establishment connection from field_110
            establishment_knack_id = None
            establishment_id = None
            
            # Check field_110_raw for establishment connection
            if 'field_110_raw' in record and record['field_110_raw']:
                if isinstance(record['field_110_raw'], list) and len(record['field_110_raw']) > 0:
                    establishment_knack_id = record['field_110_raw'][0].get('id')
                    establishment_name = record['field_110_raw'][0].get('identifier', 'Unknown')
                    logger.debug(f"Found establishment connection: {establishment_name} ({establishment_knack_id})")
            
            # Also check field_110 as fallback
            if not establishment_knack_id and 'field_110' in record and record['field_110']:
                if isinstance(record['field_110'], list) and len(record['field_110']) > 0:
                    establishment_knack_id = record['field_110'][0].get('id')
            
            # Map to Supabase establishment ID
            if establishment_knack_id and establishment_knack_id in est_map:
                establishment_id = est_map[establishment_knack_id]
                with_establishment += 1
            else:
                without_establishment += 1
                if establishment_knack_id:
                    logger.warning(f"No mapping found for establishment {establishment_knack_id} (staff: {email})")
                else:
                    logger.debug(f"No establishment connection for staff admin {email}")
            
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
                action = "Updated"
            else:
                # Insert new record
                staff_admin_data['created_at'] = datetime.now().isoformat()
                result = supabase.table('staff_admins').insert(staff_admin_data).execute()
                action = "Inserted"
            
            if result.data:
                logger.info(f"{action} staff admin: {email} -> Establishment: {'✓' if establishment_id else '✗'}")
                updated_count += 1
            else:
                logger.error(f"No data returned for {email}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Error processing staff admin {record.get('id')}: {e}")
            error_count += 1
    
    logger.info(f"\nProcessing Summary:")
    logger.info(f"  - With establishment: {with_establishment}")
    logger.info(f"  - Without establishment: {without_establishment}")
    
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
        
        if without_establishment > 0 and without_establishment < 20:  # Only show if reasonable number
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
    logger.info("Using field_110 for establishment connections")
    logger.info("=" * 60)
    
    # Test authentication first
    try:
        test_result = supabase.table('staff_admins').select('count', count='exact').limit(1).execute()
        logger.info("✅ Authentication successful")
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
    logger.info(f"\nResults: {updated} updated, {errors} errors")
    
    # Verify results
    logger.info("\nVerifying staff admin establishments...")
    total, with_est, without_est = verify_staff_admin_establishments()
    
    percentage = (with_est / total * 100) if total > 0 else 0
    
    logger.info("\n" + "=" * 60)
    if percentage >= 90:
        logger.info(f"✅ SUCCESS! {percentage:.1f}% of staff admins have establishments assigned!")
    elif percentage >= 70:
        logger.info(f"⚠️  PARTIAL SUCCESS: {percentage:.1f}% of staff admins have establishments assigned")
    else:
        logger.warning(f"❌ NEEDS ATTENTION: Only {percentage:.1f}% of staff admins have establishments assigned")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()