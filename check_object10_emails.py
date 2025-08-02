#!/usr/bin/env python3
"""
Check how many Object_10 records have missing/invalid emails
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

def check_emails():
    """Check Object_10 email validity"""
    print("=" * 80)
    print("OBJECT_10 EMAIL ANALYSIS")
    print("=" * 80)
    
    # Get first page to see total
    url = 'https://api.knack.com/v1/objects/object_10/records?page=1&rows_per_page=100'
    response = requests.get(url, headers=headers)
    data = response.json()
    
    total_records = data.get('total_records', 0)
    print(f"\nTotal Object_10 records: {total_records}")
    
    # Analyze sample
    stats = {
        'total': 0,
        'has_valid_email': 0,
        'no_email': 0,
        'empty_string': 0,
        'invalid_format': 0,
        'connected_to_object29': 0
    }
    
    # Check first 500 records
    for page in range(1, 6):
        response = requests.get(f'https://api.knack.com/v1/objects/object_10/records?page={page}&rows_per_page=100', headers=headers)
        data = response.json()
        
        for record in data.get('records', []):
            stats['total'] += 1
            
            # Check email (field_197)
            email_field = record.get('field_197_raw', {})
            
            # Process email similar to sync script
            if isinstance(email_field, dict):
                email_value = email_field.get('email', '')
                if isinstance(email_value, dict):
                    student_email = email_value.get('address', '') or email_value.get('email', '') or str(email_value)
                else:
                    student_email = str(email_value) if email_value else ''
            elif isinstance(email_field, str):
                student_email = email_field
            else:
                student_email = ''
            
            # Check validity (same as sync script)
            if not student_email:
                stats['no_email'] += 1
            elif not isinstance(student_email, str):
                stats['invalid_format'] += 1
            elif student_email == '{}':
                stats['invalid_format'] += 1
            elif student_email == '':
                stats['empty_string'] += 1
            else:
                stats['has_valid_email'] += 1
                
    print(f"\nAnalyzed {stats['total']} records:")
    print(f"  Valid emails: {stats['has_valid_email']} ({stats['has_valid_email']/stats['total']*100:.1f}%)")
    print(f"  No email field: {stats['no_email']} ({stats['no_email']/stats['total']*100:.1f}%)")
    print(f"  Empty string: {stats['empty_string']} ({stats['empty_string']/stats['total']*100:.1f}%)")
    print(f"  Invalid format: {stats['invalid_format']} ({stats['invalid_format']/stats['total']*100:.1f}%)")
    
    skipped = stats['total'] - stats['has_valid_email']
    print(f"\n🚨 SKIPPED: {skipped}/{stats['total']} ({skipped/stats['total']*100:.1f}%)")
    
    # Extrapolate to full dataset
    skip_rate = skipped / stats['total']
    estimated_skipped = int(total_records * skip_rate)
    print(f"\nEstimated across all {total_records} Object_10 records:")
    print(f"  ~{estimated_skipped} records would be skipped")
    print(f"  ~{total_records - estimated_skipped} students would be created")
    
    # Check how many Object_29 records connect to these
    print("\n" + "=" * 80)
    print("IMPACT ON OBJECT_29 SYNC:")
    print("=" * 80)
    
    # Get Object_29 count
    url = 'https://api.knack.com/v1/objects/object_29/records?page=1&rows_per_page=1'
    response = requests.get(url, headers=headers)
    data = response.json()
    
    total_object29 = data.get('total_records', 0)
    print(f"\nTotal Object_29 records: {total_object29}")
    
    if skip_rate > 0:
        print(f"\nIf {skip_rate*100:.1f}% of Object_10 records are skipped:")
        print(f"  Their connected Object_29 records would have NO student mapping")
        print(f"  Potentially affecting ~{int(total_object29 * skip_rate)} Object_29 records")
        print(f"  That's ~{int(total_object29 * skip_rate * 32 * 1.5):,} missing responses!")

if __name__ == "__main__":
    check_emails()