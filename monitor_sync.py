#!/usr/bin/env python3
"""
Monitor sync status and send alerts if jobs are missing or failing
Run this daily to ensure sync is working
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def check_sync_status():
    """Check if sync ran successfully in the last 24 hours"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get sync logs from last 24 hours
    yesterday = datetime.now() - timedelta(days=1)
    
    result = supabase.table('sync_logs')\
        .select('*')\
        .gte('started_at', yesterday.isoformat())\
        .order('started_at', desc=True)\
        .limit(1)\
        .execute()
    
    if not result.data:
        return False, "No sync run in the last 24 hours"
    
    latest_sync = result.data[0]
    
    if latest_sync['status'] != 'completed':
        return False, f"Latest sync failed with status: {latest_sync['status']}"
    
    return True, f"Sync completed successfully at {latest_sync['started_at']}"

def check_scheduler_jobs():
    """Check if critical scheduler jobs exist"""
    # Note: This requires heroku CLI to be available
    import subprocess
    
    try:
        result = subprocess.run(
            ['heroku', 'addons:info', 'scheduler', '--app', 'vespa-dashboard'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return False, "Could not check scheduler status"
            
        return True, "Scheduler addon is active"
    except Exception as e:
        return False, f"Error checking scheduler: {e}"

def send_alert(message):
    """Send alert via email or webhook"""
    print(f"ALERT: {message}")
    
    # If you have SendGrid configured, you could send an email here
    # Or send to a webhook/Slack channel
    
    # For now, just log it
    with open('sync_monitor.log', 'a') as f:
        f.write(f"{datetime.now().isoformat()}: {message}\n")

def main():
    print("=== SYNC MONITOR CHECK ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check sync status
    sync_ok, sync_msg = check_sync_status()
    print(f"Sync Status: {'✓' if sync_ok else '✗'} {sync_msg}")
    
    if not sync_ok:
        send_alert(f"Sync check failed: {sync_msg}")
    
    # Check scheduler
    scheduler_ok, scheduler_msg = check_scheduler_jobs()
    print(f"Scheduler Status: {'✓' if scheduler_ok else '✗'} {scheduler_msg}")
    
    if not scheduler_ok:
        send_alert(f"Scheduler check failed: {scheduler_msg}")
    
    # Return exit code
    return 0 if (sync_ok and scheduler_ok) else 1

if __name__ == "__main__":
    exit(main())




