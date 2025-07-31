#!/usr/bin/env python3
"""
Check the status of the Knack to Supabase sync
Provides detailed information about the sync progress and data health
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from pathlib import Path
import pickle

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Checkpoint file
CHECKPOINT_FILE = Path('sync_checkpoint.pkl')

def format_number(n):
    """Format large numbers with commas"""
    return f"{n:,}"

def check_checkpoint():
    """Check if there's a saved checkpoint"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                checkpoint = pickle.load(f)
            print("\n📌 CHECKPOINT FOUND:")
            print(f"  - Establishments synced: {'✅' if checkpoint.establishments_synced else '❌'}")
            print(f"  - VESPA page: {checkpoint.vespa_page}")
            print(f"  - Students processed: {format_number(len(checkpoint.students_processed))}")
            print(f"  - Psychometric page: {checkpoint.psychometric_page}")
            print(f"  - Statistics calculated: {'✅' if checkpoint.statistics_calculated else '❌'}")
            print(f"  - Last update: {checkpoint.last_update}")
            return True
        except Exception as e:
            print(f"\n⚠️  Error reading checkpoint: {e}")
    else:
        print("\n✅ No checkpoint found - sync completed or not started")
    return False

def check_sync_logs():
    """Check recent sync logs"""
    print("\n📊 RECENT SYNC LOGS:")
    
    # Get last 5 sync logs
    logs = supabase.table('sync_logs')\
        .select('*')\
        .order('started_at', desc=True)\
        .limit(5)\
        .execute()
    
    if not logs.data:
        print("  No sync logs found")
        return
    
    for log in logs.data:
        status_emoji = {
            'completed': '✅',
            'started': '🔄',
            'failed': '❌',
            'interrupted': '⏸️'
        }.get(log['status'], '❓')
        
        print(f"\n  {status_emoji} {log['sync_type']} - {log['status'].upper()}")
        print(f"     Started: {log['started_at']}")
        if log.get('completed_at'):
            print(f"     Completed: {log['completed_at']}")
        if log.get('metadata'):
            meta = log['metadata']
            if 'duration_seconds' in meta:
                duration = meta['duration_seconds']
                print(f"     Duration: {int(duration//60)}m {int(duration%60)}s")
            if 'total_students' in meta:
                print(f"     Students: {format_number(meta.get('total_students', 0))}")
                print(f"     VESPA Scores: {format_number(meta.get('total_vespa_scores', 0))}")
                print(f"     Question Responses: {format_number(meta.get('total_question_responses', 0))}")
        if log.get('error_message'):
            print(f"     Error: {log['error_message']}")

def check_data_counts():
    """Check current data counts in Supabase"""
    print("\n📈 CURRENT DATA COUNTS:")
    
    tables = [
        ('establishments', 'Establishments'),
        ('students', 'Students'),
        ('vespa_scores', 'VESPA Scores'),
        ('student_vespa_progress', 'Student Progress'),
        ('question_responses', 'Question Responses'),
        ('school_statistics', 'School Statistics'),
        ('comparative_metrics', 'Comparative Metrics')
    ]
    
    for table_name, display_name in tables:
        try:
            count_result = supabase.table(table_name).select('*', count='exact', head=True).execute()
            count = count_result.count if hasattr(count_result, 'count') else 0
            print(f"  - {display_name}: {format_number(count)}")
        except Exception as e:
            print(f"  - {display_name}: Error - {str(e)}")

def check_data_health():
    """Run data health checks"""
    print("\n🏥 DATA HEALTH CHECKS:")
    
    try:
        # Check for students without establishments
        orphan_students = supabase.table('students')\
            .select('id', count='exact', head=True)\
            .is_('establishment_id', 'null')\
            .execute()
        orphan_count = orphan_students.count if hasattr(orphan_students, 'count') else 0
        
        if orphan_count > 0:
            print(f"  ⚠️  Students without establishments: {format_number(orphan_count)}")
        else:
            print(f"  ✅ All students have establishments")
        
        # Check for VESPA scores without academic year
        no_year = supabase.table('vespa_scores')\
            .select('id', count='exact', head=True)\
            .is_('academic_year', 'null')\
            .execute()
        no_year_count = no_year.count if hasattr(no_year, 'count') else 0
        
        if no_year_count > 0:
            print(f"  ⚠️  VESPA scores without academic year: {format_number(no_year_count)}")
        else:
            print(f"  ✅ All VESPA scores have academic year")
        
        # Check unique student-cycle combinations
        vespa_data = supabase.table('vespa_scores').select('student_id', 'cycle').execute()
        unique_combos = len(set((v['student_id'], v['cycle']) for v in vespa_data.data))
        print(f"  ℹ️  Unique student-cycle combinations: {format_number(unique_combos)}")
        
        # Check average scores per student
        student_count = supabase.table('students').select('id', count='exact', head=True).execute()
        total_students = student_count.count if hasattr(student_count, 'count') else 1
        
        vespa_count = supabase.table('vespa_scores').select('id', count='exact', head=True).execute()
        total_scores = vespa_count.count if hasattr(vespa_count, 'count') else 0
        
        avg_scores_per_student = total_scores / total_students if total_students > 0 else 0
        print(f"  ℹ️  Average VESPA scores per student: {avg_scores_per_student:.1f}")
        
    except Exception as e:
        print(f"  ❌ Error running health checks: {e}")

def estimate_remaining_time():
    """Estimate remaining sync time based on checkpoint"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'rb') as f:
                checkpoint = pickle.load(f)
            
            # Get last completed sync duration from logs
            completed_syncs = supabase.table('sync_logs')\
                .select('metadata')\
                .eq('status', 'completed')\
                .order('started_at', desc=True)\
                .limit(1)\
                .execute()
            
            if completed_syncs.data and completed_syncs.data[0].get('metadata'):
                last_duration = completed_syncs.data[0]['metadata'].get('duration_seconds', 0)
                
                # Estimate based on VESPA page progress (assuming most time is spent here)
                if checkpoint.vespa_page > 1:
                    # Try to estimate total pages from Knack
                    # This is a rough estimate - you might need to adjust based on your data
                    estimated_total_pages = 50  # Adjust based on your typical data size
                    progress_percent = (checkpoint.vespa_page / estimated_total_pages) * 100
                    
                    if progress_percent < 100:
                        time_elapsed = (datetime.now() - checkpoint.last_update).total_seconds()
                        estimated_total_time = (time_elapsed / progress_percent) * 100
                        estimated_remaining = estimated_total_time - time_elapsed
                        
                        print(f"\n⏱️  ESTIMATED PROGRESS:")
                        print(f"  - Progress: ~{progress_percent:.1f}%")
                        print(f"  - Estimated remaining time: ~{int(estimated_remaining//60)}m")
                        print(f"  - Note: This is a rough estimate")
                    
        except Exception as e:
            print(f"\n⚠️  Could not estimate remaining time: {e}")

def main():
    """Main function to check sync status"""
    print("=" * 50)
    print("KNACK TO SUPABASE SYNC STATUS CHECK")
    print("=" * 50)
    
    # Check if sync is in progress
    has_checkpoint = check_checkpoint()
    
    # Check sync logs
    check_sync_logs()
    
    # Check data counts
    check_data_counts()
    
    # Check data health
    check_data_health()
    
    # Estimate remaining time if checkpoint exists
    if has_checkpoint:
        estimate_remaining_time()
        print("\n💡 TIP: Run 'python sync_knack_to_supabase_optimized.py' to resume the sync")
    
    print("\n" + "=" * 50)
    
    # Provide recommendations
    print("\n📋 RECOMMENDATIONS:")
    
    if has_checkpoint:
        print("  1. Resume the sync by running: python sync_knack_to_supabase_optimized.py")
        print("  2. The sync will continue from where it left off")
        print("  3. Keep your computer awake during the sync")
    else:
        # Check if data looks complete
        vespa_count = supabase.table('vespa_scores').select('id', count='exact', head=True).execute()
        total_scores = vespa_count.count if hasattr(vespa_count, 'count') else 0
        
        if total_scores < 5000:  # Adjust threshold based on expected data
            print("  1. Data counts seem low - consider running a full sync")
            print("  2. Run: python sync_knack_to_supabase_optimized.py")
        else:
            print("  ✅ Sync appears to be complete!")
            print("  1. Run the Flask app to test the dashboard")
            print("  2. Monitor performance and data accuracy")

if __name__ == "__main__":
    main()