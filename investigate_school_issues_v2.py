#!/usr/bin/env python3
"""
Investigate academic year issues for two schools:
1. The British School Al Khubairat - lost archived data
2. Rochdale Sixth Form College - data in wrong academic year
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def investigate_british_school():
    """Check The British School Al Khubairat data"""
    print("=" * 80)
    print("THE BRITISH SCHOOL AL KHUBAIRAT INVESTIGATION")
    print("=" * 80)
    
    # Find the establishment - use correct spelling
    est = supabase.table('establishments').select('*').eq('name', 'The British School Al Khubairat').execute()
    
    if not est.data:
        print("ERROR: School not found!")
        return
    
    establishment_id = est.data[0]['id']
    print(f"Establishment ID: {establishment_id}")
    print(f"Knack ID: {est.data[0].get('knack_id')}")
    
    # Get students for this establishment
    students = supabase.table('students')\
        .select('id, email, created_at, updated_at')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    print(f"\nTotal students: {len(students.data) if students.data else 0}")
    
    if students.data:
        student_ids = [s['id'] for s in students.data]
        
        # Check VESPA scores by academic year
        print("\n--- VESPA Scores by Academic Year ---")
        vespa_scores = supabase.table('vespa_scores')\
            .select('academic_year, cycle, vision, effort, systems, practice, attitude')\
            .in_('student_id', student_ids)\
            .execute()
        
        if vespa_scores.data:
            # Count by academic year and cycle
            year_cycle_counts = defaultdict(lambda: defaultdict(int))
            year_cycle_nulls = defaultdict(lambda: defaultdict(int))
            
            for score in vespa_scores.data:
                year = score.get('academic_year', 'Unknown')
                cycle = score.get('cycle')
                year_cycle_counts[year][cycle] += 1
                
                # Check if VESPA scores are null/zero
                if (score.get('vision') == 0 or score.get('vision') is None):
                    year_cycle_nulls[year][cycle] += 1
            
            for year in sorted(year_cycle_counts.keys()):
                print(f"\n{year}:")
                for cycle in sorted(year_cycle_counts[year].keys()):
                    count = year_cycle_counts[year][cycle]
                    nulls = year_cycle_nulls[year][cycle]
                    print(f"  Cycle {cycle}: {count} records ({nulls} with null/zero scores)")
            
            # Sample some records to see the actual data
            print("\n--- Sample Records (first 5) ---")
            for i, score in enumerate(vespa_scores.data[:5]):
                print(f"  {score['academic_year']} C{score['cycle']}: V={score['vision']}, E={score['effort']}, S={score['systems']}, P={score['practice']}, A={score['attitude']}")
        else:
            print("No VESPA scores found")
    else:
        print("No students found for this establishment")

def investigate_rochdale():
    """Check Rochdale Sixth Form College data"""
    print("\n" + "=" * 80)
    print("ROCHDALE SIXTH FORM COLLEGE INVESTIGATION")
    print("=" * 80)
    
    # Find the establishment
    est = supabase.table('establishments').select('*').ilike('name', '%Rochdale Sixth Form%').execute()
    
    if not est.data:
        print("ERROR: School not found!")
        return
    
    establishment_id = est.data[0]['id']
    print(f"Establishment ID: {establishment_id}")
    print(f"Knack ID: {est.data[0].get('knack_id')}")
    
    # Get students for this establishment
    students = supabase.table('students')\
        .select('id')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    print(f"\nTotal students: {len(students.data) if students.data else 0}")
    
    if students.data:
        student_ids = [s['id'] for s in students.data]
        
        # Check VESPA scores by academic year
        print("\n--- VESPA Scores by Academic Year ---")
        vespa_scores = supabase.table('vespa_scores')\
            .select('academic_year, cycle, created_at, completion_date')\
            .in_('student_id', student_ids)\
            .execute()
        
        if vespa_scores.data:
            # Count by academic year and cycle
            year_cycle_counts = defaultdict(lambda: defaultdict(int))
            dates_by_year = defaultdict(set)
            completion_dates_by_year = defaultdict(set)
            
            for score in vespa_scores.data:
                year = score.get('academic_year', 'Unknown')
                cycle = score.get('cycle')
                year_cycle_counts[year][cycle] += 1
                
                # Track creation dates
                if score.get('created_at'):
                    dates_by_year[year].add(score['created_at'][:10])
                
                # Track completion dates
                if score.get('completion_date'):
                    completion_dates_by_year[year].add(score['completion_date'])
            
            for year in sorted(year_cycle_counts.keys()):
                print(f"\n{year}:")
                for cycle in sorted(year_cycle_counts[year].keys()):
                    count = year_cycle_counts[year][cycle]
                    print(f"  Cycle {cycle}: {count} records")
                
                # Show date ranges
                if year in dates_by_year:
                    dates = sorted(dates_by_year[year])
                    print(f"  Created dates: {dates[0]} to {dates[-1]}")
                
                if year in completion_dates_by_year:
                    comp_dates = sorted(completion_dates_by_year[year])
                    print(f"  Completion dates: {comp_dates[0]} to {comp_dates[-1]}")
        
        # Check recent updates
        print("\n--- Recent VESPA Score Updates (last 10) ---")
        recent = supabase.table('vespa_scores')\
            .select('student_id, cycle, academic_year, created_at, updated_at, completion_date')\
            .in_('student_id', student_ids)\
            .order('updated_at', desc=True)\
            .limit(10)\
            .execute()
        
        if recent.data:
            for score in recent.data:
                print(f"  {score['academic_year']} Cycle {score['cycle']}: Completion={score.get('completion_date')}, Created={score['created_at'][:16]}, Updated={score.get('updated_at', 'N/A')[:16] if score.get('updated_at') else 'N/A'}")
    else:
        print("No students found for this establishment")

def check_academic_year_logic():
    """Check how academic years are being calculated"""
    print("\n" + "=" * 80)
    print("ACADEMIC YEAR CALCULATION ANALYSIS")
    print("=" * 80)
    
    # Check some recent VESPA scores to see their dates vs academic years
    print("\n--- Checking Recent Records ---")
    
    recent_scores = supabase.table('vespa_scores')\
        .select('id, student_id, cycle, academic_year, completion_date, created_at')\
        .order('created_at', desc=True)\
        .limit(20)\
        .execute()
    
    if recent_scores.data:
        print("Recent VESPA scores (completion_date -> academic_year):")
        for score in recent_scores.data[:10]:
            comp_date = score.get('completion_date', 'None')
            acad_year = score.get('academic_year', 'None')
            created = score.get('created_at', '')[:10]
            
            # Check if academic year makes sense
            if comp_date and comp_date != 'None':
                # Parse date
                year = int(comp_date[:4])
                month = int(comp_date[5:7])
                
                # Expected academic year (UK: Aug-Jul)
                if month >= 8:  # August or later
                    expected = f"{year}/{year+1}"
                else:
                    expected = f"{year-1}/{year}"
                
                match = "✓" if expected == acad_year else "✗"
                print(f"  {comp_date} -> {acad_year} (expected: {expected}) {match}")
            else:
                print(f"  No completion date, Created: {created} -> {acad_year}")

def main():
    investigate_british_school()
    investigate_rochdale()
    check_academic_year_logic()
    
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print("""
Issues identified:

1. The British School Al Khubairat:
   - Check if archived data was overwritten by blank records
   - May need to restore from backup if historical data is missing
   
2. Rochdale Sixth Form College:
   - Check if completion dates are correct
   - Verify academic year calculation logic
   
Solutions:
1. Add protection against overwriting non-null data with nulls
2. Fix academic year calculation based on completion dates
3. Add validation to prevent data misalignment
    """)

if __name__ == "__main__":
    main()
