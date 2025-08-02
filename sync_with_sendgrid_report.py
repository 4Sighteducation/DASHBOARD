#!/usr/bin/env python3
"""
Wrapper script to run sync and email the report via SendGrid
"""
import os
import subprocess
import requests
from datetime import datetime
import glob
import json

def run_sync():
    """Run the sync script and capture output"""
    try:
        # Run sync script
        result = subprocess.run(
            ['python', 'sync_knack_to_supabase.py'],
            capture_output=True,
            text=True
        )
        
        # Get the latest sync report
        sync_reports = glob.glob('sync_report_*.txt')
        if sync_reports:
            latest_report = max(sync_reports, key=os.path.getctime)
            with open(latest_report, 'r') as f:
                report_content = f.read()
        else:
            report_content = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            
        return result.returncode == 0, report_content
        
    except Exception as e:
        return False, f"Error running sync: {str(e)}"

def send_sendgrid_report(success, report_content):
    """Send email with sync report via SendGrid API"""
    # SendGrid configuration from environment variables
    sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@vespa.academy')
    to_email = os.getenv('REPORT_EMAIL', 'admin@vespa.academy')
    
    if not sendgrid_api_key:
        print("SendGrid API key not configured. Set SENDGRID_API_KEY env var.")
        print("\nSync Report:")
        print(report_content)
        return
    
    # Prepare email data
    subject = f"VESPA Sync {'✅ Success' if success else '❌ Failed'} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Format report for better readability
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: {'#28a745' if success else '#dc3545'};">
            VESPA Dashboard Sync Report
        </h2>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Status:</strong> <span style="color: {'#28a745' if success else '#dc3545'}; font-weight: bold;">
            {'SUCCESS' if success else 'FAILED'}
        </span></p>
        <hr>
        <pre style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;">
{report_content}
        </pre>
    </body>
    </html>
    """
    
    # SendGrid API request
    headers = {
        'Authorization': f'Bearer {sendgrid_api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'personalizations': [{
            'to': [{'email': to_email}]
        }],
        'from': {'email': from_email, 'name': 'VESPA Sync'},
        'subject': subject,
        'content': [
            {
                'type': 'text/plain',
                'value': f"VESPA Dashboard Sync Report\n{'='*50}\nDate: {datetime.now()}\nStatus: {'SUCCESS' if success else 'FAILED'}\n{'='*50}\n\n{report_content}"
            },
            {
                'type': 'text/html',
                'value': html_content
            }
        ]
    }
    
    # Send email
    try:
        response = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers=headers,
            data=json.dumps(data)
        )
        
        if response.status_code == 202:
            print(f"Report emailed to {to_email} via SendGrid")
        else:
            print(f"SendGrid error: {response.status_code} - {response.text}")
            print("\nSync Report:")
            print(report_content)
    except Exception as e:
        print(f"Failed to send email: {e}")
        print("\nSync Report:")
        print(report_content)

if __name__ == "__main__":
    success, report = run_sync()
    send_sendgrid_report(success, report)
    
    # Exit with appropriate code
    exit(0 if success else 1)