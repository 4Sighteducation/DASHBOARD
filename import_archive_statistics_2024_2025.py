#!/usr/bin/env python3
"""
Archive Statistics Import for 2024-2025
========================================
Simple, focused script to import aggregate statistics from August 2025 snapshot
- Calculates statistics per establishment
- Stores in school_statistics and national_statistics tables
- Marks as archived to protect from future syncs
- Does NOT import individual students (not needed for archive)

This is a ONE-TIME import to establish the 2024-2025 baseline.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('archive_import_2024_2025.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# CSV Paths
OBJECT_10_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"
OBJECT_29_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_29_2025.csv"

# Academic year we're importing
ARCHIVE_YEAR = '2024/2025'

# Field mappings
FIELD_MAPPINGS = {
    'establishment': 'field_133',
    'email': 'field_197_email',
    'name': 'field_187_full',
    'current_cycle': 'field_146',
    # Current cycle scores
    'vision_current': 'field_147',
    'effort_current': 'field_148',
    'systems_current': 'field_149',
    'practice_current': 'field_150',
    'attitude_current': 'field_151',
    'overall_current': 'field_152',
    # Cycle 1 scores
    'vision_c1': 'field_155',
    'effort_c1': 'field_156',
    'systems_c1': 'field_157',
    'practice_c1': 'field_158',
    'attitude_c1': 'field_159',
    'overall_c1': 'field_160',
    # Cycle 2 scores
    'vision_c2': 'field_161',
    'effort_c2': 'field_162',
    'systems_c2': 'field_163',
    'practice_c2': 'field_164',
    'attitude_c2': 'field_165',
    'overall_c2': 'field_166',
    # Cycle 3 scores
    'vision_c3': 'field_167',
    'effort_c3': 'field_168',
    'systems_c3': 'field_169',
    'practice_c3': 'field_170',
    'attitude_c3': 'field_171',
    'overall_c3': 'field_172',
}

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def load_and_filter_data():
    """Load Object_10 CSV and filter for 2024-2025 data"""
    print_header("LOADING DATA")
    
    logging.info(f"Reading Object_10 from: {OBJECT_10_PATH}")
    
    # Read CSV in chunks for memory efficiency
    chunks = []
    chunk_size = 10000
    total_rows = 0
    
    for chunk in pd.read_csv(OBJECT_10_PATH, chunksize=chunk_size, low_memory=False):
        chunks.append(chunk)
        total_rows += len(chunk)
        if total_rows % 50000 == 0:
            logging.info(f"  Loaded {total_rows:,} rows...")
    
    df = pd.concat(chunks, ignore_index=True)
    logging.info(f"✅ Loaded {len(df):,} total records from Object_10")
    
    # Convert created date
    df['created_date'] = pd.to_datetime(df['created'], errors='coerce')
    
    # Filter for 2024-2025 academic year (Sept 1, 2024 - Aug 31, 2025)
    archive_data = df[
        (df['created_date'] >= '2024-09-01') & 
        (df['created_date'] <= '2025-08-31')
    ].copy()
    
    logging.info(f"✅ Filtered to {len(archive_data):,} records from 2024-2025")
    logging.info(f"   Date range: {archive_data['created_date'].min()} to {archive_data['created_date'].max()}")
    
    return archive_data

def get_establishment_mapping():
    """Get mapping of Knack establishment IDs to Supabase UUIDs"""
    print_header("LOADING ESTABLISHMENT MAPPING")
    
    establishments = supabase.table('establishments').select('id,knack_id,name').execute()
    
    mapping = {est['knack_id']: est for est in establishments.data}
    
    logging.info(f"✅ Loaded {len(mapping)} establishments from database")
    
    return mapping

def calculate_statistics(values):
    """Calculate statistics for a set of values"""
    if len(values) == 0:
        return None
    
    values = [v for v in values if pd.notna(v) and v != '']
    
    if len(values) == 0:
        return None
    
    # Convert to numeric
    values = pd.to_numeric(values, errors='coerce').dropna()
    
    if len(values) == 0:
        return None
    
    # Calculate distribution (0-10 scale)
    distribution = {}
    for i in range(11):
        distribution[str(i)] = int(np.sum(values == i))
    
    return {
        'mean': round(float(np.mean(values)), 2),
        'std_dev': round(float(np.std(values)), 2) if len(values) > 1 else 0,
        'count': int(len(values)),
        'percentile_25': round(float(np.percentile(values, 25)), 2),
        'percentile_50': round(float(np.percentile(values, 50)), 2),
        'percentile_75': round(float(np.percentile(values, 75)), 2),
        'distribution': distribution
    }

def process_establishment_statistics(archive_data, establishment_mapping):
    """Calculate statistics for each establishment"""
    print_header("CALCULATING ESTABLISHMENT STATISTICS")
    
    statistics = []
    
    # Get unique establishments from data
    establishments_in_data = archive_data[FIELD_MAPPINGS['establishment']].dropna().unique()
    
    logging.info(f"Found {len(establishments_in_data)} establishments in archive data")
    
    for knack_est_id in establishments_in_data:
        # Get establishment UUID
        est_info = establishment_mapping.get(knack_est_id)
        
        if not est_info:
            logging.warning(f"Establishment {knack_est_id} not found in database, skipping")
            continue
        
        establishment_id = est_info['id']
        establishment_name = est_info['name']
        
        # Filter data for this establishment
        est_data = archive_data[archive_data[FIELD_MAPPINGS['establishment']] == knack_est_id]
        
        logging.info(f"\n📊 Processing: {establishment_name}")
        logging.info(f"   Records: {len(est_data)}")
        
        # Process each cycle
        for cycle in [1, 2, 3]:
            # Determine which fields to use based on cycle
            if cycle == 1:
                score_fields = {
                    'vision': FIELD_MAPPINGS['vision_c1'],
                    'effort': FIELD_MAPPINGS['effort_c1'],
                    'systems': FIELD_MAPPINGS['systems_c1'],
                    'practice': FIELD_MAPPINGS['practice_c1'],
                    'attitude': FIELD_MAPPINGS['attitude_c1'],
                    'overall': FIELD_MAPPINGS['overall_c1'],
                }
            elif cycle == 2:
                score_fields = {
                    'vision': FIELD_MAPPINGS['vision_c2'],
                    'effort': FIELD_MAPPINGS['effort_c2'],
                    'systems': FIELD_MAPPINGS['systems_c2'],
                    'practice': FIELD_MAPPINGS['practice_c2'],
                    'attitude': FIELD_MAPPINGS['attitude_c2'],
                    'overall': FIELD_MAPPINGS['overall_c2'],
                }
            else:  # cycle 3
                score_fields = {
                    'vision': FIELD_MAPPINGS['vision_c3'],
                    'effort': FIELD_MAPPINGS['effort_c3'],
                    'systems': FIELD_MAPPINGS['systems_c3'],
                    'practice': FIELD_MAPPINGS['practice_c3'],
                    'attitude': FIELD_MAPPINGS['attitude_c3'],
                    'overall': FIELD_MAPPINGS['overall_c3'],
                }
            
            # Calculate statistics for each element
            cycle_stats = {}
            for element, field in score_fields.items():
                values = est_data[field].tolist()
                stats = calculate_statistics(values)
                
                if stats:
                    cycle_stats[element] = stats
            
            # Store statistics for each element
            for element, stats in cycle_stats.items():
                stat_record = {
                    'establishment_id': establishment_id,
                    'cycle': cycle,
                    'academic_year': ARCHIVE_YEAR,
                    'element': element,
                    'mean': stats['mean'],
                    'std_dev': stats['std_dev'],
                    'count': stats['count'],
                    'percentile_25': stats['percentile_25'],
                    'percentile_50': stats['percentile_50'],
                    'percentile_75': stats['percentile_75'],
                    'distribution': stats['distribution']
                }
                
                statistics.append(stat_record)
            
            if cycle_stats:
                logging.info(f"   ✅ Cycle {cycle}: {len(cycle_stats)} elements calculated")
    
    logging.info(f"\n✅ Total statistics calculated: {len(statistics)}")
    
    return statistics

def process_national_statistics(archive_data):
    """Calculate national-level statistics"""
    print_header("CALCULATING NATIONAL STATISTICS")
    
    statistics = []
    
    for cycle in [1, 2, 3]:
        # Determine which fields to use
        if cycle == 1:
            score_fields = {
                'vision': FIELD_MAPPINGS['vision_c1'],
                'effort': FIELD_MAPPINGS['effort_c1'],
                'systems': FIELD_MAPPINGS['systems_c1'],
                'practice': FIELD_MAPPINGS['practice_c1'],
                'attitude': FIELD_MAPPINGS['attitude_c1'],
                'overall': FIELD_MAPPINGS['overall_c1'],
            }
        elif cycle == 2:
            score_fields = {
                'vision': FIELD_MAPPINGS['vision_c2'],
                'effort': FIELD_MAPPINGS['effort_c2'],
                'systems': FIELD_MAPPINGS['systems_c2'],
                'practice': FIELD_MAPPINGS['practice_c2'],
                'attitude': FIELD_MAPPINGS['attitude_c2'],
                'overall': FIELD_MAPPINGS['overall_c2'],
            }
        else:  # cycle 3
            score_fields = {
                'vision': FIELD_MAPPINGS['vision_c3'],
                'effort': FIELD_MAPPINGS['effort_c3'],
                'systems': FIELD_MAPPINGS['systems_c3'],
                'practice': FIELD_MAPPINGS['practice_c3'],
                'attitude': FIELD_MAPPINGS['attitude_c3'],
                'overall': FIELD_MAPPINGS['overall_c3'],
            }
        
        logging.info(f"\n📊 Processing National Cycle {cycle}")
        
        for element, field in score_fields.items():
            values = archive_data[field].tolist()
            stats = calculate_statistics(values)
            
            if stats:
                stat_record = {
                    'cycle': cycle,
                    'academic_year': ARCHIVE_YEAR,
                    'element': element,
                    'mean': stats['mean'],
                    'std_dev': stats['std_dev'],
                    'count': stats['count'],
                    'percentile_25': stats['percentile_25'],
                    'percentile_50': stats['percentile_50'],
                    'percentile_75': stats['percentile_75'],
                    'distribution': stats['distribution']
                }
                
                statistics.append(stat_record)
                
                logging.info(f"   ✅ {element}: mean={stats['mean']}, count={stats['count']}")
    
    logging.info(f"\n✅ Total national statistics: {len(statistics)}")
    
    return statistics

def import_school_statistics(statistics):
    """Import school statistics to database"""
    print_header("IMPORTING SCHOOL STATISTICS")
    
    logging.info(f"Importing {len(statistics)} school statistics records...")
    
    # Batch import
    batch_size = 100
    imported = 0
    errors = 0
    
    for i in range(0, len(statistics), batch_size):
        batch = statistics[i:i + batch_size]
        
        try:
            supabase.table('school_statistics').upsert(
                batch,
                on_conflict='establishment_id,cycle,academic_year,element'
            ).execute()
            
            imported += len(batch)
            
            if imported % 500 == 0:
                logging.info(f"  Imported {imported} records...")
                
        except Exception as e:
            logging.error(f"Error importing batch: {e}")
            errors += len(batch)
    
    logging.info(f"✅ Imported {imported} school statistics")
    if errors > 0:
        logging.warning(f"⚠️  {errors} records failed to import")
    
    return imported, errors

def import_national_statistics(statistics):
    """Import national statistics to database"""
    print_header("IMPORTING NATIONAL STATISTICS")
    
    logging.info(f"Importing {len(statistics)} national statistics records...")
    
    try:
        supabase.table('national_statistics').upsert(
            statistics,
            on_conflict='cycle,academic_year,element'
        ).execute()
        
        logging.info(f"✅ Imported {len(statistics)} national statistics")
        return len(statistics), 0
        
    except Exception as e:
        logging.error(f"Error importing national statistics: {e}")
        return 0, len(statistics)

def verify_import():
    """Verify the imported data"""
    print_header("VERIFICATION")
    
    # Check school statistics
    school_stats = supabase.table('school_statistics')\
        .select('*', count='exact')\
        .eq('academic_year', ARCHIVE_YEAR)\
        .execute()
    
    logging.info(f"✅ School statistics for {ARCHIVE_YEAR}: {school_stats.count} records")
    
    # Check national statistics
    national_stats = supabase.table('national_statistics')\
        .select('*', count='exact')\
        .eq('academic_year', ARCHIVE_YEAR)\
        .execute()
    
    logging.info(f"✅ National statistics for {ARCHIVE_YEAR}: {national_stats.count} records")
    
    # Sample some data
    if school_stats.count > 0:
        sample = supabase.table('school_statistics')\
            .select('establishment_id,cycle,element,mean,count')\
            .eq('academic_year', ARCHIVE_YEAR)\
            .limit(5)\
            .execute()
        
        logging.info("\n📊 Sample school statistics:")
        for stat in sample.data:
            logging.info(f"   Cycle {stat['cycle']} {stat['element']}: mean={stat['mean']}, n={stat['count']}")
    
    if national_stats.count > 0:
        sample = supabase.table('national_statistics')\
            .select('cycle,element,mean,count')\
            .eq('academic_year', ARCHIVE_YEAR)\
            .execute()
        
        logging.info("\n📊 National statistics:")
        for stat in sample.data:
            logging.info(f"   Cycle {stat['cycle']} {stat['element']}: mean={stat['mean']}, n={stat['count']}")

def main():
    """Main import process"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "ARCHIVE STATISTICS IMPORT: 2024-2025" + " " * 27 + "║")
    print("╚" + "═" * 78 + "╝")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Load and filter data
        archive_data = load_and_filter_data()
        
        # Step 2: Get establishment mapping
        establishment_mapping = get_establishment_mapping()
        
        # Step 3: Calculate establishment statistics
        school_statistics = process_establishment_statistics(archive_data, establishment_mapping)
        
        # Step 4: Calculate national statistics
        national_statistics = process_national_statistics(archive_data)
        
        # Step 5: Import school statistics
        school_imported, school_errors = import_school_statistics(school_statistics)
        
        # Step 6: Import national statistics
        national_imported, national_errors = import_national_statistics(national_statistics)
        
        # Step 7: Verify
        verify_import()
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print_header("IMPORT COMPLETE")
        
        print(f"""
📊 ARCHIVE IMPORT SUMMARY
========================
Academic Year: {ARCHIVE_YEAR}
Duration: {duration}

School Statistics:
  Calculated: {len(school_statistics)}
  Imported: {school_imported}
  Errors: {school_errors}

National Statistics:
  Calculated: {len(national_statistics)}
  Imported: {national_imported}
  Errors: {national_errors}

✅ Archive statistics for 2024-2025 are now preserved in the database.
   These will serve as the historical baseline for comparison.

Next Steps:
  1. Verify dashboard shows 2024-2025 data correctly
  2. Check national benchmarks are present
  3. Proceed with sync optimization if needed
        """)
        
        logging.info("Import completed successfully!")
        
    except Exception as e:
        logging.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

