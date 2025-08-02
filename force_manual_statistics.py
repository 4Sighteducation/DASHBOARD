#!/usr/bin/env python3
"""
Force manual statistics calculation with std_dev and distribution
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import statistics as stats

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_academic_year(date_str, is_australian=False):
    """Calculate academic year based on date and location"""
    if not date_str:
        date = datetime.now()
    else:
        date = datetime.strptime(date_str, '%d/%m/%Y')
    
    if is_australian:
        return str(date.year)
    else:
        if date.month >= 8:
            return f"{date.year}-{str(date.year + 1)[2:]}"
        else:
            return f"{date.year - 1}-{str(date.year)[2:]}"

def force_manual_calculation():
    """Force manual calculation of all statistics"""
    print("Forcing manual statistics calculation...")
    
    # Clear existing statistics
    print("Clearing existing statistics...")
    supabase.table('school_statistics').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    
    # Get all establishments
    establishments = supabase.table('establishments').select('*').execute()
    total_processed = 0
    
    for est in establishments.data:
        print(f"Processing {est['name']}...")
        
        # Get current academic year
        current_year = calculate_academic_year(
            datetime.now().strftime('%d/%m/%Y'), 
            est.get('is_australian', False)
        )
        
        # Get all students for this establishment
        students = supabase.table('students').select('id').eq('establishment_id', est['id']).execute()
        if not students.data:
            continue
            
        student_ids = [s['id'] for s in students.data]
        
        # Calculate statistics for each cycle and element
        for cycle in [1, 2, 3]:
            # Process students in batches of 50 to avoid URI too long error
            all_scores = []
            for i in range(0, len(student_ids), 50):
                batch_ids = student_ids[i:i+50]
                # Get scores for this batch
                batch_scores = supabase.table('vespa_scores')\
                    .select('vision, effort, systems, practice, attitude, overall')\
                    .in_('student_id', batch_ids)\
                    .eq('cycle', cycle)\
                    .execute()
                all_scores.extend(batch_scores.data)
            
            scores = type('obj', (object,), {'data': all_scores})  # Create object with data attribute
            
            if not scores.data:
                continue
            
            # Calculate stats for each element
            for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                values = [s[element] for s in scores.data if s[element] is not None]
                
                if values:
                    # Calculate distribution
                    max_score = 10 if element == 'overall' else 6
                    distribution = [0] * (max_score + 1)
                    for v in values:
                        if 0 <= v <= max_score:
                            distribution[v] += 1
                    
                    # Calculate statistics
                    stats_data = {
                        'establishment_id': est['id'],
                        'cycle': cycle,
                        'academic_year': current_year,
                        'element': element,
                        'mean': round(sum(values) / len(values), 2),
                        'std_dev': round(stats.stdev(values), 2) if len(values) > 1 else 0,
                        'count': len(values),
                        'percentile_25': round(stats.quantiles(values, n=4)[0], 2) if len(values) > 1 else values[0],
                        'percentile_50': round(stats.median(values), 2),
                        'percentile_75': round(stats.quantiles(values, n=4)[2], 2) if len(values) > 1 else values[0],
                        'distribution': distribution
                    }
                    
                    supabase.table('school_statistics').insert(stats_data).execute()
                    total_processed += 1
    
    print(f"\nProcessed {total_processed} statistics records")
    
    # Verify the results
    print("\nVerifying school statistics...")
    sample = supabase.table('school_statistics').select('*').limit(10).execute()
    
    null_std_dev = sum(1 for s in sample.data if s['std_dev'] is None)
    empty_dist = sum(1 for s in sample.data if not s['distribution'] or sum(s['distribution']) == 0)
    
    print(f"Sample of {len(sample.data)} records:")
    print(f"  - Records with null std_dev: {null_std_dev}")
    print(f"  - Records with empty distribution: {empty_dist}")
    
    if sample.data:
        print("\nFirst 3 records detail:")
        for i, record in enumerate(sample.data[:3]):
            dist_sum = sum(record['distribution']) if record['distribution'] else 0
            print(f"  {i+1}. {record['element']}, cycle {record['cycle']}: "
                  f"mean={record['mean']}, std_dev={record['std_dev']}, "
                  f"count={record['count']}, distribution_sum={dist_sum}")

if __name__ == "__main__":
    force_manual_calculation()