#!/usr/bin/env python3
"""
Fix trusts by creating trust records and linking establishments
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_trusts_and_link():
    """Create trust records and link establishments"""
    
    # First, create the E-ACT trust if it doesn't exist
    print("Creating E-ACT trust record...")
    
    # Check if E-ACT trust already exists
    existing = supabase.table('trusts').select('id').eq('name', 'E-ACT').execute()
    
    if not existing.data:
        # Create the trust
        trust_result = supabase.table('trusts').insert({
            'name': 'E-ACT'
        }).execute()
        trust_id = trust_result.data[0]['id']
        print(f"Created E-ACT trust with ID: {trust_id}")
    else:
        trust_id = existing.data[0]['id']
        print(f"E-ACT trust already exists with ID: {trust_id}")
    
    # Now update establishments with this trust
    print("\nLinking establishments to E-ACT trust...")
    
    # Get all establishments from Knack that have E-ACT as their trust
    from sync_knack_to_supabase import fetch_all_knack_records, OBJECT_KEYS
    
    # Filter for establishments with E-ACT trust
    filters = [
        {
            'field': 'field_3480',
            'operator': 'is',
            'value': 'E-ACT'
        }
    ]
    
    establishments = fetch_all_knack_records(OBJECT_KEYS['establishments'], filters=filters)
    print(f"Found {len(establishments)} establishments in E-ACT trust")
    
    # Update each establishment
    updated = 0
    for est in establishments:
        try:
            # Update the establishment with the trust UUID
            supabase.table('establishments').update({
                'trust_id': trust_id
            }).eq('knack_id', est['id']).execute()
            updated += 1
            print(f"  Updated: {est.get('field_44', 'Unknown')}")
        except Exception as e:
            print(f"  Error updating {est.get('field_44', 'Unknown')}: {e}")
    
    print(f"\nSuccessfully linked {updated} establishments to E-ACT trust")
    
    # Verify the results
    linked = supabase.table('establishments').select('id', 'name', 'trust_id').eq('trust_id', trust_id).execute()
    print(f"\nVerification: {len(linked.data)} establishments now linked to E-ACT")
    for est in linked.data:
        print(f"  - {est['name']}")

if __name__ == "__main__":
    create_trusts_and_link()