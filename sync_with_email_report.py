#!/usr/bin/env python3
"""
Wrapper script to run sync and email the report
"""
import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import glob

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

def send_email_report(success, report_content):
    """Send email with sync report"""
    # Email configuration from environment variables
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    recipient_email = os.getenv('REPORT_EMAIL', smtp_username)
    
    if not smtp_username or not smtp_password:
        print("Email credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD env vars.")
        print("\nSync Report:")
        print(report_content)
        return
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = recipient_email
    msg['Subject'] = f"VESPA Sync {'✅ Success' if success else '❌ Failed'} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Add report content
    body = f"""
VESPA Dashboard Sync Report
{'='*50}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: {'SUCCESS' if success else 'FAILED'}
{'='*50}

{report_content}
"""
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Send email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        print(f"Report emailed to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        print("\nSync Report:")
        print(report_content)

if __name__ == "__main__":
    success, report = run_sync()
    send_email_report(success, report)