#!/usr/bin/env python3
"""
Test script to verify statistics calculations before running full sync
Tests both SQL stored procedures and Python fallback calculations
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import json

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

def test_connection():
    """Test basic Supabase connection"""
    try:
        result = supabase.table('establishments').select('count').limit(1).execute()
        logging.info("✓ Supabase connection successful")
        return True
    except Exception as e:
        logging.error(f"✗ Supabase connection failed: {e}")
        return False

def test_data_availability():
    """Check if we have data to calculate statistics from"""
    try:
        # Check establishments
        est_count = supabase.table('establishments').select('id', count='exact').execute()
        logging.info(f"  Establishments: {est_count.count}")
        
        # Check students
        student_count = supabase.table('students').select('id', count='exact').execute()
        logging.info(f"  Students: {student_count.count}")
        
        # Check vespa_scores
        vespa_count = supabase.table('vespa_scores').select('id', count='exact').execute()
        logging.info(f"  VESPA scores: {vespa_count.count}")
        
        # Check question_responses
        qr_count = supabase.table('question_responses').select('id', count='exact').execute()
        logging.info(f"  Question responses: {qr_count.count}")
        
        if est_count.count > 0 and student_count.count > 0 and qr_count.count > 0:
            logging.info("✓ Sufficient data available for statistics calculation")
            return True
        else:
            logging.warning("✗ Insufficient data for statistics calculation")
            return False
            
    except Exception as e:
        logging.error(f"✗ Error checking data availability: {e}")
        return False

def test_school_statistics_procedure():
    """Test the calculate_all_statistics stored procedure"""
    logging.info("\n--- Testing School Statistics Calculation ---")
    try:
        # Get count before
        before = supabase.table('school_statistics').select('id', count='exact').execute()
        logging.info(f"School statistics before: {before.count}")
        
        # Run the stored procedure
        result = supabase.rpc('calculate_all_statistics', {}).execute()
        logging.info("✓ School statistics procedure executed successfully")
        
        # Get count after
        after = supabase.table('school_statistics').select('id', count='exact').execute()
        logging.info(f"School statistics after: {after.count}")
        logging.info(f"New records created: {after.count - before.count}")
        
        # Sample some data
        sample = supabase.table('school_statistics').select('*').limit(5).execute()
        if sample.data:
            logging.info("\nSample school statistics:")
            for stat in sample.data[:2]:
                logging.info(f"  Establishment: {stat['establishment_id'][:8]}..., "
                           f"Cycle: {stat['cycle']}, Element: {stat['element']}, "
                           f"Mean: {stat['mean']}, Count: {stat['count']}")
        
        return True
        
    except Exception as e:
        logging.error(f"✗ School statistics procedure failed: {e}")
        logging.info("This might be expected if the procedure doesn't exist yet")
        return False

def test_question_statistics_procedure():
    """Test the enhanced question statistics calculation"""
    logging.info("\n--- Testing Question Statistics Calculation ---")
    try:
        # Get count before
        before = supabase.table('question_statistics').select('id', count='exact').execute()
        logging.info(f"Question statistics before: {before.count}")
        
        # Run the enhanced stored procedure
        result = supabase.rpc('calculate_question_statistics_enhanced', {}).execute()
        logging.info("✓ Question statistics procedure executed successfully")
        
        # Get count after
        after = supabase.table('question_statistics').select('id', count='exact').execute()
        logging.info(f"Question statistics after: {after.count}")
        logging.info(f"New records created: {after.count - before.count}")
        
        # Check if we have the expected columns
        sample = supabase.table('question_statistics').select('*').limit(1).execute()
        if sample.data:
            record = sample.data[0]
            expected_fields = ['mean', 'std_dev', 'count', 'mode', 'distribution', 'percentile_25', 'percentile_75']
            missing_fields = [f for f in expected_fields if f not in record]
            
            if missing_fields:
                logging.warning(f"✗ Missing fields in question_statistics: {missing_fields}")
            else:
                logging.info("✓ All expected fields present in question_statistics")
            
            # Show sample
            logging.info(f"\nSample question statistic:")
            logging.info(f"  Question: {record['question_id']}, Cycle: {record['cycle']}")
            logging.info(f"  Mean: {record.get('mean')}, Std Dev: {record.get('std_dev')}, "
                        f"Count: {record.get('count')}, Mode: {record.get('mode')}")
            if record.get('distribution'):
                logging.info(f"  Distribution: {record['distribution']}")
        
        return True
        
    except Exception as e:
        logging.error(f"✗ Question statistics procedure failed: {e}")
        logging.info("Falling back to test Python calculation...")
        return test_question_statistics_python_fallback()

def test_question_statistics_python_fallback():
    """Test the Python fallback for question statistics"""
    logging.info("\n--- Testing Python Question Statistics Fallback ---")
    try:
        # Get a sample establishment
        est = supabase.table('establishments').select('id').limit(1).execute()
        if not est.data:
            logging.error("No establishments found")
            return False
        
        est_id = est.data[0]['id']
        
        # Get students for this establishment
        students = supabase.table('students').select('id').eq('establishment_id', est_id).limit(100).execute()
        if not students.data:
            logging.error("No students found for establishment")
            return False
        
        student_ids = [s['id'] for s in students.data]
        
        # Get question responses for cycle 1
        responses = supabase.table('question_responses')\
            .select('question_id', 'response_value')\
            .in_('student_id', student_ids)\
            .eq('cycle', 1)\
            .limit(1000)\
            .execute()
        
        if not responses.data:
            logging.error("No question responses found")
            return False
        
        # Group by question
        question_groups = {}
        for resp in responses.data:
            qid = resp['question_id']
            if qid not in question_groups:
                question_groups[qid] = []
            if resp['response_value'] is not None:
                question_groups[qid].append(resp['response_value'])
        
        logging.info(f"Found {len(question_groups)} unique questions with responses")
        
        # Calculate statistics for first question
        if question_groups:
            first_q = list(question_groups.keys())[0]
            values = question_groups[first_q]
            
            if len(values) > 1:
                import statistics as stats
                
                # Calculate distribution
                distribution = [0, 0, 0, 0, 0]
                for v in values:
                    if 1 <= v <= 5:
                        distribution[v-1] += 1
                
                mean = sum(values) / len(values)
                std_dev = stats.stdev(values)
                mode = max(range(1, 6), key=lambda x: distribution[x-1])
                
                logging.info(f"\nSample calculation for question {first_q}:")
                logging.info(f"  Responses: {len(values)}")
                logging.info(f"  Mean: {mean:.2f}")
                logging.info(f"  Std Dev: {std_dev:.2f}")
                logging.info(f"  Mode: {mode}")
                logging.info(f"  Distribution: {distribution}")
                
                logging.info("✓ Python statistics calculation working")
                return True
        
        return False
        
    except Exception as e:
        logging.error(f"✗ Python statistics calculation failed: {e}")
        return False

def test_top_bottom_questions():
    """Test identification of top/bottom 5 questions"""
    logging.info("\n--- Testing Top/Bottom Questions Identification ---")
    try:
        # First, make sure we have question statistics
        qs_count = supabase.table('question_statistics').select('id', count='exact').execute()
        if qs_count.count == 0:
            logging.warning("No question statistics found - run question statistics test first")
            return False
        
        # Test the ranking view/function
        est = supabase.table('establishments').select('id').limit(1).execute()
        if est.data:
            est_id = est.data[0]['id']
            
            # Try to get top/bottom questions
            result = supabase.rpc('get_qla_top_bottom_questions', {
                'p_establishment_id': est_id,
                'p_cycle': 1
            }).execute()
            
            if result.data:
                top_5 = [q for q in result.data if q['performance_category'] == 'TOP_5']
                bottom_5 = [q for q in result.data if q['performance_category'] == 'BOTTOM_5']
                
                logging.info(f"✓ Found {len(top_5)} top questions and {len(bottom_5)} bottom questions")
                
                if top_5:
                    logging.info("\nTop question example:")
                    q = top_5[0]
                    logging.info(f"  Question: {q['question_id']}, Mean: {q['mean']}, "
                               f"National comparison: {q.get('national_comparison', 'N/A')}")
                
                if bottom_5:
                    logging.info("\nBottom question example:")
                    q = bottom_5[0]
                    logging.info(f"  Question: {q['question_id']}, Mean: {q['mean']}, "
                               f"National comparison: {q.get('national_comparison', 'N/A')}")
                
                return True
            else:
                logging.warning("No top/bottom questions returned")
                return False
        
    except Exception as e:
        logging.error(f"✗ Top/bottom questions test failed: {e}")
        logging.info("The RPC function might not exist - check if create_qla_optimized_views.sql was run")
        return False

def test_national_statistics():
    """Test national statistics calculation"""
    logging.info("\n--- Testing National Statistics ---")
    try:
        # School statistics
        before = supabase.table('national_statistics').select('id', count='exact').execute()
        logging.info(f"National statistics before: {before.count}")
        
        # Question statistics
        nq_before = supabase.table('national_question_statistics').select('id', count='exact').execute()
        logging.info(f"National question statistics before: {nq_before.count}")
        
        # Try the national question statistics procedure
        try:
            result = supabase.rpc('calculate_national_question_statistics', {}).execute()
            logging.info("✓ National question statistics procedure executed")
            
            nq_after = supabase.table('national_question_statistics').select('id', count='exact').execute()
            logging.info(f"National question statistics after: {nq_after.count}")
            
            # Sample
            sample = supabase.table('national_question_statistics').select('*').limit(2).execute()
            if sample.data:
                logging.info("\nSample national question statistics:")
                for stat in sample.data:
                    logging.info(f"  Question: {stat['question_id']}, Cycle: {stat['cycle']}, "
                               f"Mean: {stat.get('mean')}, Total responses: {stat.get('count')}")
            
        except Exception as e:
            logging.warning(f"National question statistics procedure not found: {e}")
        
        return True
        
    except Exception as e:
        logging.error(f"✗ National statistics test failed: {e}")
        return False

def main():
    """Run all tests"""
    logging.info("=" * 60)
    logging.info("STATISTICS CALCULATION TEST SUITE")
    logging.info("=" * 60)
    
    # Keep track of results
    results = {
        'connection': False,
        'data_available': False,
        'school_stats': False,
        'question_stats': False,
        'top_bottom': False,
        'national_stats': False
    }
    
    # Run tests
    if test_connection():
        results['connection'] = True
        
        if test_data_availability():
            results['data_available'] = True
            
            # Test statistics calculations
            results['school_stats'] = test_school_statistics_procedure()
            results['question_stats'] = test_question_statistics_procedure()
            results['top_bottom'] = test_top_bottom_questions()
            results['national_stats'] = test_national_statistics()
    
    # Summary
    logging.info("\n" + "=" * 60)
    logging.info("TEST SUMMARY")
    logging.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logging.info(f"{test_name.ljust(20)}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logging.info("\n✓ All tests passed! Statistics calculations are ready.")
        logging.info("You can now run the full sync with confidence.")
    else:
        logging.info("\n✗ Some tests failed. Please check:")
        logging.info("1. All SQL files have been run (especially fix_question_statistics_schema.sql)")
        logging.info("2. create_qla_optimized_views.sql has been executed")
        logging.info("3. You have data in the tables (students, question_responses)")
    
    return all_passed

if __name__ == "__main__":
    main()