def sync_students_and_vespa_scores():
    """Sync students and VESPA scores from Object_10 with batch processing"""
    logging.info("Syncing students and VESPA scores...")
    
    # Track metrics for both tables
    for table_name in ['students', 'vespa_scores']:
        sync_report['tables'][table_name] = {
            'start_time': datetime.now(),
            'records_before': 0,
            'records_after': 0,
            'new_records': 0,
            'updated_records': 0,
            'errors': 0
        }
        try:
            before_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_before'] = before_count.count
        except:
            pass
    
    # Initialize tracking variables
    page = 1
    students_processed = set()
    
    # Get establishment mapping first - cache this for efficiency
    establishments = supabase.table('establishments').select('id', 'knack_id', 'is_australian').execute()
    est_map = {e['knack_id']: e['id'] for e in establishments.data}
    
    # Pre-fetch all Australian establishments to avoid repeated queries
    australian_ests = {e['id']: e.get('is_australian', False) for e in establishments.data}
    
    # Pre-fetch existing students to build knack_id -> student_id mapping
    logging.info("Loading existing student mappings...")
    student_id_map = {}
    offset = 0
    limit = 1000
    while True:
        existing_students = supabase.table('students').select('id', 'knack_id').limit(limit).offset(offset).execute()
        if not existing_students.data:
            break
        for student in existing_students.data:
            student_id_map[student['knack_id']] = student['id']
        if len(existing_students.data) < limit:
            break
        offset += limit
    logging.info(f"Loaded {len(student_id_map)} existing student mappings")
    
    scores_synced = 0
    students_synced = 0
    student_batch = []
    vespa_batch = []
    
    # Process in batches to avoid memory issues
    while True:
        if shutdown_requested:
            logging.info("Shutdown requested, stopping gracefully...")
            break
            
        logging.info(f"Processing VESPA records page {page}...")
        data = make_knack_request(OBJECT_KEYS['vespa_results'], page=page)
        records = data.get('records', [])
        
        if not records:
            break
            
        for record in records:
            try:
                # Extract student info
                email_field = record.get('field_197_raw', {})
                if isinstance(email_field, dict):
                    email_value = email_field.get('email', '')
                    # Handle case where email value is also a dict
                    if isinstance(email_value, dict):
                        student_email = email_value.get('address', '') or email_value.get('email', '') or str(email_value)
                    else:
                        student_email = str(email_value) if email_value else ''
                elif isinstance(email_field, str):
                    student_email = email_field
                else:
                    student_email = ''
                
                # Ensure email is a string and not empty
                if not student_email or not isinstance(student_email, str) or student_email == '{}':
                    continue
                
                # Get establishment UUID
                est_field = record.get('field_133_raw', [])
                if est_field and isinstance(est_field, list) and len(est_field) > 0:
                    est_item = est_field[0]
                    # Handle if the establishment reference is a dict
                    if isinstance(est_item, dict):
                        est_knack_id = est_item.get('id') or est_item.get('value') or None
                    else:
                        est_knack_id = est_item
                else:
                    est_knack_id = None
                establishment_id = est_map.get(est_knack_id) if est_knack_id else None
                
                # Create/update student if not already processed
                if student_email not in students_processed:
                    # Extract name safely
                    name_field = record.get('field_187_raw', '')
                    if isinstance(name_field, dict):
                        # Extract full name from the name object
                        student_name = name_field.get('full', '') or f"{name_field.get('first', '')} {name_field.get('last', '')}".strip()
                    elif isinstance(name_field, str):
                        student_name = name_field
                    else:
                        student_name = ''
                    
                    student_data = {
                        'knack_id': record['id'],
                        'email': student_email,
                        'name': student_name,
                        'establishment_id': establishment_id,
                        'group': record.get('field_223', ''),  # field_223 is group
                        'year_group': record.get('field_144', ''),  # Corrected: field_144 is year_group
                        'course': record.get('field_2299', ''),
                        'faculty': record.get('field_782', '')  # Corrected: field_782 is faculty
                    }
                    
                    student_batch.append(student_data)
                    students_processed.add(student_email)
                    
                    # Process batch if it reaches the limit
                    if len(student_batch) >= BATCH_SIZES['students']:
                        logging.info(f"Processing batch of {len(student_batch)} students...")
                        result = supabase.table('students').upsert(
                            student_batch,
                            on_conflict='knack_id'
                        ).execute()
                        
                        # Update the student_id_map with the newly inserted/updated students
                        for student in result.data:
                            student_id_map[student['knack_id']] = student['id']
                        
                        students_synced += len(student_batch)
                        student_batch = []
                
                # Get student ID from map (avoid individual lookups)
                student_id = student_id_map.get(record['id'])
                if not student_id:
                    # Student might be in the current batch but not yet in database
                    # Skip for now, it will be processed in the next sync run
                    continue
                
                # Extract VESPA scores for each cycle
                for cycle in [1, 2, 3]:
                    # Calculate field offsets for each cycle
                    field_offset = (cycle - 1) * 6
                    vision_field = f'field_{155 + field_offset}_raw'
                    
                    # Check if this cycle has data
                    if record.get(vision_field) is not None:
                        # Helper function to convert empty strings to None
                        def clean_score(value):
                            if value == "" or value is None:
                                return None
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return None
                        
                        # Convert UK date format to ISO format for PostgreSQL
                        completion_date_raw = record.get('field_855')
                        completion_date = None
                        if completion_date_raw and completion_date_raw.strip():  # Check for empty strings
                            try:
                                # Parse UK format DD/MM/YYYY and convert to YYYY-MM-DD
                                date_obj = datetime.strptime(completion_date_raw, '%d/%m/%Y')
                                completion_date = date_obj.strftime('%Y-%m-%d')
                            except ValueError:
                                logging.warning(f"Invalid date format: {completion_date_raw}")
                        
                        vespa_data = {
                            'student_id': student_id,
                            'cycle': cycle,
                            'vision': clean_score(record.get(f'field_{155 + field_offset}_raw')),
                            'effort': clean_score(record.get(f'field_{156 + field_offset}_raw')),
                            'systems': clean_score(record.get(f'field_{157 + field_offset}_raw')),
                            'practice': clean_score(record.get(f'field_{158 + field_offset}_raw')),
                            'attitude': clean_score(record.get(f'field_{159 + field_offset}_raw')),
                            'overall': clean_score(record.get(f'field_{160 + field_offset}_raw')),
                            'completion_date': completion_date,
                            'academic_year': calculate_academic_year(
                                record.get('field_855'),
                                establishment_id,
                                australian_ests.get(establishment_id, False)
                            )
                        }
                        
                        vespa_batch.append(vespa_data)
                        
                        # Process batch if it reaches the limit
                        if len(vespa_batch) >= BATCH_SIZES['vespa_scores']:
                            logging.info(f"Processing batch of {len(vespa_batch)} VESPA scores...")
                            supabase.table('vespa_scores').upsert(
                                vespa_batch,
                                on_conflict='student_id,cycle'
                            ).execute()
                            scores_synced += len(vespa_batch)
                            vespa_batch = []
                        
            except Exception as e:
                error_msg = f"Error syncing VESPA record {record.get('id')}: {e}"
                logging.error(error_msg)
                sync_report['errors'].append(error_msg)
                sync_report['tables']['vespa_scores']['errors'] += 1
                # Log more details for debugging
                if 'unhashable' in str(e):
                    logging.error(f"Debug - field_197_raw: {record.get('field_197_raw')}")
                    logging.error(f"Debug - field_133_raw: {record.get('field_133_raw')}")
                    logging.error(f"Debug - student_email type: {type(student_email) if 'student_email' in locals() else 'undefined'}")
        
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    # Process any remaining students in the batch
    if student_batch:
        logging.info(f"Processing final batch of {len(student_batch)} students...")
        result = supabase.table('students').upsert(
            student_batch,
            on_conflict='knack_id'
        ).execute()
        
        # Update the student_id_map with the newly inserted/updated students
        for student in result.data:
            student_id_map[student['knack_id']] = student['id']
        
        students_synced += len(student_batch)
    
    # Process any remaining VESPA scores in the batch
    if vespa_batch:
        logging.info(f"Processing final batch of {len(vespa_batch)} VESPA scores...")
        supabase.table('vespa_scores').upsert(
            vespa_batch,
            on_conflict='student_id,cycle'
        ).execute()
        scores_synced += len(vespa_batch)
    
    # Get final counts
    for table_name in ['students', 'vespa_scores']:
        try:
            after_count = supabase.table(table_name).select('id', count='exact').execute()
            sync_report['tables'][table_name]['records_after'] = after_count.count
            sync_report['tables'][table_name]['new_records'] = after_count.count - sync_report['tables'][table_name]['records_before']
            sync_report['tables'][table_name]['end_time'] = datetime.now()
        except:
            pass
    
    logging.info(f"Synced {students_synced} students and {scores_synced} VESPA scores")