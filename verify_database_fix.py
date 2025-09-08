#!/usr/bin/env python3
"""
Verify that the database constraint fix has been applied correctly
Run this AFTER executing fix_vespa_scores_constraint.sql in Supabase
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_multi_year_support():
    """Test if we can create multiple years of data for the same student"""
    print("=" * 80)
    print("TESTING MULTI-YEAR SUPPORT")
    print("=" * 80)
    
    # Create a test student (or use an existing one)
    test_email = "test_multi_year@example.com"
    
    # Check if test student exists
    students = supabase.table('students')\
        .select('id')\
        .eq('email', test_email)\
        .execute()
    
    if students.data:
        student_id = students.data[0]['id']
        print(f"Using existing test student: {student_id}")
    else:
        # Would need to create with an establishment
        print("No test student found - using a real student for testing")
        # Get any student
        any_student = supabase.table('students')\
            .select('id, email')\
            .limit(1)\
            .execute()
        
        if any_student.data:
            student_id = any_student.data[0]['id']
            test_email = any_student.data[0]['email']
            print(f"Using student: {test_email[:20]}...")
        else:
            print("ERROR: No students found in database")
            return False
    
    # Try to create/update records for different academic years
    test_records = [
        {
            'student_id': student_id,
            'cycle': 1,
            'academic_year': '2023/2024',
            'vision': 7,
            'effort': 8,
            'systems': 7,
            'practice': 8,
            'attitude': 9,
            'overall': 8
        },
        {
            'student_id': student_id,
            'cycle': 1,
            'academic_year': '2024/2025',
            'vision': 8,
            'effort': 8,
            'systems': 8,
            'practice': 9,
            'attitude': 9,
            'overall': 8
        },
        {
            'student_id': student_id,
            'cycle': 1,
            'academic_year': '2025/2026',
            'vision': 9,
            'effort': 9,
            'systems': 9,
            'practice': 9,
            'attitude': 10,
            'overall': 9
        }
    ]
    
    print("\nAttempting to create multiple Cycle 1 records for different years...")
    
    success_count = 0
    for record in test_records:
        try:
            result = supabase.table('vespa_scores').upsert(
                record,
                on_conflict='student_id,cycle,academic_year'
            ).execute()
            print(f"✅ Created/Updated {record['academic_year']} Cycle {record['cycle']}")
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            if 'duplicate key value violates unique constraint' in error_msg:
                if 'vespa_scores_student_id_cycle_key' in error_msg:
                    print(f"❌ FAILED: Old constraint still active! Run the SQL fix first.")
                    print("   The database still has UNIQUE(student_id, cycle)")
                    return False
                else:
                    print(f"❌ Error: {error_msg}")
            else:
                print(f"❌ Error: {error_msg}")
    
    if success_count == len(test_records):
        print("\n✅ SUCCESS! Multi-year support is working!")
        print("   Students can now have multiple years of cycle data.")
        
        # Verify by reading back
        verify = supabase.table('vespa_scores')\
            .select('cycle, academic_year, vision')\
            .eq('student_id', student_id)\
            .eq('cycle', 1)\
            .execute()
        
        print(f"\nVerification - Found {len(verify.data)} Cycle 1 records:")
        for v in verify.data:
            print(f"  - {v['academic_year']}: Vision={v['vision']}")
        
        return True
    else:
        print(f"\n⚠️ PARTIAL SUCCESS: {success_count}/{len(test_records)} records created")
        return False

def check_constraint():
    """Check if the correct constraint exists"""
    print("\n" + "=" * 80)
    print("CHECKING DATABASE CONSTRAINTS")
    print("=" * 80)
    
    # This would need an RPC function to check constraints
    # For now, we'll test by trying to violate the constraint
    
    print("Testing constraint by attempting duplicate insert...")
    
    # Get any existing record
    existing = supabase.table('vespa_scores')\
        .select('student_id, cycle, academic_year')\
        .limit(1)\
        .execute()
    
    if existing.data:
        record = existing.data[0]
        
        # Try to insert duplicate with same student_id, cycle, academic_year
        test_record = {
            'student_id': record['student_id'],
            'cycle': record['cycle'],
            'academic_year': record['academic_year'],
            'vision': 5,
            'effort': 5,
            'systems': 5,
            'practice': 5,
            'attitude': 5,
            'overall': 5
        }
        
        try:
            # This should succeed with upsert (update existing)
            result = supabase.table('vespa_scores').upsert(
                test_record,
                on_conflict='student_id,cycle,academic_year'
            ).execute()
            print("✅ Constraint allows updates to existing (student, cycle, year) combinations")
            
            # Now try different academic year - should create new record
            test_record['academic_year'] = '2099/2100'  # Future year unlikely to exist
            result = supabase.table('vespa_scores').upsert(
                test_record,
                on_conflict='student_id,cycle,academic_year'
            ).execute()
            print("✅ Constraint allows different academic years for same (student, cycle)")
            
            # Clean up test record
            supabase.table('vespa_scores')\
                .delete()\
                .eq('student_id', record['student_id'])\
                .eq('cycle', record['cycle'])\
                .eq('academic_year', '2099/2100')\
                .execute()
            
            return True
            
        except Exception as e:
            if 'vespa_scores_student_id_cycle_key' in str(e):
                print("❌ Old constraint (student_id, cycle) still active!")
                print("   Please run fix_vespa_scores_constraint.sql in Supabase")
                return False
            else:
                print(f"❌ Unexpected error: {e}")
                return False
    else:
        print("No existing records to test with")
        return None

def main():
    print("VESPA SCORES DATABASE FIX VERIFICATION")
    print("=" * 80)
    
    # Test constraint
    constraint_ok = check_constraint()
    
    # Test multi-year support
    multi_year_ok = test_multi_year_support()
    
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    if constraint_ok and multi_year_ok:
        print("✅ Database is correctly configured for multi-year support!")
        print("✅ Students can have multiple years of cycle data")
        print("✅ Sync will work correctly with academic years")
    elif constraint_ok is False or multi_year_ok is False:
        print("❌ Database needs the constraint fix applied")
        print("   Run fix_vespa_scores_constraint.sql in Supabase SQL Editor")
    else:
        print("⚠️ Verification incomplete - manual check recommended")

if __name__ == "__main__":
    main()
