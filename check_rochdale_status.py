"""
Check Rochdale College status in Supabase and refresh materialized view if needed
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')  # Use service key for admin operations

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_rochdale_in_establishments():
    """Check if Rochdale College exists in establishments table"""
    logging.info("Checking for Rochdale College in establishments table...")
    
    try:
        # Search for Rochdale
        result = supabase.table('establishments').select('*').ilike('name', '%rochdale%').execute()
        
        if result.data:
            logging.info(f"Found {len(result.data)} establishment(s) matching 'Rochdale':")
            for est in result.data:
                logging.info(f"  - ID: {est['id']}, Name: {est['name']}")
            return result.data
        else:
            logging.warning("No establishments found matching 'Rochdale'")
            
            # Try broader search
            logging.info("Trying broader search for 'College'...")
            college_result = supabase.table('establishments').select('id, name').ilike('name', '%college%').execute()
            
            if college_result.data:
                logging.info(f"Found {len(college_result.data)} colleges:")
                for est in college_result.data:
                    if 'rochdale' in est['name'].lower():
                        logging.info(f"  *** FOUND: {est['name']} (ID: {est['id']})")
                    else:
                        logging.info(f"  - {est['name']}")
            
            return None
            
    except Exception as e:
        logging.error(f"Error checking establishments: {e}")
        return None

def check_rochdale_students_and_scores(establishment_id):
    """Check if establishment has students and VESPA scores"""
    logging.info(f"Checking students and scores for establishment {establishment_id}...")
    
    try:
        # Check students
        students = supabase.table('students').select('id').eq('establishment_id', establishment_id).execute()
        student_count = len(students.data) if students.data else 0
        logging.info(f"  Students: {student_count}")
        
        if student_count > 0:
            # Check VESPA scores
            student_ids = [s['id'] for s in students.data]
            # Check in batches to avoid query limits
            batch_size = 100
            total_scores = 0
            
            for i in range(0, len(student_ids), batch_size):
                batch = student_ids[i:i+batch_size]
                scores = supabase.table('vespa_scores').select('id, cycle').in_('student_id', batch).execute()
                total_scores += len(scores.data) if scores.data else 0
            
            logging.info(f"  VESPA Scores: {total_scores}")
            
            # Get cycles with data
            if total_scores > 0:
                cycles_query = supabase.table('vespa_scores').select('cycle').in_('student_id', student_ids[:100]).execute()
                if cycles_query.data:
                    unique_cycles = set(s['cycle'] for s in cycles_query.data)
                    logging.info(f"  Cycles with data: {sorted(unique_cycles)}")
            
            return {'students': student_count, 'scores': total_scores}
        
        return {'students': 0, 'scores': 0}
        
    except Exception as e:
        logging.error(f"Error checking students/scores: {e}")
        return None

def check_comparative_metrics_view():
    """Check if Rochdale is in the comparative_metrics materialized view"""
    logging.info("Checking comparative_metrics materialized view...")
    
    try:
        # Check for Rochdale in the view
        result = supabase.table('comparative_metrics').select('establishment_id, establishment_name').ilike('establishment_name', '%rochdale%').limit(1).execute()
        
        if result.data:
            logging.info(f"✓ Rochdale College IS in comparative_metrics view")
            logging.info(f"  Name in view: {result.data[0]['establishment_name']}")
            return True
        else:
            logging.warning("✗ Rochdale College NOT found in comparative_metrics view")
            
            # Get count of establishments in view
            count_result = supabase.table('comparative_metrics').select('establishment_id', count='exact').execute()
            logging.info(f"  Total records in view: {count_result.count}")
            
            # Get distinct establishments
            distinct = supabase.table('comparative_metrics').select('establishment_id, establishment_name').execute()
            if distinct.data:
                unique_establishments = set((r['establishment_id'], r['establishment_name']) for r in distinct.data)
                logging.info(f"  Unique establishments in view: {len(unique_establishments)}")
            
            return False
            
    except Exception as e:
        logging.error(f"Error checking comparative_metrics: {e}")
        return None

def refresh_materialized_view():
    """Attempt to refresh the materialized view"""
    logging.info("Attempting to refresh comparative_metrics materialized view...")
    
    try:
        # Try using RPC function if it exists
        result = supabase.rpc('refresh_materialized_view', {'view_name': 'comparative_metrics'}).execute()
        logging.info("✓ Materialized view refresh initiated via RPC")
        return True
    except Exception as e:
        logging.warning(f"Could not refresh via RPC: {e}")
        
        # Alternative: Try direct SQL (this might not work with Supabase client)
        try:
            # Note: This requires admin privileges and might not work through the client
            logging.info("Attempting direct SQL refresh...")
            logging.warning("Note: Direct SQL refresh through client may not work. You may need to:")
            logging.warning("  1. Go to Supabase Dashboard > SQL Editor")
            logging.warning("  2. Run: REFRESH MATERIALIZED VIEW comparative_metrics;")
            return False
        except Exception as e2:
            logging.error(f"Could not refresh view: {e2}")
            return False

def main():
    """Main diagnostic function"""
    logging.info("=" * 60)
    logging.info("ROCHDALE COLLEGE DIAGNOSTIC CHECK")
    logging.info("=" * 60)
    
    # Step 1: Check if Rochdale exists
    rochdale_establishments = check_rochdale_in_establishments()
    
    if rochdale_establishments:
        for est in rochdale_establishments:
            # Step 2: Check students and scores
            stats = check_rochdale_students_and_scores(est['id'])
            
            if stats and stats['scores'] > 0:
                logging.info(f"✓ {est['name']} has data that SHOULD be in comparative_metrics")
            elif stats and stats['students'] > 0:
                logging.warning(f"⚠ {est['name']} has students but no VESPA scores")
            else:
                logging.warning(f"⚠ {est['name']} has no students or scores")
    
    # Step 3: Check if in materialized view
    in_view = check_comparative_metrics_view()
    
    # Step 4: Recommendation
    logging.info("\n" + "=" * 60)
    logging.info("RECOMMENDATION:")
    logging.info("=" * 60)
    
    if rochdale_establishments and not in_view:
        logging.info("Rochdale College exists but is NOT in the materialized view.")
        logging.info("\nTO FIX THIS:")
        logging.info("1. Go to Supabase Dashboard > SQL Editor")
        logging.info("2. Run this command:")
        logging.info("   REFRESH MATERIALIZED VIEW comparative_metrics;")
        logging.info("\n3. Or run a full sync:")
        logging.info("   python sync_knack_to_supabase.py")
        logging.info("\nThe view refresh may take 1-2 minutes depending on data size.")
        
        # Attempt automatic refresh
        logging.info("\nAttempting automatic refresh...")
        if refresh_materialized_view():
            logging.info("✓ Refresh initiated! Wait 1-2 minutes then check again.")
        else:
            logging.info("✗ Automatic refresh failed. Please use manual method above.")
            
    elif in_view:
        logging.info("✓ Rochdale College is already in the comparative_metrics view!")
        logging.info("  The comparative reporting feature should work.")
    else:
        logging.warning("✗ Rochdale College not found in establishments table.")
        logging.warning("  This school may need to be synced from Knack first.")

if __name__ == "__main__":
    main()
