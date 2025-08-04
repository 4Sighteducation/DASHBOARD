#!/usr/bin/env python3
"""
Check which Supabase key is being used
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

print("Checking Supabase keys configuration:")
print("=" * 60)

if SUPABASE_KEY:
    # Check key characteristics
    key_prefix = SUPABASE_KEY[:20]
    print(f"SUPABASE_KEY is set (starts with: {key_prefix}...)")
    
    # Service role keys typically contain 'service_role' in the JWT payload
    # Anon keys typically contain 'anon' in the JWT payload
    if 'service_role' in SUPABASE_KEY:
        print("  → Appears to be a SERVICE ROLE key (good for sync)")
    elif 'anon' in SUPABASE_KEY:
        print("  → Appears to be an ANON key (will hit RLS policies)")
    else:
        print("  → Key type unclear")
else:
    print("SUPABASE_KEY is NOT set")

if SUPABASE_SERVICE_ROLE_KEY:
    key_prefix = SUPABASE_SERVICE_ROLE_KEY[:20]
    print(f"\nSUPABASE_SERVICE_ROLE_KEY is set (starts with: {key_prefix}...)")
else:
    print("\nSUPABASE_SERVICE_ROLE_KEY is NOT set")

print("\nRecommendation:")
print("-" * 60)
print("For syncing, you should use the SERVICE ROLE key which bypasses RLS.")
print("Either:")
print("1. Set SUPABASE_KEY to your service role key, OR")
print("2. Set SUPABASE_SERVICE_ROLE_KEY and update the sync script to use it")
print("\nYou can find both keys in your Supabase project settings:")