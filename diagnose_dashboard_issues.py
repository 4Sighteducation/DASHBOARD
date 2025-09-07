#!/usr/bin/env python3
"""
VESPA Dashboard Diagnostic Tool
================================
Diagnoses issues with academic year transitions, sync failures, and data display
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VESPADashboardDiagnostics:
    def __init__(self):
        """Initialize diagnostic tool with environment configuration"""
        # Supabase configuration
        self.supabase_url = os.getenv('SUPABASE_URL', 'https://wyddnfeuvligdolpbgod.supabase.co')
        self.supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # Knack configuration
        self.knack_app_id = os.getenv('KNACK_APPLICATION_ID', '5ee90912c38ae7001510c1a9')
        self.knack_api_key = os.getenv('KNACK_API_KEY', '8f733aa5-dd35-4464-8348-64824d1f5f0d')
        
        # Heroku API
        self.heroku_api_url = 'https://vespa-dashboard-9a1f84ee5341.herokuapp.com'
        
        # Academic year settings
        self.current_date = datetime.now()
        self.current_academic_year = self._calculate_academic_year(self.current_date)
        
        # Log file paths
        self.sync_logs_dir = Path('sync_logs')
        self.sync_logs_dir.mkdir(exist_ok=True)
        
    def _calculate_academic_year(self, date: datetime) -> str:
        """Calculate academic year based on date (Sept-Aug)"""
        if date.month >= 9:  # September onwards
            return f"{date.year}/{date.year + 1}"
        else:
            return f"{date.year - 1}/{date.year}"
    
    def check_supabase_connection(self) -> Dict:
        """Test Supabase connection and get basic info"""
        logger.info("Testing Supabase connection...")
        
        if not self.supabase_anon_key:
            return {
                'status': 'error',
                'message': 'SUPABASE_ANON_KEY not found in environment'
            }
        
        headers = {
            'apikey': self.supabase_anon_key,
            'Authorization': f'Bearer {self.supabase_anon_key}'
        }
        
        try:
            # Check tables
            tables_to_check = [
                'establishments',
                'students', 
                'vespa_responses',
                'questionnaire_responses',
                'question_statistics',
                'sync_logs'
            ]
            
            results = {}
            for table in tables_to_check:
                url = f"{self.supabase_url}/rest/v1/{table}?limit=1"
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    results[table] = 'accessible'
                else:
                    results[table] = f'error: {response.status_code}'
            
            return {
                'status': 'connected',
                'tables': results,
                'url': self.supabase_url
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def check_academic_years(self) -> Dict:
        """Check academic year data in Supabase"""
        logger.info("Checking academic year data...")
        
        if not self.supabase_anon_key:
            return {'error': 'No Supabase key configured'}
        
        headers = {
            'apikey': self.supabase_anon_key,
            'Authorization': f'Bearer {self.supabase_anon_key}'
        }
        
        try:
            # Check unique academic years in vespa_responses
            url = f"{self.supabase_url}/rest/v1/vespa_responses?select=academic_year"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                years = set(r.get('academic_year') for r in data if r.get('academic_year'))
                
                # Check questionnaire_responses too
                url2 = f"{self.supabase_url}/rest/v1/questionnaire_responses?select=academic_year"
                response2 = requests.get(url2, headers=headers)
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    years2 = set(r.get('academic_year') for r in data2 if r.get('academic_year'))
                else:
                    years2 = set()
                
                return {
                    'current_academic_year': self.current_academic_year,
                    'vespa_response_years': sorted(list(years)),
                    'questionnaire_response_years': sorted(list(years2)),
                    'missing_current_year': self.current_academic_year not in years,
                    'total_vespa_responses': len(data),
                    'total_questionnaire_responses': len(data2) if response2.status_code == 200 else 0
                }
            else:
                return {'error': f'Failed to fetch data: {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_sync_logs(self, days_back: int = 7) -> Dict:
        """Analyze recent sync logs"""
        logger.info(f"Analyzing sync logs for last {days_back} days...")
        
        # Check local log files
        log_files = list(self.sync_logs_dir.glob('*.txt'))
        log_files.extend(list(Path('.').glob('sync_report_*.txt')))
        
        recent_logs = []
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    # Parse log content
                    if 'VESPA Dashboard Sync Report' in content:
                        lines = content.split('\n')
                        date_line = next((l for l in lines if 'Date:' in l), None)
                        status_line = next((l for l in lines if 'Status:' in l), None)
                        
                        if date_line and status_line:
                            date_str = date_line.split('Date:')[1].strip().rstrip('.')
                            status = status_line.split('Status:')[1].strip().rstrip('.')
                            
                            recent_logs.append({
                                'file': log_file.name,
                                'date': date_str,
                                'status': status,
                                'size': log_file.stat().st_size
                            })
            except Exception as e:
                logger.error(f"Error reading log {log_file}: {e}")
        
        # Check Supabase sync_logs table
        supabase_logs = self._fetch_supabase_sync_logs(days_back)
        
        return {
            'local_logs': recent_logs,
            'supabase_logs': supabase_logs,
            'last_successful_sync': self._find_last_successful_sync(recent_logs, supabase_logs)
        }
    
    def _fetch_supabase_sync_logs(self, days_back: int) -> List[Dict]:
        """Fetch sync logs from Supabase"""
        if not self.supabase_anon_key:
            return []
        
        headers = {
            'apikey': self.supabase_anon_key,
            'Authorization': f'Bearer {self.supabase_anon_key}'
        }
        
        try:
            # Calculate date range
            start_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            url = f"{self.supabase_url}/rest/v1/sync_logs"
            url += f"?created_at=gte.{start_date}"
            url += "&order=created_at.desc"
            url += "&limit=100"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch sync logs: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching sync logs: {e}")
            return []
    
    def _find_last_successful_sync(self, local_logs: List, supabase_logs: List) -> Optional[str]:
        """Find the last successful sync from all logs"""
        successful_syncs = []
        
        # Check local logs
        for log in local_logs:
            if log.get('status') == 'SUCCESS':
                successful_syncs.append(log.get('date'))
        
        # Check Supabase logs
        for log in supabase_logs:
            if log.get('status') == 'success':
                successful_syncs.append(log.get('created_at'))
        
        if successful_syncs:
            return max(successful_syncs)
        return None
    
    def check_recent_data(self) -> Dict:
        """Check for recent data entries"""
        logger.info("Checking for recent data entries...")
        
        if not self.supabase_anon_key:
            return {'error': 'No Supabase key configured'}
        
        headers = {
            'apikey': self.supabase_anon_key,
            'Authorization': f'Bearer {self.supabase_anon_key}'
        }
        
        try:
            # Check recent vespa_responses
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            results = {}
            
            # VESPA responses
            url = f"{self.supabase_url}/rest/v1/vespa_responses"
            url += f"?created_at=gte.{week_ago}"
            url += "&order=created_at.desc&limit=10"
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                results['recent_vespa_responses'] = len(data)
                results['latest_vespa_date'] = data[0]['created_at'] if data else None
            
            # Questionnaire responses
            url = f"{self.supabase_url}/rest/v1/questionnaire_responses"
            url += f"?created_at=gte.{week_ago}"
            url += "&order=created_at.desc&limit=10"
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                results['recent_questionnaire_responses'] = len(data)
                results['latest_questionnaire_date'] = data[0]['created_at'] if data else None
            
            return results
            
        except Exception as e:
            return {'error': str(e)}
    
    def test_heroku_api(self) -> Dict:
        """Test Heroku API endpoints"""
        logger.info("Testing Heroku API endpoints...")
        
        endpoints = [
            '/api/health',
            '/api/establishments',
            '/api/dashboard/overview'
        ]
        
        results = {}
        
        for endpoint in endpoints:
            try:
                url = f"{self.heroku_api_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                results[endpoint] = {
                    'status_code': response.status_code,
                    'accessible': response.status_code in [200, 401, 403]  # Auth errors are OK
                }
                
            except requests.exceptions.Timeout:
                results[endpoint] = {'status_code': None, 'accessible': False, 'error': 'timeout'}
            except Exception as e:
                results[endpoint] = {'status_code': None, 'accessible': False, 'error': str(e)}
        
        return results
    
    def generate_fix_script(self) -> str:
        """Generate SQL script to fix academic year issues"""
        logger.info("Generating fix script...")
        
        script = f"""
-- VESPA Dashboard Academic Year Fix Script
-- Generated: {datetime.now().isoformat()}
-- Current Academic Year: {self.current_academic_year}

-- 1. Add academic year to responses without one
UPDATE vespa_responses 
SET academic_year = '{self.current_academic_year}'
WHERE academic_year IS NULL 
  AND created_at >= '2025-09-01';

UPDATE questionnaire_responses
SET academic_year = '{self.current_academic_year}'
WHERE academic_year IS NULL
  AND created_at >= '2025-09-01';

-- 2. Create index for better performance
CREATE INDEX IF NOT EXISTS idx_vespa_responses_academic_year 
ON vespa_responses(academic_year);

CREATE INDEX IF NOT EXISTS idx_questionnaire_responses_academic_year
ON questionnaire_responses(academic_year);

-- 3. Add sync log entry
INSERT INTO sync_logs (
    sync_type,
    status,
    message,
    created_at,
    details
) VALUES (
    'academic_year_fix',
    'success',
    'Applied academic year fix for {self.current_academic_year}',
    NOW(),
    '{{"script": "diagnose_dashboard_issues.py", "year": "{self.current_academic_year}"}}'::jsonb
);

-- 4. Refresh materialized views if they exist
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS dashboard_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS student_progress;
"""
        return script
    
    def run_full_diagnostic(self) -> None:
        """Run complete diagnostic suite"""
        print("\n" + "="*60)
        print("VESPA DASHBOARD DIAGNOSTIC REPORT")
        print("="*60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Current Academic Year: {self.current_academic_year}")
        print("="*60)
        
        # 1. Supabase Connection
        print("\n📊 SUPABASE CONNECTION")
        print("-"*40)
        supabase_status = self.check_supabase_connection()
        print(f"Status: {supabase_status.get('status')}")
        if 'tables' in supabase_status:
            for table, status in supabase_status['tables'].items():
                icon = "✅" if status == 'accessible' else "❌"
                print(f"  {icon} {table}: {status}")
        
        # 2. Academic Years
        print("\n📅 ACADEMIC YEAR DATA")
        print("-"*40)
        years_data = self.check_academic_years()
        if 'error' not in years_data:
            print(f"Current Year: {years_data['current_academic_year']}")
            print(f"VESPA Response Years: {', '.join(years_data['vespa_response_years']) if years_data['vespa_response_years'] else 'None'}")
            print(f"Questionnaire Years: {', '.join(years_data['questionnaire_response_years']) if years_data['questionnaire_response_years'] else 'None'}")
            
            if years_data['missing_current_year']:
                print(f"⚠️  WARNING: Current academic year {self.current_academic_year} not found in data!")
            
            print(f"Total VESPA Responses: {years_data['total_vespa_responses']:,}")
            print(f"Total Questionnaire Responses: {years_data['total_questionnaire_responses']:,}")
        else:
            print(f"❌ Error: {years_data['error']}")
        
        # 3. Sync Logs
        print("\n📝 SYNC LOG ANALYSIS")
        print("-"*40)
        sync_analysis = self.analyze_sync_logs()
        
        if sync_analysis['local_logs']:
            print("Recent Local Logs:")
            for log in sync_analysis['local_logs'][:5]:
                icon = "✅" if log['status'] == 'SUCCESS' else "❌"
                print(f"  {icon} {log['date']}: {log['status']} ({log['file']})")
        
        if sync_analysis['last_successful_sync']:
            print(f"\nLast Successful Sync: {sync_analysis['last_successful_sync']}")
        else:
            print("\n⚠️  WARNING: No successful syncs found in recent logs!")
        
        # 4. Recent Data
        print("\n📈 RECENT DATA ACTIVITY")
        print("-"*40)
        recent_data = self.check_recent_data()
        if 'error' not in recent_data:
            print(f"VESPA Responses (last 7 days): {recent_data.get('recent_vespa_responses', 0)}")
            print(f"Questionnaire Responses (last 7 days): {recent_data.get('recent_questionnaire_responses', 0)}")
            
            if recent_data.get('latest_vespa_date'):
                print(f"Latest VESPA Entry: {recent_data['latest_vespa_date']}")
            if recent_data.get('latest_questionnaire_date'):
                print(f"Latest Questionnaire Entry: {recent_data['latest_questionnaire_date']}")
        
        # 5. Heroku API
        print("\n🌐 HEROKU API STATUS")
        print("-"*40)
        api_status = self.test_heroku_api()
        for endpoint, status in api_status.items():
            icon = "✅" if status['accessible'] else "❌"
            code = status['status_code'] if status['status_code'] else 'N/A'
            print(f"  {icon} {endpoint}: {code}")
        
        # 6. Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-"*40)
        
        if years_data.get('missing_current_year'):
            print("1. ⚠️  Add current academic year to new data entries")
            print("   Run: python diagnose_dashboard_issues.py --fix-academic-year")
        
        if not sync_analysis.get('last_successful_sync'):
            print("2. ⚠️  Investigate sync failures")
            print("   Run: python diagnose_dashboard_issues.py --check-sync-errors")
        
        if recent_data.get('recent_vespa_responses', 0) == 0:
            print("3. ⚠️  No recent VESPA responses - check data flow")
        
        print("\n" + "="*60)
        print("END OF DIAGNOSTIC REPORT")
        print("="*60)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VESPA Dashboard Diagnostic Tool')
    parser.add_argument('--fix-academic-year', action='store_true', 
                       help='Generate SQL script to fix academic year')
    parser.add_argument('--check-sync-errors', action='store_true',
                       help='Deep dive into sync errors')
    parser.add_argument('--export-report', type=str,
                       help='Export report to file')
    
    args = parser.parse_args()
    
    # Initialize diagnostics
    diag = VESPADashboardDiagnostics()
    
    if args.fix_academic_year:
        script = diag.generate_fix_script()
        filename = f"fix_academic_year_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, 'w') as f:
            f.write(script)
        print(f"✅ Fix script generated: {filename}")
        print("\nTo apply, run:")
        print(f"  psql $DATABASE_URL < {filename}")
    
    elif args.check_sync_errors:
        # Deep dive into sync errors
        print("\n🔍 SYNC ERROR ANALYSIS")
        print("-"*40)
        
        # Check last 30 days of logs
        analysis = diag.analyze_sync_logs(30)
        
        # Count failures
        failures = [l for l in analysis['local_logs'] if l['status'] != 'SUCCESS']
        print(f"Failures in last 30 days: {len(failures)}")
        
        if failures:
            print("\nRecent Failures:")
            for fail in failures[:10]:
                print(f"  - {fail['date']}: {fail['file']}")
    
    else:
        # Run full diagnostic
        diag.run_full_diagnostic()
        
        if args.export_report:
            # Redirect output to file
            import sys
            orig_stdout = sys.stdout
            with open(args.export_report, 'w') as f:
                sys.stdout = f
                diag.run_full_diagnostic()
                sys.stdout = orig_stdout
            print(f"\n✅ Report exported to: {args.export_report}")

if __name__ == "__main__":
    main()
