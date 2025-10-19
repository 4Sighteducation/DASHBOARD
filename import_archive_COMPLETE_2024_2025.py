#!/usr/bin/env python3
"""
COMPLETE Archive Import for 2024-2025
======================================
Full import of students, VESPA scores, and statistics from August 2025 snapshot

This will:
1. Import all students from Object_10 (2024-2025 academic year)
2. Import all VESPA scores for all cycles
3. Calculate school statistics
4. Calculate national statistics
5. Mark everything as archived/2024-2025

This fixes the missing 20,000+ students issue!
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('archive_import_COMPLETE_2024_2025.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# CSV Path
OBJECT_10_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"

# Academic year
ARCHIVE_YEAR = '2024/2025'

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def load_establishment_mapping():
    """Load establishment mappings"""
    print_header("LOADING ESTABLISHMENTS")
    
    establishments = supabase.table('establishments').select('id,knack_id,name').execute()
    mapping = {est['knack_id']: est for est in establishments.data}
    
    logging.info(f"✅ Loaded {len(mapping)} establishments")
    return mapping

def load_and_filter_data():
    """Load Object_10 and filter for 2024-2025"""
    print_header("LOADING OBJECT_10 DATA")
    
    logging.info("Reading CSV in chunks...")
    
    chunks = []
    chunk_size = 10000
    total_rows = 0
    
    for chunk in pd.read_csv(OBJECT_10_PATH, chunksize=chunk_size, low_memory=False):
        chunks.append(chunk)
        total_rows += len(chunk)
        if total_rows % 50000 == 0:
            logging.info(f"  Loaded {total_rows:,} rows...")
    
    df = pd.concat(chunks, ignore_index=True)
    logging.info(f"✅ Total records: {len(df):,}")
    
    # Convert dates
    df['created_date'] = pd.to_datetime(df['created'], errors='coerce')
    
    # Filter for 2024-2025 (Sept 1, 2024 - Aug 31, 2025)
    archive_data = df[
        (df['created_date'] >= '2024-09-01') & 
        (df['created_date'] <= '2025-08-31')
    ].copy()
    
    logging.info(f"✅ Filtered to {len(archive_data):,} records from 2024-2025")
    
    return archive_data

def import_students(data, establishment_mapping):
    """Import students from Object_10"""
    print_header("IMPORTING STUDENTS")
    
    logging.info("Processing students...")
    
    # Track statistics
    stats = {
        'new': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    # Get existing students by email
    logging.info("Loading existing students...")
    existing_students = {}
    offset = 0
    page_size = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('email,id,academic_year')\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not batch.data:
            break
        
        for student in batch.data:
            email = student.get('email', '').lower().strip()
            if email:
                # Store by email + academic_year combo
                key = f"{email}_{student.get('academic_year', '')}"
                existing_students[key] = student
        
        offset += page_size
        if len(batch.data) < page_size:
            break
    
    logging.info(f"Found {len(existing_students)} existing student records")
    
    # Process students from Object_10
    students_to_import = []
    batch_size = 100
    
    for idx, row in data.iterrows():
        # Extract student data
        email = row.get('field_197_email', '').strip() if pd.notna(row.get('field_197_email')) else ''
        
        if not email:
            stats['skipped'] += 1
            continue
        
        email_lower = email.lower()
        
        # Get establishment
        knack_est_id = row.get('field_133')
        est_info = establishment_mapping.get(knack_est_id)
        
        if not est_info:
            stats['skipped'] += 1
            continue
        
        # Check if student already exists for this year
        key = f"{email_lower}_{ARCHIVE_YEAR}"
        
        if key not in existing_students:
            # New student record
            student_data = {
                'email': email_lower,
                'name': row.get('field_187_full', '') if pd.notna(row.get('field_187_full')) else '',
                'establishment_id': est_info['id'],
                'knack_id': row.get('id', ''),
                'academic_year': ARCHIVE_YEAR,
                'year_group': str(row.get('field_144', '')) if pd.notna(row.get('field_144')) else '',
                'group': str(row.get('field_223', '')) if pd.notna(row.get('field_223')) else '',
                'course': str(row.get('field_2299', '')) if pd.notna(row.get('field_2299')) else '',
                'faculty': str(row.get('field_782', '')) if pd.notna(row.get('field_782')) else '',
            }
            
            students_to_import.append(student_data)
            stats['new'] += 1
        else:
            stats['updated'] += 1
        
        # Import in batches
        if len(students_to_import) >= batch_size:
            try:
                supabase.table('students').upsert(
                    students_to_import,
                    on_conflict='email,academic_year'
                ).execute()
                
                if stats['new'] % 1000 == 0:
                    logging.info(f"  Imported {stats['new']} students...")
                
                students_to_import = []
                
            except Exception as e:
                logging.error(f"Error importing batch: {e}")
                stats['errors'] += len(students_to_import)
                students_to_import = []
    
    # Import remaining
    if students_to_import:
        try:
            supabase.table('students').upsert(
                students_to_import,
                on_conflict='email,academic_year'
            ).execute()
        except Exception as e:
            logging.error(f"Error importing final batch: {e}")
            stats['errors'] += len(students_to_import)
    
    logging.info(f"\n✅ Students Import Complete:")
    logging.info(f"   New: {stats['new']}")
    logging.info(f"   Updated: {stats['updated']}")
    logging.info(f"   Skipped: {stats['skipped']}")
    logging.info(f"   Errors: {stats['errors']}")
    
    return stats

def get_student_mapping():
    """Get mapping of emails to student IDs for 2024-2025"""
    logging.info("Loading student mappings...")
    
    student_map = {}
    offset = 0
    page_size = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('id,email')\
            .eq('academic_year', ARCHIVE_YEAR)\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not batch.data:
            break
        
        for student in batch.data:
            email = student.get('email', '').lower().strip()
            if email:
                student_map[email] = student['id']
        
        offset += page_size
        if len(batch.data) < page_size:
            break
    
    logging.info(f"✅ Loaded {len(student_map)} student mappings")
    return student_map

def import_vespa_scores(data, student_map):
    """Import VESPA scores for all cycles"""
    print_header("IMPORTING VESPA SCORES")
    
    logging.info("Processing VESPA scores...")
    
    stats = {
        'imported': 0,
        'skipped': 0,
        'errors': 0
    }
    
    scores_to_import = []
    batch_size = 500
    
    # Field mappings for cycles
    cycle_fields = {
        1: {
            'vision': 'field_155', 'effort': 'field_156', 'systems': 'field_157',
            'practice': 'field_158', 'attitude': 'field_159', 'overall': 'field_160'
        },
        2: {
            'vision': 'field_161', 'effort': 'field_162', 'systems': 'field_163',
            'practice': 'field_164', 'attitude': 'field_165', 'overall': 'field_166'
        },
        3: {
            'vision': 'field_167', 'effort': 'field_168', 'systems': 'field_169',
            'practice': 'field_170', 'attitude': 'field_171', 'overall': 'field_172'
        }
    }
    
    for idx, row in data.iterrows():
        # Get student
        email = row.get('field_197_email', '').strip().lower() if pd.notna(row.get('field_197_email')) else ''
        
        if not email or email not in student_map:
            stats['skipped'] += 1
            continue
        
        student_id = student_map[email]
        
        # Import all cycles
        for cycle, fields in cycle_fields.items():
            # Check if this cycle has data
            has_data = any(pd.notna(row.get(field)) for field in fields.values())
            
            if not has_data:
                continue
            
            # Extract scores
            score_data = {
                'student_id': student_id,
                'cycle': cycle,
                'academic_year': ARCHIVE_YEAR,
                'vision': int(float(row.get(fields['vision']))) if pd.notna(row.get(fields['vision'])) else None,
                'effort': int(float(row.get(fields['effort']))) if pd.notna(row.get(fields['effort'])) else None,
                'systems': int(float(row.get(fields['systems']))) if pd.notna(row.get(fields['systems'])) else None,
                'practice': int(float(row.get(fields['practice']))) if pd.notna(row.get(fields['practice'])) else None,
                'attitude': int(float(row.get(fields['attitude']))) if pd.notna(row.get(fields['attitude'])) else None,
                'overall': float(row.get(fields['overall'])) if pd.notna(row.get(fields['overall'])) else None,
            }
            
            # Only add if at least one score exists
            if any(score_data[k] is not None for k in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']):
                scores_to_import.append(score_data)
                stats['imported'] += 1
        
        # Import in batches
        if len(scores_to_import) >= batch_size:
            try:
                supabase.table('vespa_scores').upsert(
                    scores_to_import,
                    on_conflict='student_id,cycle,academic_year'
                ).execute()
                
                if stats['imported'] % 5000 == 0:
                    logging.info(f"  Imported {stats['imported']} VESPA scores...")
                
                scores_to_import = []
                
            except Exception as e:
                logging.error(f"Error importing scores batch: {e}")
                stats['errors'] += len(scores_to_import)
                scores_to_import = []
    
    # Import remaining
    if scores_to_import:
        try:
            supabase.table('vespa_scores').upsert(
                scores_to_import,
                on_conflict='student_id,cycle,academic_year'
            ).execute()
        except Exception as e:
            logging.error(f"Error importing final scores batch: {e}")
            stats['errors'] += len(scores_to_import)
    
    logging.info(f"\n✅ VESPA Scores Import Complete:")
    logging.info(f"   Imported: {stats['imported']}")
    logging.info(f"   Skipped: {stats['skipped']}")
    logging.info(f"   Errors: {stats['errors']}")
    
    return stats

def calculate_statistics(values):
    """Calculate statistics for a set of values"""
    if len(values) == 0:
        return None
    
    values = [v for v in values if pd.notna(v) and v != '']
    values = pd.to_numeric(values, errors='coerce').dropna()
    
    if len(values) == 0:
        return None
    
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

def calculate_and_import_statistics():
    """Calculate statistics from imported data"""
    print_header("CALCULATING STATISTICS")
    
    logging.info("Fetching imported VESPA scores...")
    
    # Get all scores for 2024-2025
    all_scores = []
    offset = 0
    page_size = 1000
    
    while True:
        batch = supabase.table('vespa_scores')\
            .select('student_id,cycle,vision,effort,systems,practice,attitude,overall,students(establishment_id)')\
            .eq('academic_year', ARCHIVE_YEAR)\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not batch.data:
            break
        
        all_scores.extend(batch.data)
        offset += page_size
        
        if len(all_scores) % 10000 == 0:
            logging.info(f"  Loaded {len(all_scores):,} scores...")
        
        if len(batch.data) < page_size:
            break
    
    logging.info(f"✅ Loaded {len(all_scores):,} VESPA scores")
    
    # Calculate school statistics
    school_stats = []
    establishment_data = {}
    
    # Group by establishment
    for score in all_scores:
        est_id = score.get('students', {}).get('establishment_id') if score.get('students') else None
        if not est_id:
            continue
        
        cycle = score.get('cycle')
        key = f"{est_id}_{cycle}"
        
        if key not in establishment_data:
            establishment_data[key] = {
                'establishment_id': est_id,
                'cycle': cycle,
                'vision': [],
                'effort': [],
                'systems': [],
                'practice': [],
                'attitude': [],
                'overall': []
            }
        
        for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
            val = score.get(element)
            if val is not None:
                establishment_data[key][element].append(val)
    
    # Calculate statistics for each establishment/cycle/element
    for key, data in establishment_data.items():
        for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
            stats = calculate_statistics(data[element])
            
            if stats:
                school_stats.append({
                    'establishment_id': data['establishment_id'],
                    'cycle': data['cycle'],
                    'academic_year': ARCHIVE_YEAR,
                    'element': element,
                    **stats
                })
    
    # Import school statistics
    if school_stats:
        batch_size = 100
        for i in range(0, len(school_stats), batch_size):
            batch = school_stats[i:i + batch_size]
            supabase.table('school_statistics').upsert(
                batch,
                on_conflict='establishment_id,cycle,academic_year,element'
            ).execute()
        
        logging.info(f"✅ Imported {len(school_stats)} school statistics")
    
    # Calculate national statistics
    national_stats = []
    national_data = {}
    
    # Group by cycle
    for score in all_scores:
        cycle = score.get('cycle')
        
        if cycle not in national_data:
            national_data[cycle] = {
                'vision': [], 'effort': [], 'systems': [],
                'practice': [], 'attitude': [], 'overall': []
            }
        
        for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
            val = score.get(element)
            if val is not None:
                national_data[cycle][element].append(val)
    
    # Calculate national statistics
    for cycle, data in national_data.items():
        for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
            stats = calculate_statistics(data[element])
            
            if stats:
                national_stats.append({
                    'cycle': cycle,
                    'academic_year': ARCHIVE_YEAR,
                    'element': element,
                    **stats
                })
    
    # Import national statistics
    if national_stats:
        supabase.table('national_statistics').upsert(
            national_stats,
            on_conflict='cycle,academic_year,element'
        ).execute()
        
        logging.info(f"✅ Imported {len(national_stats)} national statistics")
    
    return len(school_stats), len(national_stats)

def verify_import():
    """Verify the import"""
    print_header("VERIFICATION")
    
    # Check students
    students = supabase.table('students').select('*', count='exact')\
        .eq('academic_year', ARCHIVE_YEAR).execute()
    logging.info(f"✅ Students for {ARCHIVE_YEAR}: {students.count}")
    
    # Check VESPA scores
    scores = supabase.table('vespa_scores').select('*', count='exact')\
        .eq('academic_year', ARCHIVE_YEAR).execute()
    logging.info(f"✅ VESPA scores for {ARCHIVE_YEAR}: {scores.count}")
    
    # Check statistics
    school_stats = supabase.table('school_statistics').select('*', count='exact')\
        .eq('academic_year', ARCHIVE_YEAR).execute()
    logging.info(f"✅ School statistics: {school_stats.count}")
    
    national_stats = supabase.table('national_statistics').select('*', count='exact')\
        .eq('academic_year', ARCHIVE_YEAR).execute()
    logging.info(f"✅ National statistics: {national_stats.count}")

def main():
    """Main import process"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 12 + "COMPLETE ARCHIVE IMPORT: 2024-2025" + " " * 32 + "║")
    print("║" + " " * 15 + "Students + Scores + Statistics" + " " * 33 + "║")
    print("╚" + "═" * 78 + "╝")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Load establishments
        establishment_mapping = load_establishment_mapping()
        
        # Step 2: Load and filter data
        data = load_and_filter_data()
        
        # Step 3: Import students
        student_stats = import_students(data, establishment_mapping)
        
        # Step 4: Get student mappings
        student_map = get_student_mapping()
        
        # Step 5: Import VESPA scores
        score_stats = import_vespa_scores(data, student_map)
        
        # Step 6: Calculate and import statistics
        school_count, national_count = calculate_and_import_statistics()
        
        # Step 7: Verify
        verify_import()
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print_header("IMPORT COMPLETE")
        
        print(f"""
📊 COMPLETE IMPORT SUMMARY
=========================
Academic Year: {ARCHIVE_YEAR}
Duration: {duration}

Students:
  New: {student_stats['new']}
  Updated: {student_stats['updated']}
  Skipped: {student_stats['skipped']}
  Errors: {student_stats['errors']}

VESPA Scores:
  Imported: {score_stats['imported']}
  Skipped: {score_stats['skipped']}
  Errors: {score_stats['errors']}

Statistics:
  School: {school_count}
  National: {national_count}

✅ Archive for 2024-2025 is now complete!

This should fix:
  ✅ Missing ~20,000 students issue
  ✅ 13K question responses can now sync
  ✅ Historical statistics preserved
  ✅ Dashboard will show correct data

Next Steps:
  1. Verify dashboard shows 2024-2025 data correctly
  2. Run daily sync - should work better now
  3. Monitor for any remaining issues
        """)
        
        logging.info("Import completed successfully!")
        
    except Exception as e:
        logging.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

