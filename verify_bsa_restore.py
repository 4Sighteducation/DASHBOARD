#!/usr/bin/env python3
"""
Verify British School Al Khubairat data restoration
Run this after importing and syncing the historical data
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_restoration():
    """Check if the restoration was successful"""
    print("=" * 80)
    print("BRITISH SCHOOL AL KHUBAIRAT - RESTORATION VERIFICATION")
    print("=" * 80)
    
    # Find the establishment
    est = supabase.table('establishments')\
        .select('id')\
        .eq('name', 'The British School Al Khubairat')\
        .execute()
    
    if not est.data:
        print("ERROR: School not found!")
        return
    
    establishment_id = est.data[0]['id']
    
    # Get all students for this school
    students = supabase.table('students')\
        .select('id')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    if not students.data:
        print("ERROR: No students found!")
        return
    
    student_ids = [s['id'] for s in students.data]
    print(f"Found {len(student_ids)} students")
    
    # Check VESPA scores by academic year
    print("\n--- VESPA Scores Analysis ---")
    
    # Get all scores in batches
    all_scores = []
    batch_size = 100
    
    for i in range(0, len(student_ids), batch_size):
        batch = student_ids[i:i+batch_size]
        scores = supabase.table('vespa_scores')\
            .select('academic_year, cycle, vision, effort, systems, practice, attitude')\
            .in_('student_id', batch)\
            .execute()
        all_scores.extend(scores.data)
    
    # Analyze by academic year
    year_stats = defaultdict(lambda: {
        'cycles': defaultdict(lambda: {'total': 0, 'with_data': 0, 'null': 0})
    })
    
    for score in all_scores:
        year = score.get('academic_year', 'Unknown')
        cycle = score.get('cycle')
        
        year_stats[year]['cycles'][cycle]['total'] += 1
        
        # Check if has actual data
        if any(score.get(field) for field in ['vision', 'effort', 'systems', 'practice', 'attitude']):
            year_stats[year]['cycles'][cycle]['with_data'] += 1
        else:
            year_stats[year]['cycles'][cycle]['null'] += 1
    
    # Display results
    for year in sorted(year_stats.keys()):
        print(f"\n{year}:")
        for cycle in sorted(year_stats[year]['cycles'].keys()):
            stats = year_stats[year]['cycles'][cycle]
            total = stats['total']
            with_data = stats['with_data']
            null_data = stats['null']
            
            if total > 0:
                data_pct = (with_data / total) * 100
                null_pct = (null_data / total) * 100
                
                status = "✅ RESTORED" if data_pct > 50 else "⚠️ MOSTLY NULL" if data_pct > 0 else "❌ ALL NULL"
                
                print(f"  Cycle {cycle}: {total} records")
                print(f"    - With data: {with_data} ({data_pct:.1f}%) {status}")
                print(f"    - NULL data: {null_data} ({null_pct:.1f}%)")
    
    # Check question responses
    print("\n--- Question Responses Analysis ---")
    
    response_count = supabase.table('question_responses')\
        .select('academic_year', count='exact')\
        .in_('student_id', student_ids[:10])\
        .execute()
    
    print(f"Sample check (first 10 students): {response_count.count} total responses")
    
    # Summary
    print("\n" + "=" * 80)
    print("RESTORATION SUMMARY")
    print("=" * 80)
    
    # Check if 2024/2025 data exists
    has_2024_25 = '2024/2025' in year_stats and \
                  any(year_stats['2024/2025']['cycles'][c]['with_data'] > 0 for c in [1, 2, 3])
    
    # Check if 2025/2026 is mostly null
    has_null_2025_26 = '2025/2026' in year_stats and \
                       all(year_stats['2025/2026']['cycles'][c]['null'] > 
                           year_stats['2025/2026']['cycles'][c]['with_data'] 
                           for c in year_stats['2025/2026']['cycles'])
    
    if has_2024_25:
        print("✅ 2024/2025 data has been restored!")
        print("   Historical data is back in the system.")
        
        if has_null_2025_26:
            print("\n⚠️ 2025/2026 has NULL records")
            print("   Run cleanup_null_records.sql to remove these after verification")
    else:
        print("❌ 2024/2025 data NOT found")
        print("   Check that:")
        print("   1. Import included correct dates")
        print("   2. Sync completed successfully")
        print("   3. Dates were in DD/MM/YYYY format")
    
    return has_2024_25

if __name__ == "__main__":
    success = verify_restoration()
    
    if success:
        print("\n🎉 Restoration successful! Your historical data is back.")
    else:
        print("\n⚠️ Restoration may need attention. Check the details above.")
