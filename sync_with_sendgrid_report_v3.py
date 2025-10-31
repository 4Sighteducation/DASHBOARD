#!/usr/bin/env python3
"""
Wrapper script for NEW sync (v3.0) with SendGrid email reporting
Replaces: sync_with_sendgrid_report.py (v2.0 wrapper)
"""
import os
import subprocess
from datetime import datetime

def run_sync():
    """Run the NEW v3.0 sync script"""
    try:
        print("Starting VESPA Sync v3.0 (Current Year Only)...")
        print("Expected duration: 6-10 minutes\n")
        
        # Run the NEW sync script
        result = subprocess.run(
            ['python', 'sync_current_year_only.py'],
            capture_output=False,  # Show real-time output
            text=True
        )
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running sync: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_sync()
    
    # Email is now sent automatically by sync_current_year_only.py
    # No wrapper email logic needed!
    
    print("\n" + "="*80)
    if success:
        print("✅ SYNC COMPLETED - Email report sent automatically")
    else:
        print("⚠️ SYNC HAD ISSUES - Check email for details")
    print("="*80)
    
    exit(0 if success else 1)

