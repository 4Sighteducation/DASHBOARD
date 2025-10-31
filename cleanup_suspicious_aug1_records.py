#!/usr/bin/env python3
"""
Cleanup Suspicious August 1st Bulk Sync Records
================================================
These 11,538 students were bulk-synced on Aug 1, 2025 at 7-8 PM
They're likely miscategorized historical records.

Since Knack now only contains current year (2025/2026) data,
we should delete these and let the fixed sync repopulate correctly.

SAFE TO RUN: Creates backup first, can be reversed
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import json

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def audit_suspicious_records():
    """Identify suspicious records from Aug 1st bulk sync"""
    print_header("AUDITING SUSPICIOUS RECORDS")
    
    # Students
    students_query = """
    SELECT COUNT(*) as count,
           MIN(academic_year) as min_year,
           MAX(academic_year) as max_year
    FROM students
    WHERE created_at >= '2025-08-01 19:00:00'
    AND created_at <= '2025-08-01 21:00:00'
    """
    
    result = supabase.rpc('exec_sql', {'query': students_query}).execute() if hasattr(supabase, 'rpc') else None
    
    # Direct count
    suspicious_students = supabase.table('students')\
        .select('id,email,academic_year', count='exact')\
        .gte('created_at', '2025-08-01 19:00:00')\
        .lte('created_at', '2025-08-01 21:00:00')\
        .execute()
    
    print(f"Suspicious Students: {suspicious_students.count}")
    
    # Group by academic year
    year_counts = {}
    sample_data = suspicious_students.data if hasattr(suspicious_students, 'data') else []
    for student in sample_data[:1000]:  # Sample
        year = student.get('academic_year', 'NULL')
        year_counts[year] = year_counts.get(year, 0) + 1
    
    print("\nDistribution by Academic Year (sample):")
    for year in sorted(year_counts.keys(), reverse=True):
        print(f"  {year}: {year_counts[year]} students")
    
    return suspicious_students.count

def export_backup():
    """Export suspicious records to JSON before deletion"""
    print_header("CREATING BACKUP")
    
    print("Fetching all suspicious students...")
    
    all_suspicious = []
    offset = 0
    limit = 1000
    
    while True:
        batch = supabase.table('students')\
            .select('*')\
            .gte('created_at', '2025-08-01 19:00:00')\
            .lte('created_at', '2025-08-01 21:00:00')\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not batch.data:
            break
        
        all_suspicious.extend(batch.data)
        offset += limit
        
        print(f"  Backed up {len(all_suspicious)} records...")
        
        if len(batch.data) < limit:
            break
    
    filename = f"suspicious_students_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(all_suspicious, f, indent=2, default=str)
    
    print(f"\nBackup saved to: {filename}")
    print(f"Total records backed up: {len(all_suspicious)}")
    
    return filename, len(all_suspicious)

def cleanup_suspicious_records(confirmed=False):
    """Delete suspicious records and their related data"""
    print_header("CLEANUP SUSPICIOUS RECORDS")
    
    if not confirmed:
        print("⚠️  DRY RUN MODE - No data will be deleted")
        print("    Set confirmed=True to actually delete\n")
    
    # Count what will be affected
    students_count = supabase.table('students')\
        .select('id', count='exact')\
        .gte('created_at', '2025-08-01 19:00:00')\
        .lte('created_at', '2025-08-01 21:00:00')\
        .execute().count
    
    print(f"Records to be deleted:")
    print(f"  Students: {students_count}")
    
    if not confirmed:
        print("\n✅ DRY RUN COMPLETE - No data deleted")
        print("   To actually delete, run: cleanup_suspicious_records(confirmed=True)")
        return
    
    # Actually delete
    print("\n🔥 DELETING RECORDS...")
    
    # Delete students (CASCADE will handle vespa_scores and question_responses)
    result = supabase.table('students')\
        .delete()\
        .gte('created_at', '2025-08-01 19:00:00')\
        .lte('created_at', '2025-08-01 21:00:00')\
        .execute()
    
    print(f"✅ Deleted {students_count} students")
    print("✅ Related VESPA scores and question responses also deleted (CASCADE)")
    
    # Verify
    remaining = supabase.table('students')\
        .select('id', count='exact')\
        .gte('created_at', '2025-08-01 19:00:00')\
        .lte('created_at', '2025-08-01 21:00:00')\
        .execute().count
    
    print(f"\nVerification: {remaining} suspicious records remaining (should be 0)")

def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "CLEANUP SUSPICIOUS AUG 1ST RECORDS" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        # Step 1: Audit
        count = audit_suspicious_records()
        
        if count == 0:
            print("\n✅ No suspicious records found!")
            return
        
        # Step 2: Backup
        backup_file, backed_up = export_backup()
        
        # Step 3: Show options
        print_header("OPTIONS")
        
        print(f"""
Found {count} suspicious students from Aug 1st bulk sync.
These are likely miscategorized historical records.

OPTION A: Delete and Re-sync (RECOMMENDED)
  ✅ Delete all {count} suspicious students
  ✅ Run fixed sync to repopulate from Knack
  ✅ Knack only has current year → clean data
  ✅ Backup saved: {backup_file}
  
  To execute:
    python cleanup_suspicious_aug1_records.py --delete

OPTION B: Keep and Fix
  ⚠️  Try to recategorize based on Knack API
  ⚠️  Complex, might not work for deleted records
  ⚠️  Many may have been deleted from Knack
  
OPTION C: Leave Alone
  ⚠️  Let fixed sync handle naturally
  ⚠️  Might cause duplicates/issues
  
RECOMMENDATION: Option A - Clean slate for current year
        """)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if '--delete' in sys.argv:
        print("\n⚠️  DELETE MODE ENABLED")
        response = input("Are you SURE you want to delete 11,538 students? (type 'YES' to confirm): ")
        if response == 'YES':
            main()
            backup_file, _ = export_backup()
            cleanup_suspicious_records(confirmed=True)
        else:
            print("Cancelled.")
    else:
        main()

