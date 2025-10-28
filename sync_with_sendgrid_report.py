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
    subject = f"VESPA Sync {'Success' if success else 'FAILED'} - {datetime.now().strftime('%Y-%m-%d')}"
    
    # Enhanced HTML format with better styling
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 900px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, {'#28a745' if success else '#dc3545'} 0%, {'#20c997' if success else '#c82333'} 100%); color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .status-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; background-color: {'#d4edda' if success else '#f8d7da'}; color: {'#155724' if success else '#721c24'}; font-weight: bold; margin: 10px 0; }}
            .metric-box {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid {'#28a745' if success else '#dc3545'}; border-radius: 3px; }}
            .metric-label {{ color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #212529; }}
            .section {{ margin: 20px 0; }}
            .section-title {{ background-color: #e9ecef; padding: 10px; font-weight: bold; border-radius: 3px; margin: 15px 0 10px 0; }}
            pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; border: 1px solid #dee2e6; font-size: 12px; line-height: 1.5; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 2px solid #dee2e6; color: #6c757d; font-size: 12px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th {{ background-color: #e9ecef; padding: 10px; text-align: left; font-weight: bold; }}
            td {{ padding: 10px; border-bottom: 1px solid #dee2e6; }}
            .success {{ color: #28a745; }}
            .warning {{ color: #ffc107; }}
            .error {{ color: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">VESPA Dashboard Sync Report</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S UTC')}</p>
            </div>
            
            <div class="status-badge">
                {'SUCCESS - All Systems Operational' if success else 'FAILED - Action Required'}
            </div>
            
            <div class="section">
                <div class="section-title">Detailed Sync Report</div>
                <pre>{report_content}</pre>
            </div>
            
            <div class="footer">
                <p><strong>Sync Script Version:</strong> 2.0 (Multi-Year Support Enabled)</p>
                <p><strong>Scheduled Run:</strong> Daily at 2:00 AM UTC</p>
                <p><strong>Log File:</strong> sync_knack_to_supabase.log on Heroku</p>
                <p style="margin-top: 15px;"><em>This is an automated message from the VESPA Dashboard sync system.</em></p>
            </div>
        </div>
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