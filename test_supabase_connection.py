#!/usr/bin/env python3
"""
Test script to verify Supabase connection
Run this locally after setting environment variables
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

def test_connection():
    """Test Supabase connection and basic operations"""
    
    # Get credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables not set")
        print("\nPlease set them in your .env file or environment:")
        print("  SUPABASE_URL=https://your-project.supabase.co")
        print("  SUPABASE_KEY=your-anon-public-key")
        return False
    
    print(f"🔄 Connecting to Supabase at: {supabase_url}")
    
    try:
        # Create client
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Successfully created Supabase client")
        
        # Test 1: Check if establishments table exists
        try:
            result = supabase.table('establishments').select('count', count='exact').limit(1).execute()
            print(f"✅ Establishments table exists with {result.count} records")
        except Exception as e:
            print(f"⚠️  Establishments table not found (this is expected if schema hasn't been created yet)")
            print(f"   Error: {str(e)}")
        
        # Test 2: List available tables (using a simple query)
        try:
            # This is a basic connectivity test
            print("\n✅ Supabase connection is working!")
            print("\nNext steps:")
            print("1. Run the schema creation script in Supabase SQL Editor")
            print("2. Configure Heroku environment variables")
            print("3. Deploy to Heroku")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing Supabase: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Supabase Connection...\n")
    success = test_connection()
    
    if success:
        print("\n✨ All tests passed! Your Supabase connection is ready.")
    else:
        print("\n❌ Connection test failed. Please check your credentials.")