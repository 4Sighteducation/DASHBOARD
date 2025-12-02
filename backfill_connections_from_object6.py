#!/usr/bin/env python3
"""
Backfill Staff-Student Connections from Knack Object_6
=======================================================

Purpose: Create user_connections for students that don't have any

Source: Object_6 (Students) connection fields:
- field_190: Staff Admins
- field_1682: Tutors  
- field_547: Heads of Year
- field_2177: Subject Teachers

Date: December 1, 2025
"""

import os
import re
import json
import logging
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

stats = {'processed': 0, 'connections_created': 0, 'skipped': 0, 'errors': []}

def clean_email(field):
    """Extract clean email from HTML or array"""
    if not field: return None
    if isinstance(field, str):
        match = re.search(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)', field)
        return match.group(1).lower() if match else None
    if isinstance(field, list) and field:
        return clean_email(field[0].get('identifier') if isinstance(field[0], dict) else field[0])
    if isinstance(field, dict) and field.get('identifier'):
        return clean_email(field['identifier'])
    return None

def fetch_object6(page=1):
    """Fetch Object_6 records"""
    url = f"https://api.knack.com/v1/objects/object_6/records?page={page}&rows_per_page=1000"
    response = requests.get(url, headers={
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY
    }, timeout=60)
    response.raise_for_status()
    return response.json()

def create_connection(staff_email, student_email, connection_type):
    """Create connection using RPC"""
    try:
        result = supabase.rpc('create_staff_student_connection', {
            'staff_email_param': staff_email,
            'student_email_param': student_email,
            'connection_type_param': connection_type,
            'context_param': {}
        }).execute()
        
        if result.data:
            stats['connections_created'] += 1
            return True
    except Exception as e:
        if 'already exists' not in str(e).lower():
            logging.warning(f"  Failed: {staff_email} → {student_email} ({connection_type}): {e}")
        return False

def process_student(record, dry_run=False, show_detail=False):
    """Process one student's connections AND update year/group"""
    student_email = clean_email(record.get('field_91'))
    
    if not student_email:
        return
    
    stats['processed'] += 1
    
    # Extract year group and student group
    year_group = record.get('field_548') or record.get('field_550') or ''
    student_group = record.get('field_708') or record.get('field_565') or ''
    
    # Extract staff from connection fields
    tutors = record.get('field_1682_raw', [])
    hoys = record.get('field_547_raw', [])
    teachers = record.get('field_2177_raw', [])
    admins = record.get('field_190_raw', [])
    
    connections_to_create = []
    
    for tutor in tutors:
        email = clean_email(tutor)
        if email: connections_to_create.append((email, 'tutor'))
    
    for hoy in hoys:
        email = clean_email(hoy)
        if email: connections_to_create.append((email, 'head_of_year'))
    
    for teacher in teachers:
        email = clean_email(teacher)
        if email: connections_to_create.append((email, 'subject_teacher'))
    
    for admin in admins:
        email = clean_email(admin)
        if email: connections_to_create.append((email, 'staff_admin'))
    
    if not connections_to_create and not year_group and not student_group:
        stats['skipped'] += 1
        return
    
    if dry_run:
        if show_detail:
            logging.info(f"\n  Student: {student_email}")
            if year_group:
                logging.info(f"    Year Group: {year_group}")
            if student_group:
                logging.info(f"    Tutor Group: {student_group}")
            for staff_email, conn_type in connections_to_create:
                logging.info(f"    → {conn_type}: {staff_email}")
        stats['connections_created'] += len(connections_to_create)
    else:
        # Update year/group in vespa_students
        if year_group or student_group:
            try:
                update_data = {}
                if year_group:
                    update_data['current_year_group'] = year_group
                if student_group:
                    update_data['student_group'] = student_group
                
                supabase.table('vespa_students').update(update_data).eq('email', student_email).execute()
            except Exception as e:
                logging.warning(f"  Failed to update groups for {student_email}: {e}")
        
        # Create connections
        for staff_email, conn_type in connections_to_create:
            create_connection(staff_email, student_email, conn_type)
        
        if stats['processed'] % 100 == 0:
            logging.info(f"  Processed {stats['processed']} students, created {stats['connections_created']} connections")

def main(dry_run=True, school_filter=None):
    logging.info(f"{'DRY RUN - ' if dry_run else ''}BACKFILL CONNECTIONS FROM OBJECT_6")
    if school_filter:
        logging.info(f"Filtering for schools: {school_filter}\n")
    
    page = 1
    detail_count = 0
    
    while page <= 30:
        logging.info(f"Fetching Object_6 page {page}...")
        data = fetch_object6(page)
        records = data.get('records', [])
        
        if not records:
            break
        
        for record in records:
            # Get establishment name for filtering
            est_field = record.get('field_133_raw', [])
            est_name = est_field[0].get('identifier', '') if est_field and isinstance(est_field, list) and len(est_field) > 0 else ''
            
            # Apply filter if specified
            if school_filter and not any(s.lower() in est_name.lower() for s in school_filter):
                continue
            
            # Show detail for first 5 matching students
            show_detail = dry_run and detail_count < 5 and (not school_filter or any(s.lower() in est_name.lower() for s in school_filter))
            if show_detail:
                detail_count += 1
                logging.info(f"\n--- Student #{detail_count} from {est_name} ---")
            
            process_student(record, dry_run, show_detail)
        
        if len(records) < 1000:
            break
        page += 1
    
    logging.info(f"\n{'='*60}")
    logging.info(f"Processed: {stats['processed']}")
    logging.info(f"{'Would create' if dry_run else 'Created'}: {stats['connections_created']}")
    logging.info(f"Skipped (no connections): {stats['skipped']}")
    logging.info(f"{'='*60}")

if __name__ == '__main__':
    import sys
    dry_run = '--live' not in sys.argv
    
    # Support filtering by school
    school_filter = None
    if '--school' in sys.argv:
        idx = sys.argv.index('--school')
        if idx + 1 < len(sys.argv):
            school_filter = [sys.argv[idx + 1]]
    
    main(dry_run, school_filter)

