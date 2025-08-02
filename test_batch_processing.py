#!/usr/bin/env python3
"""
Test batch processing to verify it's working correctly
Specifically testing the batch size limits that caused issues before
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_batch_limits():
    """Test different batch sizes to find limits"""
    print("Testing Supabase Batch Processing Limits")
    print("=" * 80)
    
    # Test data
    test_sizes = [100, 500, 1000, 2000, 5000]
    
    for size in test_sizes:
        print(f"\nTesting batch size: {size}")
        
        # Create test data
        test_data = []
        for i in range(size):
            test_data.append({
                'student_id': 'a574cc5d-0bed-4257-8d63-501eeddd975b',  # Use a real student ID
                'cycle': 1,
                'question_id': f'TEST_{i}',
                'response_value': 5,
                'question_text': f'Test question {i}'
            })
        
        try:
            # Try to insert
            result = supabase.table('question_responses').upsert(
                test_data,
                on_conflict='student_id,cycle,question_id'
            ).execute()
            
            print(f"  ✅ Success! Inserted {len(result.data)} records")
            
            # Clean up test data
            cleanup = supabase.table('question_responses')\
                .delete()\
                .like('question_id', 'TEST_%')\
                .execute()
            
            print(f"  🧹 Cleaned up {len(cleanup.data)} test records")
            
        except Exception as e:
            print(f"  ❌ Failed at size {size}: {str(e)[:100]}")
            
            # Clean up any partial data
            try:
                cleanup = supabase.table('question_responses')\
                    .delete()\
                    .like('question_id', 'TEST_%')\
                    .execute()
            except:
                pass
            
            print(f"  This might be the batch size limit!")
            break

def check_current_batch_performance():
    """Check how the current 500-record batches are performing"""
    print("\n\nChecking Current Batch Performance")
    print("=" * 80)
    
    # Get timing data from recent syncs
    result = supabase.rpc('execute_sql', {
        'query': '''
            WITH sync_times AS (
                SELECT 
                    DATE_TRUNC('minute', created_at) as minute,
                    COUNT(*) as records_per_minute
                FROM question_responses
                WHERE created_at > NOW() - INTERVAL '1 day'
                GROUP BY DATE_TRUNC('minute', created_at)
            )
            SELECT 
                AVG(records_per_minute) as avg_per_minute,
                MAX(records_per_minute) as max_per_minute,
                MIN(records_per_minute) as min_per_minute
            FROM sync_times
            WHERE records_per_minute > 0
        '''
    }).execute()
    
    if result.data and result.data[0]['avg_per_minute']:
        stats = result.data[0]
        print(f"Average records per minute: {stats['avg_per_minute']:.0f}")
        print(f"Max records per minute: {stats['max_per_minute']}")
        print(f"Min records per minute: {stats['min_per_minute']}")
        
        # Estimate time for different amounts
        avg_per_min = float(stats['avg_per_minute'])
        print(f"\nAt current rate ({avg_per_min:.0f} records/min):")
        print(f"  17,000 records: {17000/avg_per_min:.1f} minutes")
        print(f"  100,000 records: {100000/avg_per_min:.1f} minutes") 
        print(f"  750,000 records: {750000/avg_per_min:.1f} minutes")

if __name__ == "__main__":
    # First check batch limits
    test_batch_limits()
    
    # Then check performance
    check_current_batch_performance()