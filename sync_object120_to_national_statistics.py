#!/usr/bin/env python3
"""
Sync Object_120 national benchmarks from Knack to Supabase national_statistics table
This is the correct table that the API actually uses
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Knack configuration
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
KNACK_API_URL = f"https://api.knack.com/v1"

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def make_knack_request(object_key, filters=None, page=1, rows_per_page=100):
    """Make a request to Knack API"""
    url = f"{KNACK_API_URL}/objects/{object_key}/records"
    
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
        # Format filters for Knack API
        filter_list = []
        for f in filters:
            filter_list.append({
                'field': f['field'],
                'operator': f.get('operator', 'is'),
                'value': f['value']
            })
        params['filters'] = json.dumps({'match': 'and', 'rules': filter_list})
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def sync_object120_to_national_statistics():
    """Main sync function"""
    logging.info("Starting Object_120 sync to national_statistics table...")
    
    try:
        # Fetch Object_120 records for both academic years
        academic_years = ['2024-2025', '2025-2026']  # Object_120 format
        
        # Field mappings for Object_120
        cycle_fields = {
            1: {
                'vision': 'field_3292',  # Vision Cycle 1
                'effort': 'field_3293',  # Effort Cycle 1
                'systems': 'field_3294',  # Systems Cycle 1
                'practice': 'field_3295',  # Practice Cycle 1
                'attitude': 'field_3296',  # Attitude Cycle 1
                'overall': 'field_3297',  # Overall Cycle 1
                'resilience': 'field_3410'  # Resilience Cycle 1
            },
            2: {
                'vision': 'field_3298',  # Vision Cycle 2
                'effort': 'field_3299',  # Effort Cycle 2
                'systems': 'field_3300',  # Systems Cycle 2
                'practice': 'field_3301',  # Practice Cycle 2
                'attitude': 'field_3302',  # Attitude Cycle 2
                'overall': 'field_3303',  # Overall Cycle 2
                'resilience': 'field_3411'  # Resilience Cycle 2
            },
            3: {
                'vision': 'field_3304',  # Vision Cycle 3
                'effort': 'field_3348',  # Effort Cycle 3
                'systems': 'field_3349',  # Systems Cycle 3
                'practice': 'field_3350',  # Practice Cycle 3
                'attitude': 'field_3351',  # Attitude Cycle 3
                'overall': 'field_3352',  # Overall Cycle 3
                'resilience': 'field_3412'  # Resilience Cycle 3
            }
        }
        
        # ERI fields
        eri_fields = {
            1: 'field_3432',  # ERI Cycle 1
            2: 'field_3433',  # ERI Cycle 2
            3: 'field_3434'   # ERI Cycle 3
        }
        
        records_synced = 0
        
        for knack_year in academic_years:
            # Convert to Supabase format (2024-2025 -> 2024/2025)
            supabase_year = knack_year.replace('-', '/')
            
            logging.info(f"Fetching Object_120 for academic year: {knack_year}")
            
            # Fetch records for this academic year
            filters = [{'field': 'field_3308', 'operator': 'is', 'value': knack_year}]
            data = make_knack_request('object_120', filters=filters)
            records = data.get('records', [])
            
            if not records:
                logging.warning(f"No Object_120 records found for {knack_year}")
                continue
            
            logging.info(f"Found {len(records)} record(s) for {knack_year}")
            
            for record in records:
                # Process each cycle
                for cycle, fields in cycle_fields.items():
                    # Delete existing records for this year/cycle
                    logging.info(f"Clearing existing national_statistics for {supabase_year} cycle {cycle}")
                    supabase.table('national_statistics').delete().eq(
                        'academic_year', supabase_year
                    ).eq('cycle', cycle).execute()
                    
                    # Process VESPA components
                    for element, field_id in fields.items():
                        value = record.get(f'{field_id}_raw')
                        if value is not None and value != '':
                            try:
                                # Insert into national_statistics table
                                stat_data = {
                                    'academic_year': supabase_year,
                                    'cycle': cycle,
                                    'element': element,
                                    'mean': float(value),
                                    'std_dev': 0,  # Not available from Object_120
                                    'count': 0,  # Not available from Object_120
                                    'percentile_25': 0,
                                    'percentile_50': float(value),  # Use mean as median
                                    'percentile_75': 0,
                                    'distribution': []  # Empty distribution
                                }
                                
                                supabase.table('national_statistics').insert(stat_data).execute()
                                records_synced += 1
                                logging.info(f"Synced {element} for cycle {cycle}, year {supabase_year}: {value}")
                            except Exception as e:
                                logging.error(f"Error syncing {element}: {e}")
                    
                    # Process ERI separately
                    eri_value = record.get(f'{eri_fields[cycle]}_raw')
                    if eri_value is not None and eri_value != '':
                        try:
                            eri_data = {
                                'academic_year': supabase_year,
                                'cycle': cycle,
                                'element': 'ERI',
                                'eri_score': float(eri_value),
                                'mean': 0,  # ERI is stored in eri_score field
                                'std_dev': 0,
                                'count': 0,
                                'percentile_25': 0,
                                'percentile_50': 0,
                                'percentile_75': 0,
                                'distribution': []
                            }
                            
                            supabase.table('national_statistics').insert(eri_data).execute()
                            records_synced += 1
                            logging.info(f"Synced ERI for cycle {cycle}, year {supabase_year}: {eri_value}")
                        except Exception as e:
                            logging.error(f"Error syncing ERI: {e}")
        
        logging.info(f"Sync complete! {records_synced} records synced to national_statistics table")
        
        # Verify the sync
        logging.info("\nVerifying synced data...")
        for year in ['2024/2025', '2025/2026']:
            result = supabase.table('national_statistics').select('*').eq('academic_year', year).eq('cycle', 1).execute()
            logging.info(f"  {year}: {len(result.data)} records for cycle 1")
        
        return True
        
    except Exception as e:
        logging.error(f"Error syncing Object_120 to national_statistics: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if sync_object120_to_national_statistics():
        logging.info("✅ Sync completed successfully!")
    else:
        logging.error("❌ Sync failed!")
        sys.exit(1)
