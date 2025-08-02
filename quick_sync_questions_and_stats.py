#!/usr/bin/env python3
"""
Quick script to sync just question responses and recalculate statistics
Since students and VESPA scores are already synced
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the fixed sync functions
from sync_knack_to_supabase_optimized import (
    supabase, logging, SyncCheckpoint,
    sync_question_responses, calculate_statistics
)

# First, clear existing question responses to avoid duplicates
print("Clearing existing question responses...")
try:
    supabase.table('question_responses').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print("✅ Cleared existing question responses")
except Exception as e:
    print(f"❌ Error clearing question responses: {e}")

# Also clear any existing checkpoint for fresh start
if Path('sync_checkpoint.pkl').exists():
    Path('sync_checkpoint.pkl').unlink()
    print("✅ Cleared checkpoint file")

def main():
    """Run just the question responses and statistics sync"""
    print("=" * 60)
    print("QUICK SYNC: Question Responses & Statistics")
    print("=" * 60)
    
    # Create a minimal checkpoint
    checkpoint = SyncCheckpoint()
    checkpoint.establishments_synced = True
    checkpoint.vespa_page = 999  # Skip VESPA sync
    checkpoint.total_students = 24971  # Already synced
    checkpoint.total_vespa_scores = 28096  # Already synced
    
    try:
        print("\n1. Syncing question responses from Object_29...")
        print("   Using field_792 to connect to Object_10 records")
        success = sync_question_responses(checkpoint)
        
        if success:
            print(f"\n   ✅ Synced {checkpoint.total_responses} question responses")
        else:
            print("\n   ❌ Failed to sync question responses")
            return
        
        print("\n2. Calculating statistics...")
        success = calculate_statistics(checkpoint)
        
        if success:
            print("\n   ✅ Statistics calculated successfully")
        else:
            print("\n   ❌ Failed to calculate statistics")
            
        # Clean up checkpoint
        if Path('sync_checkpoint.pkl').exists():
            Path('sync_checkpoint.pkl').unlink()
            
        print("\n✨ Quick sync complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logging.error(f"Quick sync failed: {e}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the sync
    main()