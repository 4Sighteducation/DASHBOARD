#!/usr/bin/env python3
"""
Calculate national statistics from Supabase data
This aggregates school statistics to create national benchmarks
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import statistics as stats

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_academic_year():
    """Calculate current academic year"""
    now = datetime.now()
    if now.month >= 9:  # September onwards
        return f"{now.year}/{now.year + 1}"
    else:
        return f"{now.year - 1}/{now.year}"

def calculate_national_statistics():
    """Calculate national statistics across all schools"""
    logging.info("Starting national statistics calculation...")
    
    try:
        # Get current academic year
        current_year = calculate_academic_year()
        logging.info(f"Calculating for academic year: {current_year}")
        
        # Clear existing national statistics for current year
        supabase.table('national_statistics').delete().eq('academic_year', current_year).execute()
        
        # For each cycle and element combination
        for cycle in [1, 2, 3]:
            for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                logging.info(f"Calculating national stats for Cycle {cycle}, {element}...")
                
                # Get all school statistics for this combination
                school_stats = supabase.table('school_statistics')\
                    .select('mean, count, percentile_25, percentile_50, percentile_75')\
                    .eq('cycle', cycle)\
                    .eq('element', element)\
                    .eq('academic_year', current_year)\
                    .execute()
                
                if not school_stats.data:
                    logging.warning(f"No data found for Cycle {cycle}, {element}")
                    continue
                
                # Calculate weighted national averages
                total_students = sum(s['count'] for s in school_stats.data)
                if total_students == 0:
                    continue
                
                # Weighted mean
                weighted_sum = sum(s['mean'] * s['count'] for s in school_stats.data)
                national_mean = weighted_sum / total_students
                
                # Collect all school means for percentile calculation
                school_means = [s['mean'] for s in school_stats.data]
                
                # Calculate national percentiles from school means
                if len(school_means) >= 2:
                    national_p25 = stats.quantiles(school_means, n=4)[0]
                    national_p50 = stats.median(school_means)
                    national_p75 = stats.quantiles(school_means, n=4)[2]
                    national_std = stats.stdev(school_means)
                else:
                    # If only one school, use that school's values
                    national_p25 = school_stats.data[0]['percentile_25']
                    national_p50 = school_stats.data[0]['percentile_50']
                    national_p75 = school_stats.data[0]['percentile_75']
                    national_std = 0
                
                # Create distribution array (0-10 scale)
                distribution = [0] * 11  # Initialize array for scores 0-10
                
                # Insert national statistics
                national_data = {
                    'cycle': cycle,
                    'academic_year': current_year,
                    'element': element,
                    'mean': round(national_mean, 2),
                    'std_dev': round(national_std, 2),
                    'count': total_students,
                    'percentile_25': round(national_p25, 2),
                    'percentile_50': round(national_p50, 2),
                    'percentile_75': round(national_p75, 2),
                    'distribution': distribution  # Placeholder, could be calculated if needed
                }
                
                result = supabase.table('national_statistics').insert(national_data).execute()
                logging.info(f"✓ Inserted national stats for Cycle {cycle}, {element}: mean={national_mean:.2f}, n={total_students}")
        
        # Log completion
        logging.info("National statistics calculation completed successfully!")
        
        # Update sync log
        sync_log = {
            'sync_type': 'national_stats_calculation',
            'status': 'completed',
            'started_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
            'metadata': {
                'academic_year': current_year,
                'message': 'National statistics calculated successfully'
            }
        }
        supabase.table('sync_logs').insert(sync_log).execute()
        
        return True
        
    except Exception as e:
        logging.error(f"Error calculating national statistics: {e}")
        
        # Log error
        sync_log = {
            'sync_type': 'national_stats_calculation',
            'status': 'failed',
            'started_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
            'error_message': str(e)
        }
        supabase.table('sync_logs').insert(sync_log).execute()
        
        return False

def verify_national_statistics():
    """Verify that national statistics were calculated correctly"""
    logging.info("\nVerifying national statistics...")
    
    try:
        # Get count of national statistics
        result = supabase.table('national_statistics').select('cycle, element, mean, count').execute()
        
        if not result.data:
            logging.error("No national statistics found!")
            return
        
        logging.info(f"Found {len(result.data)} national statistics entries")
        
        # Show sample
        for stat in result.data[:5]:
            logging.info(f"  Cycle {stat['cycle']}, {stat['element']}: mean={stat['mean']}, n={stat['count']}")
        
        # Check completeness (should be 18 entries: 3 cycles × 6 elements)
        expected = 18
        if len(result.data) < expected:
            logging.warning(f"Expected {expected} entries but found {len(result.data)}")
        else:
            logging.info(f"✓ All {expected} cycle/element combinations have national statistics")
            
    except Exception as e:
        logging.error(f"Error verifying national statistics: {e}")

def main():
    """Main function"""
    logging.info("=" * 60)
    logging.info("National Statistics Calculator for Supabase")
    logging.info("=" * 60)
    
    # First check if we have school statistics
    school_stats = supabase.table('school_statistics').select('count').limit(1).execute()
    if not school_stats.data:
        logging.error("No school statistics found! Run sync_knack_to_supabase.py first.")
        return
    
    # Calculate national statistics
    if calculate_national_statistics():
        # Verify the results
        verify_national_statistics()
    else:
        logging.error("National statistics calculation failed!")

if __name__ == "__main__":
    main()