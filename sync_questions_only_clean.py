#!/usr/bin/env python3
"""
Sync ONLY question responses using the PROVEN approach from quick_sync
This CLEARS existing data first, then syncs fresh - exactly what worked before!
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the OPTIMIZED version that we KNOW works
from sync_knack_to_supabase_optimized import (
    supabase, logging, SyncCheckpoint,
    sync_question_responses, keep_system_awake
)

def main():
    print("=" * 60)
    print("QUESTION RESPONSES SYNC - CLEAN START")
    print("Using the approach that successfully synced 750k records")
    print("=" * 60)
    
    # Keep system awake
    keep_system_awake()
    
    # CRITICAL: Clear existing question responses first (this is what made it work!)
    print("\n1. Clearing existing question responses...")
    try:
        result = supabase.table('question_responses').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print("✅ Cleared existing question responses")
    except Exception as e:
        print(f"❌ Error clearing: {e}")
        return
    
    # Clear checkpoint for fresh start
    if Path('sync_checkpoint.pkl').exists():
        Path('sync_checkpoint.pkl').unlink()
    
    # Create checkpoint with other syncs marked as done
    checkpoint = SyncCheckpoint()
    checkpoint.establishments_synced = True
    checkpoint.vespa_page = 999  # Skip VESPA sync
    checkpoint.total_students = 24971  # Already synced
    checkpoint.total_vespa_scores = 28096  # Already synced
    
    try:
        print("\n2. Syncing question responses from Object_29...")
        print("   Expected: ~754k records based on your calculations")
        print("   Batch size: 1000 (what worked before)")
        
        success = sync_question_responses(checkpoint)
        
        if success:
            print(f"\n✅ SUCCESS! Synced {checkpoint.total_responses} question responses")
        else:
            print("\n❌ Sync failed")
            
    except KeyboardInterrupt:
        print("\n⚠️  Sync interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logging.error(f"Sync failed: {e}")
    finally:
        # Clean up
        if Path('sync_checkpoint.pkl').exists():
            Path('sync_checkpoint.pkl').unlink()

if __name__ == "__main__":
    load_dotenv()
    main()