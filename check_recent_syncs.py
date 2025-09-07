#!/usr/bin/env python3
"""
Quick script to check recent sync logs and identify patterns
"""

import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_sync_logs():
    """Analyze all sync log files in the current directory and subdirectories"""
    
    # Find all sync-related log files
    log_patterns = [
        'sync_report_*.txt',
        'sync_*.log',
        'sync_logs/*.txt',
        'sync_logs/*.log',
        'recent_logs.txt',
        'temp_logs.txt'
    ]
    
    all_logs = []
    
    for pattern in log_patterns:
        if '*' in pattern:
            # It's a glob pattern
            for log_file in Path('.').glob(pattern):
                if log_file.is_file():
                    all_logs.append(log_file)
        else:
            # Direct file path
            log_file = Path(pattern)
            if log_file.exists() and log_file.is_file():
                all_logs.append(log_file)
    
    print(f"Found {len(all_logs)} log files to analyze\n")
    print("="*60)
    
    sync_results = []
    error_patterns = defaultdict(int)
    
    for log_file in all_logs:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for sync report patterns
                if 'VESPA Dashboard Sync Report' in content:
                    # Extract date and status
                    date_match = re.search(r'Date:\s*([\d\-\s:]+)', content)
                    status_match = re.search(r'Status:\s*(\w+)', content)
                    
                    if date_match and status_match:
                        sync_results.append({
                            'file': log_file.name,
                            'date': date_match.group(1).strip().rstrip('.'),
                            'status': status_match.group(1).strip().rstrip('.'),
                            'size': log_file.stat().st_size
                        })
                
                # Look for specific error patterns
                if 'ERROR' in content or 'Failed' in content or 'FAILED' in content:
                    # Extract error messages
                    error_lines = [line for line in content.split('\n') if 'ERROR' in line or 'Failed' in line or 'FAILED' in line]
                    
                    for error_line in error_lines[:5]:  # Just first 5 errors per file
                        # Clean and categorize the error
                        if 'timeout' in error_line.lower():
                            error_patterns['Timeout errors'] += 1
                        elif 'connection' in error_line.lower():
                            error_patterns['Connection errors'] += 1
                        elif 'academic_year' in error_line.lower():
                            error_patterns['Academic year errors'] += 1
                        elif 'supabase' in error_line.lower():
                            error_patterns['Supabase errors'] += 1
                        elif 'knack' in error_line.lower():
                            error_patterns['Knack API errors'] += 1
                        else:
                            error_patterns['Other errors'] += 1
                
                # Look for academic year references
                if 'academic_year' in content or 'academic year' in content.lower():
                    # Extract academic years mentioned
                    year_pattern = r'20\d{2}/20\d{2}'
                    years_found = re.findall(year_pattern, content)
                    if years_found:
                        print(f"📅 Academic years found in {log_file.name}: {set(years_found)}")
                        
        except Exception as e:
            print(f"Error reading {log_file}: {e}")
    
    # Sort sync results by date
    sync_results.sort(key=lambda x: x['date'], reverse=True)
    
    # Display results
    print("\n" + "="*60)
    print("SYNC HISTORY (Most Recent First)")
    print("="*60)
    
    # Initialize counters
    success_count = 0
    fail_count = 0
    
    if sync_results:
        success_count = sum(1 for r in sync_results if r['status'] == 'SUCCESS')
        fail_count = sum(1 for r in sync_results if r['status'] != 'SUCCESS')
        
        print(f"\n📊 Summary: {success_count} successful, {fail_count} failed")
        print("-"*40)
        
        for result in sync_results[:20]:  # Show last 20 syncs
            icon = "✅" if result['status'] == 'SUCCESS' else "❌"
            print(f"{icon} {result['date']:<25} {result['status']:<10} ({result['file']})")
        
        # Find last successful sync
        last_success = next((r for r in sync_results if r['status'] == 'SUCCESS'), None)
        if last_success:
            print(f"\n✅ Last Successful Sync: {last_success['date']}")
            
            # Calculate time since last success
            try:
                last_date = datetime.strptime(last_success['date'], '%Y-%m-%d %H:%M:%S')
                days_ago = (datetime.now() - last_date).days
                print(f"   ({days_ago} days ago)")
            except:
                pass
        else:
            print("\n⚠️  WARNING: No successful syncs found in logs!")
    else:
        print("No sync reports found in log files")
        print("\nChecking for other sync indicators...")
        
        # Look for any date patterns in the logs
        for log_file in all_logs:
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:1000]  # Just check first 1000 chars
                    # Look for date patterns
                    date_pattern = r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'
                    dates_found = re.findall(date_pattern, content)
                    if dates_found:
                        print(f"  Found dates in {log_file.name}: {dates_found[0]}")
            except:
                pass
    
    # Display error patterns
    if error_patterns:
        print("\n" + "="*60)
        print("ERROR PATTERN ANALYSIS")
        print("="*60)
        
        for error_type, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error_type}: {count} occurrences")
    
    # Check for patterns in failures
    if sync_results:
        print("\n" + "="*60)
        print("FAILURE PATTERN ANALYSIS")
        print("="*60)
        
        # Group failures by hour of day
        failure_hours = defaultdict(int)
        for result in sync_results:
            if result['status'] != 'SUCCESS':
                try:
                    dt = datetime.strptime(result['date'], '%Y-%m-%d %H:%M:%S')
                    failure_hours[dt.hour] += 1
                except:
                    pass
        
        if failure_hours:
            print("\nFailures by Hour of Day:")
            for hour in sorted(failure_hours.keys()):
                print(f"  {hour:02d}:00 - {'█' * failure_hours[hour]} ({failure_hours[hour]})")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    # Provide recommendations based on findings
    if fail_count > success_count:
        print("⚠️  More failures than successes - sync process needs urgent attention")
    
    if 'Academic year errors' in error_patterns:
        print("⚠️  Academic year errors detected - need to update year handling logic")
    
    if 'Timeout errors' in error_patterns:
        print("⚠️  Timeout errors present - consider increasing timeout or optimizing queries")
    
    if 'Connection errors' in error_patterns:
        print("⚠️  Connection errors found - check network/firewall settings")
    
    print("\nNext Steps:")
    print("1. Run full diagnostics: python diagnose_dashboard_issues.py")
    print("2. Check Heroku logs: heroku logs --app vespa-dashboard-9a1f84ee5341 --tail")
    print("3. Verify Supabase status: https://status.supabase.com/")
    
    return sync_results, error_patterns

if __name__ == "__main__":
    print("VESPA Dashboard Sync Log Analysis")
    print("="*60)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    analyze_sync_logs()
