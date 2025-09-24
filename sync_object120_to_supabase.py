#!/usr/bin/env python3
"""
Sync Object_120 national benchmarks from Knack to Supabase
This ensures national averages are available for each academic year
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
        'rows_per_page': rows_per_page,
        'sort_field': 'field_3307',  # DateTime field
        'sort_order': 'desc'
    }
    
    if filters:
        params['filters'] = json.dumps(filters)
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def parse_academic_year_from_name(name):
    """Extract academic year from record name"""
    if not name:
        return None
    
    # Look for patterns like "2024-25", "2024/2025", "2024"
    import re
    
    # Try to match 2024/2025 format
    match = re.search(r'(\d{4})/(\d{4})', name)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    
    # Try to match 2024-25 format
    match = re.search(r'(\d{4})-(\d{2})', name)
    if match:
        year1 = match.group(1)
        year2_short = match.group(2)
        year2 = f"20{year2_short}" if int(year2_short) < 50 else f"19{year2_short}"
        return f"{year1}/{year2}"
    
    # Try to match just a year and infer the academic year
    match = re.search(r'(\d{4})', name)
    if match:
        year = int(match.group(1))
        # Assume it's for the academic year starting in August of that year
        return f"{year}/{year + 1}"
    
    return None

def sync_object120_to_supabase():
    """Main sync function"""
    logging.info("Starting Object_120 sync to Supabase...")
    
    try:
        # Fetch all Object_120 records
        logging.info("Fetching Object_120 records from Knack...")
        data = make_knack_request('object_120', rows_per_page=100)
        records = data.get('records', [])
        
        logging.info(f"Found {len(records)} Object_120 records")
        
        # Field mappings for cycles and components
        cycle_fields = {
            1: {
                'vision': 'field_3309',
                'effort': 'field_3310',
                'systems': 'field_3311',
                'practice': 'field_3312',
                'attitude': 'field_3313',
                'overall': 'field_3314',
                'resilience': 'field_3488'  # If exists
            },
            2: {
                'vision': 'field_3315',
                'effort': 'field_3316',
                'systems': 'field_3317',
                'practice': 'field_3318',
                'attitude': 'field_3319',
                'overall': 'field_3320',
                'resilience': 'field_3489'  # If exists
            },
            3: {
                'vision': 'field_3321',
                'effort': 'field_3322',
                'systems': 'field_3323',
                'practice': 'field_3324',
                'attitude': 'field_3325',
                'overall': 'field_3326',
                'resilience': 'field_3490'  # If exists
            }
        }
        
        # ERI fields
        eri_fields = {
            1: 'field_3432',
            2: 'field_3433',
            3: 'field_3434'
        }
        
        records_synced = 0
        
        for record in records:
            # Extract academic year
            academic_year = record.get('field_3497_raw')  # Direct academic year field if exists
            
            if not academic_year:
                # Try to parse from name
                name = record.get('field_3306_raw', '')
                academic_year = parse_academic_year_from_name(name)
                
                if not academic_year:
                    # Try to parse from date
                    date_str = record.get('field_3307_raw')
                    if date_str:
                        try:
                            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            # Academic year runs Aug-Jul (UK) or Jan-Dec (AU)
                            if date_obj.month >= 8:
                                academic_year = f"{date_obj.year}/{date_obj.year + 1}"
                            else:
                                academic_year = f"{date_obj.year - 1}/{date_obj.year}"
                        except:
                            pass
            
            if not academic_year:
                logging.warning(f"Could not determine academic year for record: {record.get('id')} - {record.get('field_3306_raw')}")
                continue
            
            logging.info(f"Processing record for academic year: {academic_year}")
            
            # Process each cycle
            for cycle, fields in cycle_fields.items():
                # Process VESPA components
                for component, field_id in fields.items():
                    if component == 'overall':
                        continue  # Skip overall for element-based table
                    
                    value = record.get(f'{field_id}_raw')
                    if value is not None and value != '':
                        try:
                            # Check if record exists
                            existing = supabase.table('national_benchmarks').select('id').eq(
                                'academic_year', academic_year
                            ).eq('cycle', cycle).eq('vespa_component', component).execute()
                            
                            benchmark_data = {
                                'academic_year': academic_year,
                                'cycle': cycle,
                                'vespa_component': component,
                                'mean_score': float(value),
                                'source': 'object_120',
                                'last_calculated': record.get('field_3307_raw', datetime.now().isoformat())
                            }
                            
                            if existing.data:
                                # Update existing
                                supabase.table('national_benchmarks').update(
                                    benchmark_data
                                ).eq('id', existing.data[0]['id']).execute()
                                logging.info(f"Updated {component} for cycle {cycle}, year {academic_year}: {value}")
                            else:
                                # Insert new
                                supabase.table('national_benchmarks').insert(benchmark_data).execute()
                                logging.info(f"Inserted {component} for cycle {cycle}, year {academic_year}: {value}")
                            
                            records_synced += 1
                        except Exception as e:
                            logging.error(f"Error syncing {component} cycle {cycle}: {e}")
                
                # Process ERI if available
                if cycle in eri_fields:
                    eri_value = record.get(f'{eri_fields[cycle]}_raw')
                    if eri_value is not None and eri_value != '':
                        try:
                            # For backward compatibility, also update national_statistics table
                            existing_stat = supabase.table('national_statistics').select('id').eq(
                                'academic_year', academic_year
                            ).eq('cycle', cycle).eq('element', 'ERI').execute()
                            
                            eri_data = {
                                'academic_year': academic_year,
                                'cycle': cycle,
                                'element': 'ERI',
                                'mean': float(eri_value),
                                'eri_score': float(eri_value),
                                'source': 'object_120'
                            }
                            
                            if existing_stat.data:
                                supabase.table('national_statistics').update(
                                    eri_data
                                ).eq('id', existing_stat.data[0]['id']).execute()
                            else:
                                supabase.table('national_statistics').insert(eri_data).execute()
                            
                            logging.info(f"Synced ERI for cycle {cycle}, year {academic_year}: {eri_value}")
                        except Exception as e:
                            logging.error(f"Error syncing ERI cycle {cycle}: {e}")
        
        logging.info(f"Sync complete! Synced {records_synced} benchmark values")
        
        # Verify what we have in the database now
        verify_synced_data()
        
    except Exception as e:
        logging.error(f"Error during sync: {e}")
        raise

def verify_synced_data():
    """Verify what academic years have data in Supabase"""
    logging.info("\nVerifying synced data...")
    
    try:
        # Check national_benchmarks table
        result = supabase.table('national_benchmarks').select(
            'academic_year, cycle, count(*)'
        ).execute()
        
        # Group by academic year and cycle
        from collections import defaultdict
        year_cycle_counts = defaultdict(lambda: defaultdict(int))
        
        for item in result.data:
            year = item['academic_year']
            cycle = item['cycle']
            year_cycle_counts[year][cycle] += 1
        
        logging.info("\nNational Benchmarks Summary:")
        for year in sorted(year_cycle_counts.keys()):
            for cycle in sorted(year_cycle_counts[year].keys()):
                count = year_cycle_counts[year][cycle]
                logging.info(f"  {year} Cycle {cycle}: {count} components")
        
    except Exception as e:
        logging.error(f"Error verifying data: {e}")

def main():
    """Main entry point"""
    if not all([KNACK_APP_ID, KNACK_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        logging.error("Missing required environment variables. Please check your .env file.")
        sys.exit(1)
    
    sync_object120_to_supabase()

if __name__ == "__main__":
    main()
