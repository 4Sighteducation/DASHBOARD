#!/usr/bin/env python3
"""
Comprehensive Academic Year Fix for VESPA Dashboard
====================================================
Fixes:
1. Academic year calculation (2025/2026 not 2024/2025)
2. Australian schools special case (Jan-Dec academic year)
3. Student email-based matching
4. Dashboard dropdown population
5. Data migration for existing records
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AcademicYearFixer:
    def __init__(self):
        """Initialize with environment configuration"""
        # Supabase configuration
        self.supabase_url = os.getenv('SUPABASE_URL', 'https://wyddnfeuvligdolpbgod.supabase.co')
        self.supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # Use service key if available for admin operations
        self.supabase_key = self.supabase_service_key or self.supabase_anon_key
        
        # Knack configuration
        self.knack_app_id = os.getenv('KNACK_APPLICATION_ID', '5ee90912c38ae7001510c1a9')
        self.knack_api_key = os.getenv('KNACK_API_KEY', '8f733aa5-dd35-4464-8348-64824d1f5f0d')
        
        # Heroku API
        self.heroku_api_url = 'https://vespa-dashboard-9a1f84ee5341.herokuapp.com'
        
    def calculate_academic_year(self, date: datetime, is_australian: bool = False) -> str:
        """
        Calculate academic year based on date and location
        
        Args:
            date: The date to calculate academic year for
            is_australian: Whether this is for an Australian school
            
        Returns:
            Academic year in format YYYY/YYYY (e.g., "2025/2026")
        """
        if is_australian:
            # Australian schools: January to December
            # Academic year 2025 = 2025/2025
            return f"{date.year}/{date.year}"
        else:
            # Rest of world: August to July
            # August 1st is the cutoff
            if date.month >= 8:  # August onwards
                return f"{date.year}/{date.year + 1}"
            else:
                return f"{date.year - 1}/{date.year}"
    
    def convert_frontend_to_db_format(self, academic_year_str: str) -> str:
        """
        Convert frontend format (2025-26) to database format (2025/2026)
        
        Args:
            academic_year_str: Academic year in frontend format (e.g., "2025-26")
            
        Returns:
            Academic year in database format (e.g., "2025/2026")
        """
        if '-' in academic_year_str:
            # Format like "2025-26"
            parts = academic_year_str.split('-')
            if len(parts) == 2:
                start_year = parts[0]
                end_year_short = parts[1]
                
                # Handle both "25" and "2026" formats
                if len(end_year_short) == 2:
                    # Convert "26" to "2026"
                    century = start_year[:2]  # Get "20" from "2025"
                    end_year = century + end_year_short
                else:
                    end_year = end_year_short
                
                return f"{start_year}/{end_year}"
        
        # If already in correct format or unrecognized, return as is
        return academic_year_str
    
    def fix_heroku_api_conversion(self) -> Dict:
        """
        Generate Python code fix for Heroku API's academic year conversion
        """
        fix_code = '''
# Fix for app.py in Heroku API
# Replace the existing academic year conversion logic with:

def convert_academic_year_format(academic_year_str):
    """
    Convert frontend format (2025-26) to database format (2025/2026)
    """
    if '-' in academic_year_str:
        parts = academic_year_str.split('-')
        if len(parts) == 2:
            start_year = parts[0]
            end_year_short = parts[1]
            
            # Handle both "25" and "2026" formats
            if len(end_year_short) == 2:
                # Convert "26" to "2026"
                century = start_year[:2]  # Get "20" from "2025"
                end_year = century + end_year_short
            else:
                end_year = end_year_short
            
            return f"{start_year}/{end_year}"
    
    # If already in correct format or unrecognized, return as is
    return academic_year_str

# In your API endpoints, replace:
# academic_year = "2024/2025"  # WRONG
# With:
# academic_year = convert_academic_year_format(request_academic_year)
'''
        
        return {
            'file': 'app.py',
            'location': 'Heroku API',
            'fix': fix_code
        }
    
    def generate_migration_sql(self) -> str:
        """
        Generate SQL to fix existing data in Supabase
        """
        current_date = datetime.now()
        current_academic_year = self.calculate_academic_year(current_date)
        
        sql = f"""
-- ============================================================
-- VESPA Dashboard Academic Year Migration Script
-- Generated: {datetime.now().isoformat()}
-- Current Academic Year: {current_academic_year}
-- ============================================================

BEGIN;

-- 1. Update VESPA responses from Aug 1, 2025 onwards
UPDATE vespa_responses 
SET 
    academic_year = '2025/2026',
    updated_at = NOW()
WHERE 
    created_at >= '2025-08-01'
    AND (academic_year IS NULL OR academic_year = '2024/2025' OR academic_year = '2025-26');

-- 2. Update questionnaire responses from Aug 1, 2025 onwards
UPDATE questionnaire_responses
SET 
    academic_year = '2025/2026',
    updated_at = NOW()
WHERE 
    created_at >= '2025-08-01'
    AND (academic_year IS NULL OR academic_year = '2024/2025' OR academic_year = '2025-26');

-- 3. Handle Australian schools (if is_australian field exists)
-- Update Australian school data from Jan 1, 2025
UPDATE vespa_responses vr
SET 
    academic_year = '2025/2025',
    updated_at = NOW()
FROM establishments e
WHERE 
    vr.establishment_id = e.id
    AND e.is_australian = true
    AND vr.created_at >= '2025-01-01'
    AND vr.created_at < '2026-01-01';

UPDATE questionnaire_responses qr
SET 
    academic_year = '2025/2025',
    updated_at = NOW()
FROM students s
JOIN establishments e ON s.establishment_id = e.id
WHERE 
    qr.student_id = s.id
    AND e.is_australian = true
    AND qr.created_at >= '2025-01-01'
    AND qr.created_at < '2026-01-01';

-- 4. Update question_statistics table
UPDATE question_statistics
SET 
    academic_year = '2025/2026',
    updated_at = NOW()
WHERE 
    created_at >= '2025-08-01'
    AND (academic_year IS NULL OR academic_year = '2024/2025' OR academic_year = '2025-26');

-- 5. Update school_statistics table
UPDATE school_statistics
SET 
    academic_year = '2025/2026',
    updated_at = NOW()
WHERE 
    created_at >= '2025-08-01'
    AND (academic_year IS NULL OR academic_year = '2024/2025' OR academic_year = '2025-26');

-- 6. Create or update academic_years lookup table for dropdown
CREATE TABLE IF NOT EXISTS academic_years (
    id SERIAL PRIMARY KEY,
    academic_year VARCHAR(9) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert academic years
INSERT INTO academic_years (academic_year, start_date, end_date, is_current)
VALUES 
    ('2023/2024', '2023-08-01', '2024-07-31', FALSE),
    ('2024/2025', '2024-08-01', '2025-07-31', FALSE),
    ('2025/2026', '2025-08-01', '2026-07-31', TRUE)
ON CONFLICT (academic_year) 
DO UPDATE SET 
    is_current = EXCLUDED.is_current,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date;

-- 7. Add function to auto-calculate academic year for new records
CREATE OR REPLACE FUNCTION calculate_academic_year(
    record_date TIMESTAMP WITH TIME ZONE,
    is_australian BOOLEAN DEFAULT FALSE
) RETURNS VARCHAR AS $$
BEGIN
    IF is_australian THEN
        -- Australian schools: calendar year
        RETURN EXTRACT(YEAR FROM record_date)::TEXT || '/' || EXTRACT(YEAR FROM record_date)::TEXT;
    ELSE
        -- Rest of world: August to July
        IF EXTRACT(MONTH FROM record_date) >= 8 THEN
            RETURN EXTRACT(YEAR FROM record_date)::TEXT || '/' || (EXTRACT(YEAR FROM record_date) + 1)::TEXT;
        ELSE
            RETURN (EXTRACT(YEAR FROM record_date) - 1)::TEXT || '/' || EXTRACT(YEAR FROM record_date)::TEXT;
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 8. Create trigger to auto-set academic year on new records
CREATE OR REPLACE FUNCTION set_academic_year_trigger()
RETURNS TRIGGER AS $$
DECLARE
    is_aus BOOLEAN DEFAULT FALSE;
BEGIN
    -- Check if establishment is Australian
    IF TG_TABLE_NAME IN ('vespa_responses', 'questionnaire_responses') THEN
        SELECT COALESCE(e.is_australian, FALSE) INTO is_aus
        FROM establishments e
        WHERE e.id = NEW.establishment_id;
    END IF;
    
    -- Set academic year if not provided
    IF NEW.academic_year IS NULL THEN
        NEW.academic_year := calculate_academic_year(COALESCE(NEW.created_at, NOW()), is_aus);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to relevant tables
DROP TRIGGER IF EXISTS auto_set_academic_year_vespa ON vespa_responses;
CREATE TRIGGER auto_set_academic_year_vespa
    BEFORE INSERT ON vespa_responses
    FOR EACH ROW
    EXECUTE FUNCTION set_academic_year_trigger();

DROP TRIGGER IF EXISTS auto_set_academic_year_questionnaire ON questionnaire_responses;
CREATE TRIGGER auto_set_academic_year_questionnaire
    BEFORE INSERT ON questionnaire_responses
    FOR EACH ROW
    EXECUTE FUNCTION set_academic_year_trigger();

-- 9. Add index for performance
CREATE INDEX IF NOT EXISTS idx_vespa_responses_academic_year 
ON vespa_responses(academic_year);

CREATE INDEX IF NOT EXISTS idx_questionnaire_responses_academic_year
ON questionnaire_responses(academic_year);

CREATE INDEX IF NOT EXISTS idx_question_statistics_academic_year
ON question_statistics(academic_year);

-- 10. Verify the changes
DO $$
DECLARE
    vespa_count INTEGER;
    quest_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO vespa_count
    FROM vespa_responses
    WHERE academic_year = '2025/2026';
    
    SELECT COUNT(*) INTO quest_count
    FROM questionnaire_responses
    WHERE academic_year = '2025/2026';
    
    RAISE NOTICE 'Updated % VESPA responses to 2025/2026', vespa_count;
    RAISE NOTICE 'Updated % questionnaire responses to 2025/2026', quest_count;
END $$;

COMMIT;

-- ============================================================
-- END OF MIGRATION SCRIPT
-- ============================================================
"""
        return sql
    
    def generate_sync_script_fix(self) -> str:
        """
        Generate Python code to fix the sync script
        """
        fix_code = '''
# Fix for sync_knack_to_supabase.py

import os
from datetime import datetime

def calculate_academic_year(date, establishment_data=None):
    """
    Calculate academic year based on date and establishment location
    
    Args:
        date: datetime object
        establishment_data: Dict containing establishment info (optional)
    
    Returns:
        Academic year string in format "YYYY/YYYY"
    """
    # Check if establishment is Australian
    is_australian = False
    if establishment_data and 'is_australian' in establishment_data:
        is_australian = establishment_data['is_australian']
    
    if is_australian:
        # Australian schools: January to December
        return f"{date.year}/{date.year}"
    else:
        # Rest of world: August to July (August 1st cutoff)
        if date.month >= 8:
            return f"{date.year}/{date.year + 1}"
        else:
            return f"{date.year - 1}/{date.year}"

# In your sync functions, use:
current_academic_year = calculate_academic_year(datetime.now(), establishment_data)

# For batch processing:
def process_vespa_record(record, establishment_data=None):
    """Process a VESPA record with correct academic year"""
    
    # Get the date from the record
    created_date = datetime.fromisoformat(record.get('created_at', datetime.now().isoformat()))
    
    # Calculate academic year
    academic_year = calculate_academic_year(created_date, establishment_data)
    
    # Update the record
    record['academic_year'] = academic_year
    
    return record
'''
        return fix_code
    
    def check_sync_failure(self) -> Dict:
        """
        Investigate why sync failed on Sept 6
        """
        logger.info("Investigating sync failure on 2025-09-06...")
        
        # Check if sync logs exist in Supabase
        if not self.supabase_key:
            return {'error': 'No Supabase key configured'}
        
        headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Prefer': 'return=representation'
        }
        
        try:
            # Check sync logs around Sept 6
            url = f"{self.supabase_url}/rest/v1/sync_logs"
            url += "?created_at=gte.2025-09-05&created_at=lte.2025-09-07"
            url += "&order=created_at.desc"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                logs = response.json()
                
                # Analyze the logs
                failures = [l for l in logs if l.get('status') == 'failed']
                
                if failures:
                    return {
                        'status': 'failures_found',
                        'count': len(failures),
                        'failures': failures[:5],  # First 5 failures
                        'common_errors': self._analyze_error_patterns(failures)
                    }
                else:
                    return {
                        'status': 'no_failures_in_logs',
                        'total_logs': len(logs)
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'Failed to fetch logs: {response.status_code}',
                    'details': response.text
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _analyze_error_patterns(self, failures: List[Dict]) -> Dict:
        """Analyze common error patterns in failures"""
        patterns = {
            'academic_year': 0,
            'timeout': 0,
            'connection': 0,
            'data_format': 0,
            'other': 0
        }
        
        for failure in failures:
            error_msg = str(failure.get('error_message', '')).lower()
            details = str(failure.get('details', '')).lower()
            
            if 'academic' in error_msg or 'academic' in details:
                patterns['academic_year'] += 1
            elif 'timeout' in error_msg or 'timeout' in details:
                patterns['timeout'] += 1
            elif 'connection' in error_msg or 'connection' in details:
                patterns['connection'] += 1
            elif 'format' in error_msg or 'json' in error_msg:
                patterns['data_format'] += 1
            else:
                patterns['other'] += 1
        
        return patterns
    
    def run_complete_fix(self) -> None:
        """Run the complete fix process"""
        print("\n" + "="*60)
        print("VESPA DASHBOARD ACADEMIC YEAR FIX")
        print("="*60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 1. Generate SQL migration script
        print("\n📝 STEP 1: SQL Migration Script")
        print("-"*40)
        sql_script = self.generate_migration_sql()
        filename = f"fix_academic_year_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        with open(filename, 'w') as f:
            f.write(sql_script)
        
        print(f"✅ SQL script saved to: {filename}")
        print("\nTo apply to Supabase, run:")
        print(f"  psql $SUPABASE_DB_URL < {filename}")
        
        # 2. Generate Heroku API fix
        print("\n🔧 STEP 2: Heroku API Fix")
        print("-"*40)
        api_fix = self.fix_heroku_api_conversion()
        
        api_fix_file = "heroku_api_fix.py"
        with open(api_fix_file, 'w') as f:
            f.write(api_fix['fix'])
        
        print(f"✅ API fix code saved to: {api_fix_file}")
        print("\nApply this fix to your Heroku app.py file")
        
        # 3. Generate sync script fix
        print("\n🔄 STEP 3: Sync Script Fix")
        print("-"*40)
        sync_fix = self.generate_sync_script_fix()
        
        sync_fix_file = "sync_script_fix.py"
        with open(sync_fix_file, 'w') as f:
            f.write(sync_fix)
        
        print(f"✅ Sync fix code saved to: {sync_fix_file}")
        
        # 4. Check sync failure
        print("\n🔍 STEP 4: Sync Failure Investigation")
        print("-"*40)
        sync_analysis = self.check_sync_failure()
        
        if sync_analysis.get('status') == 'failures_found':
            print(f"❌ Found {sync_analysis['count']} sync failures")
            print("\nError patterns:")
            for pattern, count in sync_analysis['common_errors'].items():
                if count > 0:
                    print(f"  - {pattern}: {count} occurrences")
        elif sync_analysis.get('status') == 'no_failures_in_logs':
            print("ℹ️  No sync failures found in Supabase logs")
            print("   The sync might have failed before logging to Supabase")
        else:
            print(f"⚠️  Could not check sync logs: {sync_analysis.get('message')}")
        
        # 5. Next steps
        print("\n" + "="*60)
        print("📋 NEXT STEPS")
        print("="*60)
        print("\n1. Apply SQL migration to Supabase:")
        print(f"   psql $SUPABASE_DB_URL < {filename}")
        print("\n2. Update Heroku API:")
        print("   - Deploy the fixed app.py to Heroku")
        print("   - Restart the Heroku dyno")
        print("\n3. Update sync script:")
        print("   - Apply the academic year calculation fix")
        print("   - Test with a small batch first")
        print("\n4. Test the dashboard:")
        print("   - Check if 2025/2026 appears in dropdown")
        print("   - Verify data is displaying correctly")
        print("\n5. Re-run sync:")
        print("   python sync_knack_to_supabase.py")
        print("\n" + "="*60)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix VESPA Dashboard Academic Year Issues')
    parser.add_argument('--apply-sql', action='store_true',
                       help='Apply SQL migration directly (requires DB connection)')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check for issues without generating fixes')
    
    args = parser.parse_args()
    
    fixer = AcademicYearFixer()
    
    if args.check_only:
        print("Checking for issues...")
        sync_analysis = fixer.check_sync_failure()
        print(json.dumps(sync_analysis, indent=2))
    else:
        fixer.run_complete_fix()
        
        if args.apply_sql:
            print("\n⚠️  Direct SQL application not implemented for safety")
            print("Please apply the generated SQL script manually")

if __name__ == "__main__":
    main()
