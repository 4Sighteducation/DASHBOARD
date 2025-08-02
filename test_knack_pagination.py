#!/usr/bin/env python3
"""
Test Knack pagination to ensure we're getting all Object_29 records
"""

import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY,
    'Content-Type': 'application/json'
}

def test_pagination():
    """Test Object_29 pagination to ensure we get all records"""
    print("Testing Knack Object_29 Pagination")
    print("=" * 80)
    
    page = 1
    total_fetched = 0
    valid_records = 0
    invalid_records = 0
    pages_with_data = []
    
    while True:
        print(f"\nFetching page {page}...")
        
        url = f'https://api.knack.com/v1/objects/object_29/records'
        params = {
            'page': page,
            'rows_per_page': 500  # Match the sync script
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"  ❌ Error: Status {response.status_code}")
                break
                
            data = response.json()
            records = data.get('records', [])
            
            if not records:
                print(f"  No more records. Stopping at page {page}")
                break
            
            page_valid = 0
            page_invalid = 0
            
            for record in records:
                # Check if record has valid VESPA link (field_792)
                vespa_link = record.get('field_792_raw', [])
                if vespa_link and isinstance(vespa_link, list) and len(vespa_link) > 0:
                    page_valid += 1
                else:
                    page_invalid += 1
            
            total_fetched += len(records)
            valid_records += page_valid
            invalid_records += page_invalid
            
            pages_with_data.append({
                'page': page,
                'total': len(records),
                'valid': page_valid,
                'invalid': page_invalid
            })
            
            print(f"  Page {page}: {len(records)} records ({page_valid} valid, {page_invalid} without VESPA link)")
            
            # Show total pages if available
            if page == 1:
                total_pages = data.get('total_pages', 'Unknown')
                total_records = data.get('total_records', 'Unknown')
                print(f"  Total pages: {total_pages}")
                print(f"  Total records: {total_records}")
            
            page += 1
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"  ❌ Error on page {page}: {e}")
            break
    
    print("\n" + "=" * 80)
    print("PAGINATION SUMMARY:")
    print(f"Pages processed: {page - 1}")
    print(f"Total records fetched: {total_fetched:,}")
    print(f"Valid records (with VESPA link): {valid_records:,}")
    print(f"Invalid records (no VESPA link): {invalid_records:,}")
    
    # Show distribution
    if len(pages_with_data) > 10:
        print(f"\nFirst 5 pages:")
        for p in pages_with_data[:5]:
            print(f"  Page {p['page']}: {p['total']} records ({p['valid']} valid)")
        
        print(f"\nLast 5 pages:")
        for p in pages_with_data[-5:]:
            print(f"  Page {p['page']}: {p['total']} records ({p['valid']} valid)")
    
    # Check if we might be hitting a limit
    if valid_records < 20000 and total_fetched > 30000:
        print("\n⚠️  WARNING: Low percentage of valid records!")
        print("   Many Object_29 records don't have VESPA links (field_792)")
        print("   This explains why only ~17k records are synced")

if __name__ == "__main__":
    test_pagination()