#!/usr/bin/env python3
"""
Script to show how to modify the establishment sync to include all establishments
"""

# In sync_knack_to_supabase_production.py, change the sync_establishments function:

def sync_establishments():
    """Sync establishments (schools) from Knack to Supabase"""
    logging.info("Syncing establishments...")
    
    # OPTION 1: Remove filter entirely to get ALL establishments
    establishments = fetch_all_knack_records(OBJECT_KEYS['establishments'], filters=[])
    
    # OPTION 2: Include both Active and Cancelled establishments
    # filters = [
    #     {
    #         'field': 'field_2209',
    #         'operator': 'is any',
    #         'value': ['Active', 'Cancelled', 'Inactive', 'Alumni']
    #     }
    # ]
    
    # OPTION 3: Only exclude truly deleted establishments
    # filters = [
    #     {
    #         'field': 'field_2209',
    #         'operator': 'is not',
    #         'value': 'Deleted'
    #     }
    # ]
    
    # Rest of the function remains the same...