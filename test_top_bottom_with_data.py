#!/usr/bin/env python3
"""
Test top/bottom questions with establishments that actually have data
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

def find_establishments_with_data():
    """Find establishments that actually have question statistics"""
    logging.info("Finding establishments with question data...")
    
    # Get establishments that have question statistics
    est_with_data = supabase.table('question_statistics')\
        .select('establishment_id')\
        .execute()
    
    if not est_with_data.data:
        logging.error("No question statistics found")
        return []
    
    # Get unique establishment IDs
    unique_est_ids = list(set([item['establishment_id'] for item in est_with_data.data]))
    
    # Get establishment details for these IDs
    establishments = []
    for est_id in unique_est_ids[:5]:  # Test with first 5
        est_info = supabase.table('establishments')\
            .select('id', 'name')\
            .eq('id', est_id)\
            .execute()
        
        if est_info.data:
            # Check if this establishment has students
            student_count = supabase.table('students')\
                .select('id', count='exact')\
                .eq('establishment_id', est_id)\
                .execute()
            
            if student_count.count > 0:
                establishments.append({
                    'id': est_info.data[0]['id'],
                    'name': est_info.data[0]['name'],
                    'student_count': student_count.count
                })
    
    logging.info(f"Found {len(establishments)} establishments with data")
    return establishments

def test_top_bottom_with_real_data():
    """Test top/bottom questions with establishments that have data"""
    logging.info("\n--- Testing Top/Bottom Questions with Real Data ---")
    
    # Find establishments with data
    establishments = find_establishments_with_data()
    
    if not establishments:
        logging.error("No establishments with data found")
        return False
    
    success_count = 0
    
    for est in establishments:
        est_id = est['id']
        est_name = est['name']
        student_count = est['student_count']
        
        logging.info(f"\nTesting: {est_name} ({student_count} students)")
        
        # Check what question statistics exist for this establishment
        q_stats = supabase.table('question_statistics')\
            .select('cycle', 'count')\
            .eq('establishment_id', est_id)\
            .execute()
        
        cycles_with_data = set([q['cycle'] for q in q_stats.data]) if q_stats.data else set()
        logging.info(f"  Has data for cycles: {sorted(cycles_with_data)}")
        
        # Test each cycle that has data
        for cycle in sorted(cycles_with_data):
            try:
                result = supabase.rpc('get_qla_top_bottom_questions', {
                    'p_establishment_id': est_id,
                    'p_cycle': cycle
                }).execute()
                
                if result.data:
                    top_5 = [q for q in result.data if q['performance_category'] == 'TOP_5']
                    bottom_5 = [q for q in result.data if q['performance_category'] == 'BOTTOM_5']
                    
                    logging.info(f"  Cycle {cycle}: ✓ {len(top_5)} top, {len(bottom_5)} bottom questions")
                    
                    if top_5:
                        best = top_5[0]
                        logging.info(f"    Best: {best['question_id']} (mean={best['mean']:.2f}, "
                                   f"national={best.get('national_mean', 'N/A')})")
                    
                    if bottom_5:
                        worst = bottom_5[0]
                        logging.info(f"    Worst: {worst['question_id']} (mean={worst['mean']:.2f}, "
                                   f"national={worst.get('national_mean', 'N/A')})")
                    
                    success_count += 1
                else:
                    logging.warning(f"  Cycle {cycle}: No results from function")
                    
            except Exception as e:
                logging.error(f"  Cycle {cycle} Error: {e}")
        
        # Stop after finding one successful establishment
        if success_count > 0:
            break
    
    if success_count > 0:
        logging.info(f"\n✓ Top/bottom questions working! Found data for {success_count} cycle(s)")
        return True
    else:
        logging.error("\n✗ No top/bottom questions found even for establishments with data")
        
        # Debug: Check the view directly
        logging.info("\nDebug: Checking qla_question_performance view directly...")
        view_data = supabase.table('qla_question_performance')\
            .select('performance_category', 'count')\
            .limit(10)\
            .execute()
        
        if view_data.data:
            categories = {}
            for item in view_data.data:
                cat = item['performance_category']
                categories[cat] = categories.get(cat, 0) + 1
            logging.info(f"View categories found: {categories}")
        
        return False

def main():
    logging.info("=" * 60)
    logging.info("TOP/BOTTOM QUESTIONS TEST WITH REAL DATA")
    logging.info("=" * 60)
    
    test_top_bottom_with_real_data()

if __name__ == "__main__":
    main()