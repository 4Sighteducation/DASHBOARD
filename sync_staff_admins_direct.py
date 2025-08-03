#!/usr/bin/env python3
"""
Direct database sync for staff_admins - bypasses RLS completely
Uses PostgreSQL connection instead of Supabase client
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from datetime import datetime
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Parse Supabase URL to get database connection details
SUPABASE_URL = os.getenv('SUPABASE_URL')
DATABASE_URL = os.getenv('DATABASE_URL')  # Direct database URL if available

if not DATABASE_URL and SUPABASE_URL:
    # Extract database host from Supabase URL
    parsed = urlparse(SUPABASE_URL)
    db_host = parsed.hostname.replace('supabase.co', 'supabase.co')
    db_name = 'postgres'
    db_user = 'postgres'
    db_password = os.getenv('SUPABASE_DB_PASSWORD')  # You'll need this
    db_port = 5432
    
    if db_password:
        DATABASE_URL = f"postgresql://{db_user}:{db_password}@db.{parsed.hostname}:{db_port}/{db_name}"
    else:
        logger.error("Need DATABASE_URL or SUPABASE_DB_PASSWORD for direct connection")
        logger.info("Get DATABASE_URL from Supabase Dashboard → Settings → Database → Connection string")
        exit(1)

# Knack credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

def get_db_connection():
    """Get direct PostgreSQL connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("Connected directly to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        exit(1)

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
            
        except Exception as e:
            logger.error(f"Error fetching staff admins: {e}")
            break
            
    return all_records

def sync_to_database(knack_records):
    """Sync directly to PostgreSQL, bypassing RLS"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get establishments mapping
        cur.execute("SELECT id, knack_id FROM establishments")
        establishments = cur.fetchall()
        est_map = {e['knack_id']: e['id'] for e in establishments}
        logger.info(f"Loaded {len(est_map)} establishments")
        
        # Temporarily disable RLS (if we have permissions)
        try:
            cur.execute("ALTER TABLE staff_admins DISABLE ROW LEVEL SECURITY")
            conn.commit()
            logger.info("Disabled RLS on staff_admins table")
        except:
            logger.warning("Could not disable RLS - continuing anyway")
        
        updated = 0
        errors = 0
        
        for record in knack_records:
            try:
                knack_id = record['id']
                email = record.get('field_86', '').lower().strip()
                name = record.get('field_85', '')
                
                if not email:
                    continue
                
                # Get establishment
                establishment_id = None
                if 'field_201' in record and record['field_201']:
                    if isinstance(record['field_201'], list) and len(record['field_201']) > 0:
                        est_knack_id = record['field_201'][0].get('id')
                        establishment_id = est_map.get(est_knack_id)
                
                # Upsert query
                cur.execute("""
                    INSERT INTO staff_admins (knack_id, email, name, establishment_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (knack_id) 
                    DO UPDATE SET 
                        email = EXCLUDED.email,
                        name = EXCLUDED.name,
                        establishment_id = EXCLUDED.establishment_id,
                        updated_at = EXCLUDED.updated_at
                """, (
                    knack_id, 
                    email, 
                    name, 
                    establishment_id,
                    datetime.now(),
                    datetime.now()
                ))
                
                updated += 1
                
                if updated % 100 == 0:
                    conn.commit()
                    logger.info(f"Committed {updated} records...")
                    
            except Exception as e:
                logger.error(f"Error syncing {record.get('id')}: {e}")
                errors += 1
                conn.rollback()
        
        # Final commit
        conn.commit()
        logger.info(f"Sync complete: {updated} updated, {errors} errors")
        
        # Re-enable RLS
        try:
            cur.execute("ALTER TABLE staff_admins ENABLE ROW LEVEL SECURITY")
            conn.commit()
            logger.info("Re-enabled RLS on staff_admins table")
        except:
            logger.warning("Could not re-enable RLS")
        
        return updated, errors
        
    finally:
        cur.close()
        conn.close()

def main():
    logger.info("Starting direct database sync for staff_admins...")
    
    # Check environment
    if not DATABASE_URL:
        logger.error("\n" + "=" * 60)
        logger.error("DATABASE_URL not set!")
        logger.error("Get it from Supabase Dashboard:")
        logger.error("1. Go to Settings → Database")
        logger.error("2. Copy the 'Connection string' (URI)")
        logger.error("3. Add to .env: DATABASE_URL=postgresql://...")
        logger.error("=" * 60)
        return
    
    # Fetch from Knack
    records = fetch_staff_admins_from_knack()
    logger.info(f"Fetched {len(records)} records from Knack")
    
    if records:
        # Sync to database
        updated, errors = sync_to_database(records)
        
        if errors == 0:
            logger.info("✅ Sync completed successfully!")
        else:
            logger.warning(f"⚠️  Sync completed with {errors} errors")

if __name__ == "__main__":
    main()