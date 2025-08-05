#!/usr/bin/env python3
"""
Calculate National ERI from outcome questions in Supabase
This should be run after the daily sync to update national ERI statistics
"""

import os
import logging
from datetime import datetime
from supabase import create_client, Client
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'your-supabase-url')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'your-service-key')

def get_supabase_client() -> Client:
    """Create and return Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_national_eri_for_cycle(supabase: Client, cycle: int, academic_year: str = None):
    """Calculate national ERI for a specific cycle and optionally academic year"""
    
    # Query outcome question responses
    query = supabase.table('question_responses').select('response_value, student_id')
    query = query.in_('question_id', ['outcome_q_confident', 'outcome_q_equipped', 'outcome_q_support'])
    query = query.eq('cycle', cycle)
    query = query.not_.is_('response_value', 'null')
    
    if academic_year:
        query = query.eq('academic_year', academic_year)
    
    result = query.execute()
    
    if not result.data:
        logger.warning(f"No outcome responses found for cycle {cycle}, academic_year {academic_year}")
        return None
    
    # Calculate statistics
    response_values = [r['response_value'] for r in result.data]
    unique_students = len(set(r['student_id'] for r in result.data))
    
    if len(response_values) < 30:  # Minimum responses needed
        logger.warning(f"Not enough responses ({len(response_values)}) for cycle {cycle}")
        return None
    
    mean = np.mean(response_values)
    std_dev = np.std(response_values)
    percentiles = np.percentile(response_values, [25, 50, 75])
    
    return {
        'cycle': cycle,
        'academic_year': academic_year,
        'element': 'ERI',
        'mean': float(mean),
        'std_dev': float(std_dev),
        'count': unique_students,
        'percentile_25': float(percentiles[0]),
        'percentile_50': float(percentiles[1]),
        'percentile_75': float(percentiles[2]),
        'eri_score': float(mean),
        'calculated_at': datetime.utcnow().isoformat()
    }

def update_national_statistics(supabase: Client):
    """Update national statistics table with ERI calculations"""
    
    # Get distinct cycles and academic years
    cycles_result = supabase.table('question_responses')\
        .select('cycle, academic_year')\
        .in_('question_id', ['outcome_q_confident', 'outcome_q_equipped', 'outcome_q_support'])\
        .execute()
    
    if not cycles_result.data:
        logger.error("No outcome question data found")
        return
    
    # Get unique combinations
    cycle_year_combos = set()
    for row in cycles_result.data:
        if row['cycle'] and row['academic_year']:
            cycle_year_combos.add((row['cycle'], row['academic_year']))
    
    logger.info(f"Found {len(cycle_year_combos)} cycle/year combinations to process")
    
    for cycle, academic_year in cycle_year_combos:
        logger.info(f"Processing cycle {cycle}, academic year {academic_year}")
        
        # Calculate ERI statistics
        eri_stats = calculate_national_eri_for_cycle(supabase, cycle, academic_year)
        
        if not eri_stats:
            continue
        
        # Check if record exists
        existing = supabase.table('national_statistics')\
            .select('id')\
            .eq('cycle', cycle)\
            .eq('academic_year', academic_year)\
            .eq('element', 'ERI')\
            .execute()
        
        if existing.data:
            # Update existing record
            logger.info(f"Updating existing ERI record for cycle {cycle}, year {academic_year}")
            supabase.table('national_statistics')\
                .update(eri_stats)\
                .eq('id', existing.data[0]['id'])\
                .execute()
        else:
            # Insert new record
            logger.info(f"Inserting new ERI record for cycle {cycle}, year {academic_year}")
            supabase.table('national_statistics')\
                .insert(eri_stats)\
                .execute()
    
    # Also update eri_score for existing VESPA element records
    logger.info("Updating ERI scores for VESPA element records")
    
    vespa_records = supabase.table('national_statistics')\
        .select('id, cycle, academic_year')\
        .in_('element', ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall'])\
        .execute()
    
    for record in vespa_records.data:
        eri_stats = calculate_national_eri_for_cycle(
            supabase, 
            record['cycle'], 
            record['academic_year']
        )
        
        if eri_stats:
            supabase.table('national_statistics')\
                .update({'eri_score': eri_stats['eri_score']})\
                .eq('id', record['id'])\
                .execute()

def main():
    """Main function"""
    logger.info("Starting National ERI calculation")
    
    try:
        supabase = get_supabase_client()
        update_national_statistics(supabase)
        logger.info("National ERI calculation completed successfully")
        
    except Exception as e:
        logger.error(f"Error calculating national ERI: {e}")
        raise

if __name__ == "__main__":
    main()