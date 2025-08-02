#!/usr/bin/env python3
"""
Run FULL sync using the OPTIMIZED script that actually works!
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the WORKING optimized version
from sync_knack_to_supabase_optimized import (
    supabase, logging, SyncCheckpoint,
    sync_establishments, sync_students_and_vespa_scores,
    sync_question_responses, sync_staff_admins,
    sync_super_users, calculate_statistics,
    keep_system_awake
)

def main():
    """Run the full sync using the optimized functions"""
    print("=" * 60)
    print("FULL SYNC using OPTIMIZED (working) version")
    print("=" * 60)
    
    # Keep system awake
    keep_system_awake()
    
    # Start fresh
    checkpoint = SyncCheckpoint()
    if Path('sync_checkpoint.pkl').exists():
        Path('sync_checkpoint.pkl').unlink()
    
    try:
        # 1. Sync establishments
        print("\n1. Syncing establishments...")
        sync_establishments(checkpoint)
        
        # 2. Sync students and VESPA scores
        print("\n2. Syncing students and VESPA scores...")
        sync_students_and_vespa_scores(checkpoint)
        
        # 3. Sync question responses
        print("\n3. Syncing question responses...")
        sync_question_responses(checkpoint)
        
        # 4. Sync staff admins
        print("\n4. Syncing staff admins...")
        sync_staff_admins(checkpoint)
        
        # 5. Sync super users
        print("\n5. Syncing super users...")
        sync_super_users(checkpoint)
        
        # 6. Calculate statistics
        print("\n6. Calculating statistics...")
        calculate_statistics(checkpoint)
        
        print("\n✨ Full sync complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logging.error(f"Full sync failed: {e}")
    finally:
        # Clean up checkpoint
        if Path('sync_checkpoint.pkl').exists():
            Path('sync_checkpoint.pkl').unlink()

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the sync
    main()