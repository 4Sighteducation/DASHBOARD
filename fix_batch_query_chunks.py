#!/usr/bin/env python3
"""
Fix for the batch query size issue - need to chunk the IN queries
"""

# The problem:
# results = supabase.table('students').select('id,knack_id').in_('knack_id', knack_ids).execute()
# This fails with 975 IDs - too large!

# The fix - chunk the queries:
def get_student_ids_in_chunks(supabase, knack_ids, chunk_size=50):
    """Get student IDs in chunks to avoid query size limits"""
    all_results = []
    
    for i in range(0, len(knack_ids), chunk_size):
        chunk = knack_ids[i:i+chunk_size]
        results = supabase.table('students').select('id,knack_id').in_('knack_id', chunk).execute()
        all_results.extend(results.data)
    
    return all_results

# Usage in the sync script:
"""
if batch_upsert_with_retry('students', student_batch, 'knack_id'):
    # Update mapping - get all IDs in chunks
    knack_ids = [s['knack_id'] for s in student_batch]
    
    # Process in chunks of 50 to avoid query limits
    for i in range(0, len(knack_ids), 50):
        chunk = knack_ids[i:i+50]
        results = supabase.table('students').select('id,knack_id').in_('knack_id', chunk).execute()
        
        # Update the mapping
        for student in results.data:
            student_knack_to_id[student['knack_id']] = student['id']
"""

print("Fix: Chunk the .in_() queries to 50 IDs at a time!")
print("This avoids the 'JSON could not be generated' error")