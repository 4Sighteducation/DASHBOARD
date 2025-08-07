"""
Fix for sync_knack_to_supabase.py to properly refresh materialized views
This shows the change needed to make refresh work automatically
"""

# OPTION 1: Add this SQL function to Supabase (see create_refresh_function.sql)
# Then the existing sync script will work

# OPTION 2: Replace the refresh_materialized_views function in sync_knack_to_supabase.py
# with this version that uses direct SQL:

def refresh_materialized_views():
    """Refresh materialized views for comparative analytics"""
    import psycopg2
    from psycopg2 import sql
    import os
    from urllib.parse import urlparse
    
    logging.info("Refreshing materialized views...")
    
    try:
        # Parse the Supabase URL to get connection details
        db_url = os.getenv('DATABASE_URL')  # You need the direct PostgreSQL URL
        if not db_url:
            # Construct from Supabase URL if DATABASE_URL not available
            supabase_url = os.getenv('SUPABASE_URL')
            # This won't work directly - you need the actual PostgreSQL connection string
            logging.warning("DATABASE_URL not found, cannot refresh view directly")
            return False
            
        # Connect directly to PostgreSQL
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Refresh the materialized view
        logging.info("Executing REFRESH MATERIALIZED VIEW comparative_metrics...")
        cur.execute("REFRESH MATERIALIZED VIEW comparative_metrics")
        conn.commit()
        
        # Get count to verify
        cur.execute("SELECT COUNT(*) FROM comparative_metrics")
        count = cur.fetchone()[0]
        logging.info(f"Materialized view refreshed successfully. Records: {count}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Failed to refresh materialized view: {e}")
        return False

# OPTION 3: Add this as a separate step after sync completes:
"""
After your sync runs, manually run:
python refresh_comparative_view.py

Or add to your sync script at the very end:
if __name__ == "__main__":
    main()
    # Add this line:
    os.system("python refresh_comparative_view.py")
"""
