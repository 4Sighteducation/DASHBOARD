#!/usr/bin/env python3
"""
Sync Object_120 to national_statistics INCLUDING distribution data
This version extracts both the statistical summaries AND the distribution histograms
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

def parse_distribution_json(dist_json_str):
    """
    Parse the distribution JSON from Knack and convert to array format for Supabase
    Input format: {"Vision": {"1": 56, "2": 185, ...}, "Effort": {...}, ...}
    Output format: {"vision": [56, 185, ...], "effort": [...], ...}
    """
    distributions = {}
    
    if not dist_json_str:
        return distributions
        
    try:
        if isinstance(dist_json_str, str):
            dist_data = json.loads(dist_json_str)
        else:
            dist_data = dist_json_str
            
        for element_name, scores in dist_data.items():
            element_lower = element_name.lower()
            
            # Convert score dict to array (scores 1-10)
            distribution_array = []
            for score in range(1, 11):
                count = scores.get(str(score), 0)
                distribution_array.append(count)
            
            distributions[element_lower] = distribution_array
            
    except Exception as e:
        logging.error(f"Error parsing distribution JSON: {e}")
    
    return distributions

def sync_with_distributions():
    """Main sync function including distribution data"""
    logging.info("Starting Object_120 sync with distribution data...")
    
    try:
        academic_years = ['2024-2025', '2025-2026']  # Object_120 format
        
        # Field mappings
        json_stat_fields = {
            1: 'field_3429',  # Cycle 1 JSON statistics
            2: 'field_3430',  # Cycle 2 JSON statistics
            3: 'field_3431'   # Cycle 3 JSON statistics
        }
        
        # Distribution histogram fields
        distribution_fields = {
            1: 'field_3409',  # Cycle 1 distribution histogram
            2: 'field_3410',  # Cycle 2 distribution histogram
            3: 'field_3411'   # Cycle 3 distribution histogram
        }
        
        # Total responses fields
        response_count_fields = {
            1: 'field_3412',  # Cycle 1 response count
            2: 'field_3413',  # Cycle 2 response count
            3: 'field_3414'   # Cycle 3 response count
        }
        
        # Basic mean fields (fallback)
        cycle_field_mappings = {
            1: {
                'vision': 'field_3292',
                'effort': 'field_3293',
                'systems': 'field_3294',
                'practice': 'field_3295',
                'attitude': 'field_3296',
                'overall': 'field_3297'
            },
            2: {
                'vision': 'field_3298',
                'effort': 'field_3299',
                'systems': 'field_3300',
                'practice': 'field_3301',
                'attitude': 'field_3302',
                'overall': 'field_3303'
            },
            3: {
                'vision': 'field_3304',
                'effort': 'field_3348',
                'systems': 'field_3349',
                'practice': 'field_3350',
                'attitude': 'field_3351',
                'overall': 'field_3352'
            }
        }
        
        # ERI fields
        eri_fields = {
            1: 'field_3432',
            2: 'field_3433',
            3: 'field_3434'
        }
        
        records_synced = 0
        
        for knack_year in academic_years:
            supabase_year = knack_year.replace('-', '/')
            
            logging.info(f"Fetching Object_120 for academic year: {knack_year}")
            
            filters = [{'field': 'field_3308', 'operator': 'is', 'value': knack_year}]
            data = make_knack_request('object_120', filters=filters)
            records = data.get('records', [])
            
            if not records:
                logging.warning(f"No Object_120 records found for {knack_year}")
                continue
            
            logging.info(f"Found {len(records)} record(s) for {knack_year}")
            
            for record in records:
                # Process each cycle
                for cycle in [1, 2, 3]:
                    # Get distribution data for this cycle
                    dist_field = distribution_fields.get(cycle)
                    dist_json_raw = record.get(f'{dist_field}_raw') if dist_field else None
                    distributions = parse_distribution_json(dist_json_raw) if dist_json_raw else {}
                    
                    # Get total response count for this cycle
                    response_field = response_count_fields.get(cycle)
                    response_raw = record.get(f'{response_field}_raw', 0) if response_field else 0
                    try:
                        total_responses = int(float(response_raw)) if response_raw else 0
                    except (ValueError, TypeError):
                        total_responses = 0
                    logging.info(f"Cycle {cycle}: Total responses = {total_responses}")
                    
                    # Get statistical summaries
                    json_field = json_stat_fields.get(cycle)
                    json_stats_raw = record.get(f'{json_field}_raw') if json_field else None
                    
                    # Delete existing records for this year/cycle
                    logging.info(f"Clearing existing national_statistics for {supabase_year} cycle {cycle}")
                    supabase.table('national_statistics').delete().eq(
                        'academic_year', supabase_year
                    ).eq('cycle', cycle).execute()
                    
                    if json_stats_raw:
                        # Use rich JSON statistics with distributions
                        try:
                            if isinstance(json_stats_raw, str):
                                json_stats = json.loads(json_stats_raw)
                            else:
                                json_stats = json_stats_raw
                            
                            for element_name, stats in json_stats.items():
                                if isinstance(stats, dict) and element_name.lower() in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                                    element_lower = element_name.lower()
                                    
                                    # Get distribution for this element
                                    element_distribution = distributions.get(element_lower, [])
                                    
                                    stat_data = {
                                        'academic_year': supabase_year,
                                        'cycle': cycle,
                                        'element': element_lower,
                                        'mean': float(stats.get('mean', 0)),
                                        'std_dev': float(stats.get('std_dev', 0)),
                                        'count': int(stats.get('count', total_responses)),  # Use total_responses if count not in stats
                                        'percentile_25': float(stats.get('percentile_25', 0)),
                                        'percentile_50': float(stats.get('percentile_50', 0)),
                                        'percentile_75': float(stats.get('percentile_75', 0)),
                                        'distribution': element_distribution  # Add the actual distribution!
                                    }
                                    
                                    supabase.table('national_statistics').insert(stat_data).execute()
                                    records_synced += 1
                                    
                                    if element_distribution:
                                        logging.info(f"Synced {element_lower} for cycle {cycle} with distribution: {sum(element_distribution)} total counts")
                                    else:
                                        logging.info(f"Synced {element_lower} for cycle {cycle} (no distribution data)")
                        
                        except Exception as e:
                            logging.error(f"Error processing stats for cycle {cycle}: {e}")
                    
                    else:
                        # Fallback to individual fields
                        fields = cycle_field_mappings.get(cycle, {})
                        for element, field_id in fields.items():
                            value = record.get(f'{field_id}_raw')
                            if value is not None and value != '':
                                # Get distribution for this element
                                element_distribution = distributions.get(element, [])
                                
                                stat_data = {
                                    'academic_year': supabase_year,
                                    'cycle': cycle,
                                    'element': element,
                                    'mean': float(value),
                                    'std_dev': 0,
                                    'count': total_responses,  # Use the total response count
                                    'percentile_25': 0,
                                    'percentile_50': float(value),
                                    'percentile_75': 0,
                                    'distribution': element_distribution
                                }
                                
                                supabase.table('national_statistics').insert(stat_data).execute()
                                records_synced += 1
                                
                                if element_distribution:
                                    logging.info(f"Synced {element} for cycle {cycle} with distribution")
                    
                    # Process ERI
                    eri_value = record.get(f'{eri_fields[cycle]}_raw')
                    if eri_value is not None and eri_value != '':
                        try:
                            eri_data = {
                                'academic_year': supabase_year,
                                'cycle': cycle,
                                'element': 'ERI',
                                'eri_score': float(eri_value),
                                'mean': 0,
                                'std_dev': 0,
                                'count': total_responses,  # Use the total response count for ERI too
                                'percentile_25': 0,
                                'percentile_50': 0,
                                'percentile_75': 0,
                                'distribution': []
                            }
                            
                            supabase.table('national_statistics').insert(eri_data).execute()
                            records_synced += 1
                            logging.info(f"Synced ERI for cycle {cycle}: {eri_value}")
                        except Exception as e:
                            logging.error(f"Error syncing ERI: {e}")
        
        logging.info(f"Sync complete! {records_synced} records synced")
        
        # Verify the sync
        logging.info("\nVerifying distribution data...")
        for year in ['2024/2025', '2025/2026']:
            result = supabase.table('national_statistics').select('element, distribution').eq('academic_year', year).eq('cycle', 1).execute()
            if result.data:
                for rec in result.data:
                    dist = rec.get('distribution', [])
                    total = sum(dist) if dist else 0
                    logging.info(f"  {year} - {rec['element']}: distribution with {total} total counts")
        
        return True
        
    except Exception as e:
        logging.error(f"Error syncing: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if sync_with_distributions():
        logging.info("✅ Distribution sync completed successfully!")
    else:
        logging.error("❌ Distribution sync failed!")
        sys.exit(1)
