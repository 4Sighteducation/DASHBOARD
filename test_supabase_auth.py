#!/usr/bin/env python3
"""
Test Supabase authentication and determine which key type you're using
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Test which key you're using
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

print("=" * 60)
print("SUPABASE AUTHENTICATION TEST")
print("=" * 60)

print(f"\nSUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY length: {len(SUPABASE_KEY) if SUPABASE_KEY else 0}")
print(f"SUPABASE_SERVICE_KEY length: {len(SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else 0}")

# Check key characteristics
if SUPABASE_KEY:
    if "anon" in SUPABASE_KEY or len(SUPABASE_KEY) < 200:
        print("\n⚠️  SUPABASE_KEY appears to be an ANON key (public)")
    else:
        print("\n✓ SUPABASE_KEY might be a service role key")

if SUPABASE_SERVICE_KEY:
    if "service_role" in SUPABASE_SERVICE_KEY or len(SUPABASE_SERVICE_KEY) > 200:
        print("✓ SUPABASE_SERVICE_KEY appears to be a SERVICE ROLE key")
    else:
        print("⚠️  SUPABASE_SERVICE_KEY might not be a service role key")

# Test authentication
print("\n" + "-" * 60)
print("TESTING AUTHENTICATION:")
print("-" * 60)

# Test with regular key
if SUPABASE_KEY:
    try:
        client1 = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = client1.table('staff_admins').select('count', count='exact').limit(1).execute()
        print(f"\n✓ SUPABASE_KEY can SELECT from staff_admins")
        
        # Try an insert
        try:
            test_data = {'knack_id': 'test_123', 'email': 'test@example.com'}
            result = client1.table('staff_admins').insert(test_data).execute()
            # Delete the test record
            client1.table('staff_admins').delete().eq('knack_id', 'test_123').execute()
            print("✓ SUPABASE_KEY can INSERT into staff_admins")
        except Exception as e:
            print(f"✗ SUPABASE_KEY CANNOT INSERT: {str(e)[:100]}...")
            
    except Exception as e:
        print(f"✗ SUPABASE_KEY failed: {str(e)[:100]}...")

# Test with service role key
if SUPABASE_SERVICE_KEY:
    try:
        client2 = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = client2.table('staff_admins').select('count', count='exact').limit(1).execute()
        print(f"\n✓ SUPABASE_SERVICE_KEY can SELECT from staff_admins")
        
        # Try an insert
        try:
            test_data = {'knack_id': 'test_456', 'email': 'test2@example.com'}
            result = client2.table('staff_admins').insert(test_data).execute()
            # Delete the test record
            client2.table('staff_admins').delete().eq('knack_id', 'test_456').execute()
            print("✓ SUPABASE_SERVICE_KEY can INSERT into staff_admins")
        except Exception as e:
            print(f"✗ SUPABASE_SERVICE_KEY CANNOT INSERT: {str(e)[:100]}...")
            
    except Exception as e:
        print(f"✗ SUPABASE_SERVICE_KEY failed: {str(e)[:100]}...")

print("\n" + "=" * 60)
print("RECOMMENDATION:")
print("=" * 60)

if not SUPABASE_SERVICE_KEY:
    print("\n⚠️  You don't have SUPABASE_SERVICE_KEY set!")
    print("⚠️  Get it from Supabase Dashboard → Settings → API → service_role (secret)")
    print("⚠️  Add to .env file: SUPABASE_SERVICE_KEY=your_service_role_key_here")
else:
    print("\n✓ Use SUPABASE_SERVICE_KEY for sync operations")
    print("✓ Update your sync script to use: create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)")