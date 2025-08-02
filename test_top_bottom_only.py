#!/usr/bin/env python3
"""
Test only the top/bottom questions functionality
"""

import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_view_exists():
    """Check if the qla_question_performance view exists"""
    try:
        # Try to query the view
        result = supabase.table('qla_question_performance').select('*').limit(1).execute()
        logging.info("✓ View qla_question_performance exists")
        return True
    except Exception as e:
        logging.error(f"✗ View qla_question_performance not found: {e}")
        logging.info("  You need to run create_qla_optimized_views.sql")
        return False

def test_top_bottom_questions():
    """Test the top/bottom questions function"""
    logging.info("\n--- Testing Top/Bottom Questions ---")
    
    # Get a few establishments to test
    establishments = supabase.table('establishments').select('id', 'name').limit(3).execute()
    
    if not establishments.data:
        logging.error("No establishments found")
        return False
    
    success_count = 0
    
    for est in establishments.data:
        est_id = est['id']
        est_name = est['name']
        
        logging.info(f"\nTesting for: {est_name}")
        
        try:
            # Test for each cycle
            for cycle in [1, 2, 3]:
                result = supabase.rpc('get_qla_top_bottom_questions', {
                    'p_establishment_id': est_id,
                    'p_cycle': cycle
                }).execute()
                
                if result.data:
                    top_5 = [q for q in result.data if q['performance_category'] == 'TOP_5']
                    bottom_5 = [q for q in result.data if q['performance_category'] == 'BOTTOM_5']
                    
                    logging.info(f"  Cycle {cycle}: {len(top_5)} top, {len(bottom_5)} bottom questions")
                    
                    if top_5:
                        best = top_5[0]
                        logging.info(f"    Best: {best['question_id']} (mean={best['mean']}, national_mean={best['national_mean']})")
                    
                    if bottom_5:
                        worst = bottom_5[0]
                        logging.info(f"    Worst: {worst['question_id']} (mean={worst['mean']}, national_mean={worst['national_mean']})")
                    
                    if top_5 or bottom_5:
                        success_count += 1
                else:
                    logging.info(f"  Cycle {cycle}: No data")
                    
        except Exception as e:
            logging.error(f"  Error: {e}")
    
    if success_count > 0:
        logging.info(f"\n✓ Top/bottom questions working for {success_count} test cases")
        return True
    else:
        logging.error("\n✗ No top/bottom questions found for any establishment")
        return False

def check_question_rankings():
    """Debug: Check how questions are being ranked"""
    logging.info("\n--- Checking Question Rankings ---")
    
    # Get a sample establishment with question data
    est = supabase.table('establishments').select('id', 'name').limit(1).execute()
    if not est.data:
        return
    
    est_id = est.data[0]['id']
    est_name = est.data[0]['name']
    
    # Check question statistics for this establishment
    q_stats = supabase.table('question_statistics')\
        .select('question_id', 'mean', 'count')\
        .eq('establishment_id', est_id)\
        .eq('cycle', 1)\
        .order('mean', desc=True)\
        .limit(10)\
        .execute()
    
    if q_stats.data:
        logging.info(f"\nQuestion statistics for {est_name} (Cycle 1):")
        logging.info(f"Found {len(q_stats.data)} questions")
        for i, q in enumerate(q_stats.data[:5]):
            logging.info(f"  {i+1}. {q['question_id']}: mean={q['mean']}, n={q['count']}")
    else:
        logging.warning(f"No question statistics found for {est_name}")

def main():
    logging.info("=" * 60)
    logging.info("TOP/BOTTOM QUESTIONS FUNCTIONALITY TEST")
    logging.info("=" * 60)
    
    # Test 1: Check if view exists
    view_exists = test_view_exists()
    
    if view_exists:
        # Test 2: Test the function
        test_top_bottom_questions()
    else:
        logging.info("\nSkipping function test - view needs to be created first")
    
    # Debug check
    check_question_rankings()

if __name__ == "__main__":
    main()