#!/usr/bin/env python3
"""
Database Audit Script - Pre-Archive Import
Analyze current database state before making any changes
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import json

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def audit_students():
    """Audit students table"""
    print_section("STUDENTS TABLE AUDIT")
    
    try:
        # Count total students
        total = supabase.table('students').select('id', count='exact').execute()
        print(f"📊 Total Students: {total.count}")
        
        # Count by academic year
        print("\n🗓️  Students by Academic Year:")
        students = supabase.table('students').select('academic_year').execute()
        
        year_counts = {}
        for student in students.data:
            year = student.get('academic_year', 'NULL')
            year_counts[year] = year_counts.get(year, 0) + 1
        
        for year in sorted(year_counts.keys(), reverse=True):
            print(f"   {year}: {year_counts[year]} students")
        
        # Check for duplicates
        print("\n🔍 Checking for duplicate emails...")
        emails = [s.get('email', '') for s in students.data if s.get('email')]
        unique_emails = len(set(emails))
        print(f"   Total email addresses: {len(emails)}")
        print(f"   Unique email addresses: {unique_emails}")
        print(f"   Duplicates: {len(emails) - unique_emails}")
        
        # Check is_archived field (if exists)
        print("\n📦 Archive Status:")
        try:
            archived = [s for s in students.data if s.get('is_archived', False)]
            print(f"   Archived students: {len(archived)}")
            print(f"   Non-archived students: {len(students.data) - len(archived)}")
        except:
            print("   ⚠️  'is_archived' field not found")
        
        # Sample records
        print("\n📝 Sample Student Records (first 3):")
        sample = supabase.table('students').select('*').limit(3).execute()
        for i, student in enumerate(sample.data, 1):
            print(f"\n   Student {i}:")
            print(f"      Email: {student.get('email', 'N/A')}")
            print(f"      Name: {student.get('name', 'N/A')}")
            print(f"      Academic Year: {student.get('academic_year', 'N/A')}")
            print(f"      Year Group: {student.get('year_group', 'N/A')}")
            print(f"      Created: {student.get('created_at', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error auditing students: {e}")

def audit_vespa_scores():
    """Audit vespa_scores table"""
    print_section("VESPA SCORES TABLE AUDIT")
    
    try:
        # Count total scores
        total = supabase.table('vespa_scores').select('id', count='exact').execute()
        print(f"📊 Total VESPA Score Records: {total.count}")
        
        # Get all scores for analysis
        print("\n⏳ Fetching VESPA scores (this may take a moment)...")
        all_scores = []
        page_size = 1000
        offset = 0
        
        while True:
            batch = supabase.table('vespa_scores')\
                .select('academic_year,cycle,completion_date')\
                .range(offset, offset + page_size - 1)\
                .execute()
            
            if not batch.data:
                break
            
            all_scores.extend(batch.data)
            offset += page_size
            
            if len(batch.data) < page_size:
                break
            
            if offset % 10000 == 0:
                print(f"   Fetched {offset} scores...")
        
        print(f"✅ Fetched {len(all_scores)} total scores\n")
        
        # Count by academic year and cycle
        print("🗓️  VESPA Scores by Academic Year and Cycle:")
        
        year_cycle_counts = {}
        for score in all_scores:
            year = score.get('academic_year', 'NULL')
            cycle = score.get('cycle', 'NULL')
            key = f"{year} - Cycle {cycle}"
            year_cycle_counts[key] = year_cycle_counts.get(key, 0) + 1
        
        for key in sorted(year_cycle_counts.keys()):
            print(f"   {key}: {year_cycle_counts[key]} scores")
        
        # Completion date analysis
        print("\n📅 Completion Date Analysis:")
        dates_present = [s for s in all_scores if s.get('completion_date')]
        dates_null = len(all_scores) - len(dates_present)
        
        print(f"   Scores with completion_date: {len(dates_present)}")
        print(f"   Scores with NULL completion_date: {dates_null}")
        
        if dates_present:
            dates = [datetime.fromisoformat(s['completion_date'].replace('Z', '+00:00')) 
                    for s in dates_present if s.get('completion_date')]
            if dates:
                print(f"   Earliest completion: {min(dates).strftime('%Y-%m-%d')}")
                print(f"   Latest completion: {max(dates).strftime('%Y-%m-%d')}")
        
        # Check for is_archived field
        print("\n📦 Archive Status:")
        try:
            archived = [s for s in all_scores if s.get('is_archived', False)]
            print(f"   Archived scores: {len(archived)}")
            print(f"   Non-archived scores: {len(all_scores) - len(archived)}")
        except:
            print("   ⚠️  'is_archived' field not found")
        
    except Exception as e:
        print(f"❌ Error auditing VESPA scores: {e}")

def audit_establishments():
    """Audit establishments table"""
    print_section("ESTABLISHMENTS TABLE AUDIT")
    
    try:
        establishments = supabase.table('establishments').select('*').execute()
        print(f"📊 Total Establishments: {len(establishments.data)}")
        
        print("\n🏫 Establishments List:")
        for est in establishments.data[:10]:  # Show first 10
            print(f"   • {est.get('name', 'N/A')} (ID: {est.get('id', 'N/A')[:8]}...)")
            print(f"     Knack ID: {est.get('knack_id', 'N/A')}")
            print(f"     Is Australian: {est.get('is_australian', False)}")
        
        if len(establishments.data) > 10:
            print(f"   ... and {len(establishments.data) - 10} more")
        
    except Exception as e:
        print(f"❌ Error auditing establishments: {e}")

def audit_question_responses():
    """Audit question_responses table"""
    print_section("QUESTION RESPONSES TABLE AUDIT")
    
    try:
        total = supabase.table('question_responses').select('id', count='exact').execute()
        print(f"📊 Total Question Responses: {total.count}")
        
        # Get sample for analysis
        sample = supabase.table('question_responses')\
            .select('academic_year,cycle')\
            .limit(1000)\
            .execute()
        
        print("\n🗓️  Sample Distribution (first 1000 responses):")
        year_cycle_counts = {}
        for resp in sample.data:
            year = resp.get('academic_year', 'NULL')
            cycle = resp.get('cycle', 'NULL')
            key = f"{year} - Cycle {cycle}"
            year_cycle_counts[key] = year_cycle_counts.get(key, 0) + 1
        
        for key in sorted(year_cycle_counts.keys()):
            print(f"   {key}: {year_cycle_counts[key]} responses")
        
    except Exception as e:
        print(f"❌ Error auditing question responses: {e}")

def audit_statistics():
    """Audit statistics tables"""
    print_section("STATISTICS TABLES AUDIT")
    
    try:
        # School statistics
        school_stats = supabase.table('school_statistics').select('id', count='exact').execute()
        print(f"📊 School Statistics Records: {school_stats.count}")
        
        # National statistics
        national_stats = supabase.table('national_statistics').select('id', count='exact').execute()
        print(f"📊 National Statistics Records: {national_stats.count}")
        
        # Sample national stats
        if national_stats.count > 0:
            print("\n🌍 National Statistics Sample:")
            sample = supabase.table('national_statistics')\
                .select('academic_year,cycle,element,mean')\
                .limit(10)\
                .execute()
            
            for stat in sample.data:
                print(f"   {stat.get('academic_year', 'N/A')} Cycle {stat.get('cycle', 'N/A')} "
                      f"{stat.get('element', 'N/A')}: {stat.get('mean', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error auditing statistics: {e}")

def check_table_structure():
    """Check table structures"""
    print_section("TABLE STRUCTURE CHECK")
    
    tables = ['students', 'vespa_scores', 'question_responses']
    
    for table_name in tables:
        try:
            print(f"\n📋 {table_name.upper()} table structure:")
            sample = supabase.table(table_name).select('*').limit(1).execute()
            
            if sample.data:
                fields = sample.data[0].keys()
                print(f"   Fields ({len(fields)}):")
                for field in sorted(fields):
                    value = sample.data[0].get(field)
                    value_type = type(value).__name__
                    print(f"      • {field} ({value_type})")
            else:
                print("   ⚠️  No data in table")
                
        except Exception as e:
            print(f"   ❌ Error checking {table_name}: {e}")

def check_constraints():
    """Check database constraints"""
    print_section("CONSTRAINT CHECK")
    
    print("🔒 Testing VESPA scores unique constraint...")
    
    try:
        # Try to create a test duplicate
        test_student_id = '00000000-0000-0000-0000-000000000001'
        test_record_1 = {
            'student_id': test_student_id,
            'cycle': 1,
            'academic_year': '2024/2025',
            'overall': 5
        }
        test_record_2 = {
            'student_id': test_student_id,
            'cycle': 1,
            'academic_year': '2024/2025',
            'overall': 6
        }
        
        # Try upsert with academic_year
        try:
            supabase.table('vespa_scores').upsert(
                [test_record_1],
                on_conflict='student_id,cycle,academic_year'
            ).execute()
            
            # Try to insert duplicate
            supabase.table('vespa_scores').upsert(
                [test_record_2],
                on_conflict='student_id,cycle,academic_year'
            ).execute()
            
            # Clean up
            supabase.table('vespa_scores').delete()\
                .eq('student_id', test_student_id).execute()
            
            print("   ✅ Constraint: (student_id, cycle, academic_year)")
            
        except Exception as e:
            if 'no unique or exclusion constraint' in str(e):
                print("   ⚠️  Constraint: (student_id, cycle) - OLD constraint, needs migration")
            else:
                print(f"   ❌ Error testing constraint: {e}")
    
    except Exception as e:
        print(f"   ❌ Error in constraint check: {e}")

def generate_summary_report():
    """Generate a summary report"""
    print_section("AUDIT SUMMARY REPORT")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"""
📝 Database Audit Summary
Generated: {timestamp}

This audit was run BEFORE implementing the archive import.
The data shown represents the current state of the database.

Key Findings:
1. Check the students count by academic year above
2. Check the VESPA scores distribution
3. Verify if is_archived field exists
4. Note the constraint type in use

Next Steps:
1. Review this audit output carefully
2. Compare with expected values
3. Identify any anomalies
4. Proceed with archive import plan if data looks correct

⚠️  BACKUP RECOMMENDATION ⚠️
Before proceeding with any import:
- Export current database to backup
- Document current state
- Have rollback plan ready
    """)

def export_audit_to_file():
    """Export audit data to JSON file"""
    print_section("EXPORTING AUDIT DATA")
    
    audit_data = {
        'timestamp': datetime.now().isoformat(),
        'students': {},
        'vespa_scores': {},
        'establishments': {},
        'question_responses': {}
    }
    
    try:
        # Export student data
        print("📤 Exporting students data...")
        students = supabase.table('students').select('*').execute()
        audit_data['students'] = {
            'total_count': len(students.data),
            'by_academic_year': {},
            'sample_records': students.data[:5]
        }
        
        for student in students.data:
            year = student.get('academic_year', 'NULL')
            audit_data['students']['by_academic_year'][year] = \
                audit_data['students']['by_academic_year'].get(year, 0) + 1
        
        # Export VESPA scores metadata
        print("📤 Exporting VESPA scores metadata...")
        vespa_count = supabase.table('vespa_scores').select('id', count='exact').execute()
        audit_data['vespa_scores']['total_count'] = vespa_count.count
        
        # Save to file
        filename = f"database_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)
        
        print(f"✅ Audit data exported to: {filename}")
        
    except Exception as e:
        print(f"❌ Error exporting audit data: {e}")

def main():
    """Run all audit checks"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "DATABASE AUDIT SCRIPT" + " " * 37 + "║")
    print("║" + " " * 15 + "Pre-Archive Import Assessment" + " " * 34 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        audit_students()
        audit_vespa_scores()
        audit_establishments()
        audit_question_responses()
        audit_statistics()
        check_table_structure()
        check_constraints()
        generate_summary_report()
        export_audit_to_file()
        
        print("\n" + "=" * 80)
        print("  ✅ AUDIT COMPLETE")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ AUDIT FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

