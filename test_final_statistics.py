#!/usr/bin/env python3
"""
Final test to verify all statistics are working correctly
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

def test_all_statistics():
    """Comprehensive test of all statistics"""
    
    logging.info("=" * 60)
    logging.info("FINAL STATISTICS VERIFICATION")
    logging.info("=" * 60)
    
    # 1. Check school statistics
    school_stats = supabase.table('school_statistics').select('count').execute()
    school_count = len(school_stats.data) if school_stats.data else 0
    logging.info(f"\n1. School Statistics: {school_count} records")
    
    if school_count > 0:
        # Sample by element
        for element in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
            sample = supabase.table('school_statistics')\
                .select('mean', 'count')\
                .eq('element', element)\
                .eq('cycle', 1)\
                .limit(1)\
                .execute()
            if sample.data:
                logging.info(f"   {element}: mean={sample.data[0]['mean']}, n={sample.data[0]['count']}")
    
    # 2. Check question statistics
    question_stats = supabase.table('question_statistics').select('count').execute()
    question_count = len(question_stats.data) if question_stats.data else 0
    logging.info(f"\n2. Question Statistics: {question_count} records")
    
    # Check for distribution data
    sample_q = supabase.table('question_statistics')\
        .select('question_id', 'mean', 'std_dev', 'distribution')\
        .limit(3)\
        .execute()
    
    if sample_q.data:
        for q in sample_q.data:
            logging.info(f"   {q['question_id']}: mean={q['mean']}, std={q['std_dev']}, dist={q['distribution']}")
    
    # 3. Check top/bottom questions
    logging.info(f"\n3. Top/Bottom Questions Test:")
    est = supabase.table('establishments').select('id', 'name').limit(1).execute()
    if est.data:
        est_id = est.data[0]['id']
        est_name = est.data[0]['name']
        
        result = supabase.rpc('get_qla_top_bottom_questions', {
            'p_establishment_id': est_id,
            'p_cycle': 1
        }).execute()
        
        if result.data:
            top_5 = [q for q in result.data if q['performance_category'] == 'TOP_5']
            bottom_5 = [q for q in result.data if q['performance_category'] == 'BOTTOM_5']
            
            logging.info(f"   School: {est_name}")
            logging.info(f"   Top 5 questions found: {len(top_5)}")
            logging.info(f"   Bottom 5 questions found: {len(bottom_5)}")
            
            if top_5:
                logging.info(f"   Best performing: {top_5[0]['question_id']} (mean={top_5[0]['mean']})")
            if bottom_5:
                logging.info(f"   Worst performing: {bottom_5[0]['question_id']} (mean={bottom_5[0]['mean']})")
        else:
            logging.warning("   No top/bottom questions found - check if qla_question_performance view exists")
    
    # 4. Check national statistics
    national_stats = supabase.table('national_statistics').select('count').execute()
    national_count = len(national_stats.data) if national_stats.data else 0
    logging.info(f"\n4. National Statistics: {national_count} records")
    
    national_q_stats = supabase.table('national_question_statistics').select('count').execute()
    national_q_count = len(national_q_stats.data) if national_q_stats.data else 0
    logging.info(f"   National Question Statistics: {national_q_count} records")
    
    # Summary
    logging.info("\n" + "=" * 60)
    logging.info("SUMMARY")
    logging.info("=" * 60)
    
    all_good = school_count > 0 and question_count > 0 and national_q_count > 0
    
    if all_good:
        logging.info("✅ Core statistics are ready!")
        if len(result.data if 'result' in locals() else []) == 0:
            logging.info("⚠️  Top/bottom questions view needs to be created")
            logging.info("    Run create_qla_optimized_views.sql in Supabase")
    else:
        logging.info("❌ Some statistics are missing")
    
    logging.info(f"\nTotal statistics records:")
    logging.info(f"  School: {school_count}")
    logging.info(f"  Questions: {question_count}")  
    logging.info(f"  National: {national_count}")
    logging.info(f"  National Questions: {national_q_count}")
    
    return all_good

if __name__ == "__main__":
    test_all_statistics()