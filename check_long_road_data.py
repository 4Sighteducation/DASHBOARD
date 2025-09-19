import os
from datetime import datetime
from supabase import create_client, Client

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Please set SUPABASE_URL and SUPABASE_KEY environment variables")
    exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("LONG ROAD SIXTH FORM COLLEGE - DATA INVESTIGATION")
print("=" * 80)

# 1. Find Long Road establishment
establishment_result = supabase.table('establishments').select('*').ilike('name', '%Long Road%').execute()

if not establishment_result.data:
    print("ERROR: Long Road Sixth Form College not found in establishments table")
    exit(1)

establishment = establishment_result.data[0]
establishment_id = establishment['id']
establishment_name = establishment['name']

print(f"\n✓ Found establishment: {establishment_name}")
print(f"  ID: {establishment_id}")
print(f"  Knack ID: {establishment.get('knack_id')}")

# 2. Check students and their academic years
print("\n" + "=" * 60)
print("STUDENT DATA:")
print("=" * 60)

students_result = supabase.table('students').select('*').eq('establishment_id', establishment_id).execute()
students = students_result.data

if not students:
    print("❌ NO STUDENTS FOUND!")
else:
    print(f"Total students: {len(students)}")
    
    # Group by academic year
    year_counts = {}
    created_dates = {}
    
    for student in students:
        year = student.get('academic_year', 'None')
        if year not in year_counts:
            year_counts[year] = 0
            created_dates[year] = []
        year_counts[year] += 1
        created_dates[year].append(student.get('created_at'))
    
    print("\nStudents by academic year:")
    for year, count in sorted(year_counts.items()):
        print(f"  {year}: {count} students")
        if created_dates[year]:
            # Parse dates and find min/max
            dates = [datetime.fromisoformat(d.replace('Z', '+00:00')) for d in created_dates[year] if d]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                print(f"    Created between: {min_date.date()} and {max_date.date()}")

# 3. Check VESPA scores and their academic years
print("\n" + "=" * 60)
print("VESPA SCORES DATA:")
print("=" * 60)

vespa_result = supabase.table('vespa_scores').select('*').eq('establishment_id', establishment_id).execute()
vespa_scores = vespa_result.data

if not vespa_scores:
    print("❌ NO VESPA SCORES FOUND!")
else:
    print(f"Total VESPA scores: {len(vespa_scores)}")
    
    # Group by academic year and cycle
    vespa_years = {}
    completion_dates = {}
    
    for score in vespa_scores:
        year = score.get('academic_year', 'None')
        cycle = score.get('cycle', 'Unknown')
        key = f"{year} - Cycle {cycle}"
        
        if key not in vespa_years:
            vespa_years[key] = 0
            completion_dates[key] = []
        vespa_years[key] += 1
        
        if score.get('completion_date'):
            completion_dates[key].append(score['completion_date'])
    
    print("\nVESPA scores by academic year and cycle:")
    for key, count in sorted(vespa_years.items()):
        print(f"  {key}: {count} scores")
        if completion_dates[key]:
            # Parse dates and find min/max
            dates = [datetime.fromisoformat(d.replace('Z', '+00:00')) if 'T' in d else datetime.strptime(d, '%Y-%m-%d') for d in completion_dates[key] if d]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                print(f"    Completed between: {min_date.date()} and {max_date.date()}")

# 4. Check for mismatches
print("\n" + "=" * 60)
print("ANALYSIS:")
print("=" * 60)

# Check if students have VESPA scores
students_with_scores = set()
for score in vespa_scores:
    students_with_scores.add(score.get('student_id'))

print(f"Students with VESPA scores: {len(students_with_scores)}/{len(students)}")

# Check for students with wrong academic year
current_year = "2025/2026"
previous_year = "2024/2025"

current_students = [s for s in students if s.get('academic_year') == current_year]
previous_students = [s for s in students if s.get('academic_year') == previous_year]

print(f"\nStudents in {current_year}: {len(current_students)}")
print(f"Students in {previous_year}: {len(previous_students)}")

# Check when current year students were created
if current_students:
    created_dates = [datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')) for s in current_students if s.get('created_at')]
    if created_dates:
        earliest = min(created_dates)
        latest = max(created_dates)
        print(f"\n{current_year} students created between:")
        print(f"  Earliest: {earliest}")
        print(f"  Latest: {latest}")

# Check if there are VESPA scores for 2024/2025 that should be visible
vespa_2024_25 = [v for v in vespa_scores if v.get('academic_year') == previous_year]
print(f"\nVESPA scores for {previous_year}: {len(vespa_2024_25)}")
if vespa_2024_25:
    # Check completion dates
    completion_dates = []
    for v in vespa_2024_25:
        if v.get('completion_date'):
            if 'T' in v['completion_date']:
                completion_dates.append(datetime.fromisoformat(v['completion_date'].replace('Z', '+00:00')))
            else:
                completion_dates.append(datetime.strptime(v['completion_date'], '%Y-%m-%d'))
    
    if completion_dates:
        earliest = min(completion_dates)
        latest = max(completion_dates)
        print(f"  Completed between: {earliest.date()} and {latest.date()}")

# 5. Sample check - show a few students
print("\n" + "=" * 60)
print("SAMPLE STUDENTS (first 5):")
print("=" * 60)

for i, student in enumerate(students[:5]):
    print(f"\nStudent {i+1}:")
    print(f"  Email: {student.get('email', 'N/A')}")
    print(f"  Academic Year: {student.get('academic_year', 'N/A')}")
    print(f"  Created: {student.get('created_at', 'N/A')}")
    print(f"  Knack ID: {student.get('knack_id', 'N/A')}")
    
    # Check if this student has VESPA scores
    student_vespa = [v for v in vespa_scores if v.get('student_id') == student['id']]
    if student_vespa:
        print(f"  VESPA scores: {len(student_vespa)}")
        for v in student_vespa[:2]:  # Show first 2 scores
            print(f"    - Cycle {v.get('cycle')}, Year: {v.get('academic_year')}, Completed: {v.get('completion_date', 'N/A')}")



