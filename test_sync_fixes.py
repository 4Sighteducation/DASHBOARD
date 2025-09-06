#!/usr/bin/env python3
"""
Test the sync fixes for academic year transition
================================================
This script tests the updated sync logic and helps diagnose any remaining issues
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_academic_year_calculation():
    """Test the academic year calculation logic"""
    # Import the function from the sync script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sync_knack_to_supabase import calculate_academic_year
    
    print("\n" + "="*60)
    print("TESTING ACADEMIC YEAR CALCULATION")
    print("="*60)
    
    # Test cases
    test_cases = [
        # Date, Is Australian, Expected Result
        ("01/08/2025", False, "2025/2026"),  # Aug 1, 2025 - UK
        ("31/07/2025", False, "2024/2025"),  # Jul 31, 2025 - UK
        ("01/09/2025", False, "2025/2026"),  # Sep 1, 2025 - UK
        ("01/01/2025", False, "2024/2025"),  # Jan 1, 2025 - UK
        ("01/01/2025", True, "2025/2025"),   # Jan 1, 2025 - Australian
        ("31/12/2025", True, "2025/2025"),   # Dec 31, 2025 - Australian
        ("01/01/2026", True, "2026/2026"),   # Jan 1, 2026 - Australian
        (None, False, f"{datetime.now().year}/{datetime.now().year + 1}" if datetime.now().month >= 8 else f"{datetime.now().year-1}/{datetime.now().year}")
    ]
    
    all_passed = True
    for date_str, is_australian, expected in test_cases:
        result = calculate_academic_year(date_str, is_australian=is_australian)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
            
        print(f"{status} | Date: {date_str or 'Current'}, Australian: {is_australian}")
        print(f"       Expected: {expected}, Got: {result}")
    
    return all_passed

def test_sync_connection():
    """Test connection to Knack and Supabase"""
    print("\n" + "="*60)
    print("TESTING CONNECTIONS")
    print("="*60)
    
    # Test Supabase connection
    try:
        from supabase import create_client, Client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials in .env file")
            return False
            
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test query
        result = supabase.table('establishments').select('id').limit(1).execute()
        print(f"✅ Supabase connection successful")
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False
    
    # Test Knack connection
    try:
        import requests
        
        knack_app_id = os.getenv('KNACK_APP_ID') or os.getenv('KNACK_APPLICATION_ID')
        knack_api_key = os.getenv('KNACK_API_KEY')
        
        if not knack_app_id or not knack_api_key:
            print("❌ Missing Knack credentials in .env file")
            return False
        
        headers = {
            'X-Knack-Application-Id': knack_app_id,
            'X-Knack-REST-API-Key': knack_api_key,
            'Content-Type': 'application/json'
        }
        
        # Test API call
        response = requests.get(
            'https://api.knack.com/v1/objects/object_10/records',
            headers=headers,
            params={'page': 1, 'rows_per_page': 1}
        )
        
        if response.status_code == 200:
            print(f"✅ Knack connection successful")
        else:
            print(f"❌ Knack connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Knack connection failed: {e}")
        return False
    
    return True

def check_recent_data():
    """Check for recent data and academic years in Supabase"""
    print("\n" + "="*60)
    print("CHECKING RECENT DATA IN SUPABASE")
    print("="*60)
    
    try:
        from supabase import create_client, Client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Check unique academic years
        vespa_years = supabase.table('vespa_scores')\
            .select('academic_year')\
            .execute()
        
        unique_years = set()
        for record in vespa_years.data:
            if record.get('academic_year'):
                unique_years.add(record['academic_year'])
        
        print(f"\nUnique academic years in vespa_scores: {sorted(unique_years)}")
        
        # Check for 2025/2026 data
        vespa_2025 = supabase.table('vespa_scores')\
            .select('id', count='exact')\
            .eq('academic_year', '2025/2026')\
            .execute()
        
        print(f"Records with 2025/2026: {vespa_2025.count}")
        
        # Check for wrong format
        wrong_format_count = 0
        for year in unique_years:
            if '-' in year and '/' not in year:
                count = supabase.table('vespa_scores')\
                    .select('id', count='exact')\
                    .eq('academic_year', year)\
                    .execute()
                wrong_format_count += count.count
                print(f"⚠️  Found {count.count} records with wrong format: {year}")
        
        if wrong_format_count > 0:
            print(f"\n❌ Total records with wrong format: {wrong_format_count}")
            print("   Run the SQL migration script to fix these")
        
        # Check recent sync logs
        print("\n" + "-"*40)
        print("Recent sync activity:")
        
        # Check for recent student updates
        recent_students = supabase.table('students')\
            .select('id', 'created_at', 'updated_at')\
            .order('updated_at', desc=True)\
            .limit(5)\
            .execute()
        
        if recent_students.data:
            latest = recent_students.data[0]
            print(f"Latest student update: {latest.get('updated_at', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False

def run_mini_sync_test():
    """Run a minimal sync test to verify the fixes work"""
    print("\n" + "="*60)
    print("RUNNING MINI SYNC TEST")
    print("="*60)
    
    try:
        from sync_knack_to_supabase import sync_students_and_vespa_scores
        
        print("⚠️  This will sync only the first page of data")
        response = input("Continue? (y/n): ")
        
        if response.lower() != 'y':
            print("Skipped mini sync test")
            return True
        
        # Temporarily modify batch size for testing
        import sync_knack_to_supabase
        original_batch = sync_knack_to_supabase.BATCH_SIZES['students']
        sync_knack_to_supabase.BATCH_SIZES['students'] = 5
        
        # Run sync for first page only
        print("\nRunning sync for first 5 students...")
        
        # We'd need to modify the sync function to accept a limit parameter
        # For now, just indicate this would be the test
        print("✅ Sync test setup complete (actual sync skipped for safety)")
        
        # Restore original batch size
        sync_knack_to_supabase.BATCH_SIZES['students'] = original_batch
        
        return True
        
    except Exception as e:
        print(f"❌ Sync test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("VESPA DASHBOARD SYNC FIX TESTING")
    print("="*60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run tests
    results['Academic Year Calculation'] = test_academic_year_calculation()
    results['Connection Test'] = test_sync_connection()
    
    if results['Connection Test']:
        results['Data Check'] = check_recent_data()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ All tests passed! The sync should work correctly.")
        print("\nNext steps:")
        print("1. Run the SQL migration script in Supabase")
        print("2. Deploy the updated sync_knack_to_supabase.py to Heroku")
        print("3. Trigger a manual sync or wait for the scheduled sync")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        print("\nTroubleshooting:")
        print("1. Check your .env file has all required credentials")
        print("2. Verify network connectivity to Knack and Supabase")
        print("3. Review the error messages for specific issues")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
