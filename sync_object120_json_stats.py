#!/usr/bin/env python3
"""
Sync the detailed JSON statistics from Object_120 to Supabase national_statistics table
This extracts the rich statistical data from field_3429 (Cycle1), field_3430 (Cycle2), field_3431 (Cycle3)
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
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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

def sync_json_statistics_to_supabase():
    """Main sync function to extract JSON statistics"""
    logging.info("Starting Object_120 JSON statistics sync to national_statistics table...")
    
    try:
        # Fetch Object_120 records for both academic years
        academic_years = ['2024-2025', '2025-2026']  # Object_120 format
        
        # JSON statistics fields for each cycle
        json_stat_fields = {
            1: 'field_3429',  # Cycle 1 JSON statistics
            2: 'field_3430',  # Cycle 2 JSON statistics
            3: 'field_3431'   # Cycle 3 JSON statistics
        }
        
        # ERI fields (keeping these as before)
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
                for cycle, json_field_id in json_stat_fields.items():
                    # Get the JSON statistics for this cycle
                    json_stats_raw = record.get(f'{json_field_id}_raw')
                    
                    if json_stats_raw and json_stats_raw != '':
                        try:
                            # Parse the JSON data
                            if isinstance(json_stats_raw, str):
                                json_stats = json.loads(json_stats_raw)
                            else:
                                json_stats = json_stats_raw
                            
                            # Delete existing records for this year/cycle
                            logging.info(f"Clearing existing national_statistics for {supabase_year} cycle {cycle}")
                            supabase.table('national_statistics').delete().eq(
                                'academic_year', supabase_year
                            ).eq('cycle', cycle).execute()
                            
                            # Process each VESPA component from the JSON
                            for element, stats in json_stats.items():
                                if isinstance(stats, dict) and element.lower() in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                                    element_lower = element.lower()
                                    
                                    # Extract all available statistics
                                    stat_data = {
                                        'academic_year': supabase_year,
                                        'cycle': cycle,
                                        'element': element_lower,
                                        'mean': float(stats.get('mean', 0)),
                                        'std_dev': float(stats.get('std_dev', 0)),
                                        'count': int(stats.get('count', 0)),
                                        'percentile_25': float(stats.get('percentile_25', 0)),
                                        'percentile_50': float(stats.get('percentile_50', 0)),
                                        'percentile_75': float(stats.get('percentile_75', 0)),
                                        'min_value': float(stats.get('min', 0)),
                                        'max_value': float(stats.get('max', 0)),
                                        'confidence_interval_lower': float(stats.get('confidence_interval_lower', 0)),
                                        'confidence_interval_upper': float(stats.get('confidence_interval_upper', 0)),
                                        'skewness': float(stats.get('skewness', 0)),
                                        'distribution': []  # Would need to calculate from raw data
                                    }
                                    
                                    # Store any additional stats as JSON
                                    additional_stats = {
                                        'raw_stats': stats  # Keep the original JSON for reference
                                    }
                                    stat_data['additional_stats'] = json.dumps(additional_stats)
                                    
                                    logging.info(f"Element {element_lower}: mean={stat_data['mean']:.2f}, "
                                               f"std_dev={stat_data['std_dev']:.2f}, count={stat_data['count']}, "
                                               f"CI=[{stat_data['confidence_interval_lower']:.2f}, "
                                               f"{stat_data['confidence_interval_upper']:.2f}], "
                                               f"skewness={stat_data['skewness']:.3f}")
                                    
                                    supabase.table('national_statistics').insert(stat_data).execute()
                                    records_synced += 1
                                    logging.info(f"Synced {element_lower} for cycle {cycle}, year {supabase_year}")
                        
                        except json.JSONDecodeError as e:
                            logging.error(f"Error parsing JSON for cycle {cycle}: {e}")
                        except Exception as e:
                            logging.error(f"Error processing JSON stats for cycle {cycle}: {e}")
                    
                    # Process ERI separately (keeping existing logic)
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
            for cycle in [1, 2, 3]:
                result = supabase.table('national_statistics').select('*').eq('academic_year', year).eq('cycle', cycle).execute()
                if result.data:
                    logging.info(f"  {year} Cycle {cycle}: {len(result.data)} records")
                    # Show sample of the data quality
                    for rec in result.data[:2]:  # Show first 2 records
                        logging.info(f"    - {rec['element']}: mean={rec['mean']}, std_dev={rec['std_dev']}, "
                                   f"count={rec['count']}, percentiles=[{rec['percentile_25']}, "
                                   f"{rec['percentile_50']}, {rec['percentile_75']}]")
        
        return True
        
    except Exception as e:
        logging.error(f"Error syncing Object_120 JSON statistics to national_statistics: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if sync_json_statistics_to_supabase():
        logging.info("✅ JSON statistics sync completed successfully!")
    else:
        logging.error("❌ JSON statistics sync failed!")
        sys.exit(1)
