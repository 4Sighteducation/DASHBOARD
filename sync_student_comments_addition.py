"""
Addition to sync_knack_to_supabase.py for syncing student comments
This code should be integrated into the existing sync_students_and_vespa_scores() function
"""

def sync_student_comments_from_record(record, student_id, establishment_id, australian_ests):
    """
    Extract and sync student comments from an Object_10 record
    Returns a list of comment data to be batch inserted
    """
    comments_batch = []
    
    # Define the comment field mappings
    comment_mappings = [
        # Cycle 1
        {'cycle': 1, 'type': 'rrc', 'field': 'field_2302', 'field_raw': 'field_2302_raw'},
        {'cycle': 1, 'type': 'goal', 'field': 'field_2499', 'field_raw': 'field_2499_raw'},
        # Cycle 2
        {'cycle': 2, 'type': 'rrc', 'field': 'field_2303', 'field_raw': 'field_2303_raw'},
        {'cycle': 2, 'type': 'goal', 'field': 'field_2493', 'field_raw': 'field_2493_raw'},
        # Cycle 3
        {'cycle': 3, 'type': 'rrc', 'field': 'field_2304', 'field_raw': 'field_2304_raw'},
        {'cycle': 3, 'type': 'goal', 'field': 'field_2494', 'field_raw': 'field_2494_raw'},
    ]
    
    for mapping in comment_mappings:
        # Try to get the comment text from raw field first, then regular field
        comment_text = record.get(mapping['field_raw']) or record.get(mapping['field'])
        
        # Only create a record if there's actual comment text
        if comment_text and isinstance(comment_text, str) and comment_text.strip():
            comment_data = {
                'student_id': student_id,
                'cycle': mapping['cycle'],
                'comment_type': mapping['type'],
                'comment_text': comment_text.strip(),
                'knack_field_id': mapping['field']
            }
            comments_batch.append(comment_data)
    
    return comments_batch


# Add this to the sync_students_and_vespa_scores function after line 431 (after student_id is obtained):
"""
                # Also sync student comments from this record
                comment_records = sync_student_comments_from_record(
                    record, 
                    student_id, 
                    establishment_id,
                    australian_ests
                )
                
                if comment_records:
                    comments_batch.extend(comment_records)
                    
                    # Process comments batch if it reaches the limit
                    if len(comments_batch) >= BATCH_SIZES.get('student_comments', 200):
                        logging.info(f"Processing batch of {len(comments_batch)} student comments...")
                        supabase.table('student_comments').upsert(
                            comments_batch,
                            on_conflict='student_id,cycle,comment_type'
                        ).execute()
                        comments_synced += len(comments_batch)
                        comments_batch = []
"""

# Also add at the beginning of sync_students_and_vespa_scores:
"""
    # Add student_comments to tracking
    sync_report['tables']['student_comments'] = {
        'start_time': datetime.now(),
        'records_before': 0,
        'records_after': 0,
        'new_records': 0,
        'updated_records': 0,
        'errors': 0
    }
    try:
        before_count = supabase.table('student_comments').select('id', count='exact').execute()
        sync_report['tables']['student_comments']['records_before'] = before_count.count
    except:
        pass
    
    # Initialize comments tracking
    comments_batch = []
    comments_synced = 0
"""

# And at the end, process remaining comments:
"""
    # Process any remaining comments in the batch
    if comments_batch:
        logging.info(f"Processing final batch of {len(comments_batch)} student comments...")
        supabase.table('student_comments').upsert(
            comments_batch,
            on_conflict='student_id,cycle,comment_type'
        ).execute()
        comments_synced += len(comments_batch)
    
    # Get final count for comments
    try:
        after_count = supabase.table('student_comments').select('id', count='exact').execute()
        sync_report['tables']['student_comments']['records_after'] = after_count.count
        sync_report['tables']['student_comments']['new_records'] = after_count.count - sync_report['tables']['student_comments']['records_before']
        sync_report['tables']['student_comments']['end_time'] = datetime.now()
    except:
        pass
    
    logging.info(f"Synced {students_synced} students, {scores_synced} VESPA scores, and {comments_synced} student comments")
"""