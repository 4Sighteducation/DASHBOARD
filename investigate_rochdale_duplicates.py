#!/usr/bin/env python3
"""
Investigate duplicate student records for Rochdale based on email addresses
This will help us understand the duplicate record situation
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import logging

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
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def investigate_email_duplicates():
    """Find duplicate student records by email for Rochdale"""
    logging.info("=" * 60)
    logging.info("ROCHDALE EMAIL DUPLICATE INVESTIGATION")
    logging.info("=" * 60)
    
    # Get Rochdale's establishment ID
    rochdale = supabase.table('establishments')\
        .select('id, name')\
        .ilike('name', '%Rochdale Sixth Form%')\
        .execute()
    
    if not rochdale.data:
        logging.error("Rochdale Sixth Form College not found!")
        return
    
    establishment_id = rochdale.data[0]['id']
    logging.info(f"Found: {rochdale.data[0]['name']}")
    logging.info(f"Establishment ID: {establishment_id}")
    
    # Get ALL students for Rochdale
    all_students = supabase.table('students')\
        .select('*')\
        .eq('establishment_id', establishment_id)\
        .execute()
    
    logging.info(f"\n📊 Total student records: {len(all_students.data)}")
    
    # Group by email to find duplicates
    students_by_email = {}
    for student in all_students.data:
        email = student.get('email', '').lower() if student.get('email') else None
        if email:
            if email not in students_by_email:
                students_by_email[email] = []
            students_by_email[email].append(student)
    
    # Find duplicates
    duplicate_emails = {email: students for email, students in students_by_email.items() if len(students) > 1}
    
    logging.info(f"\n🔍 DUPLICATE ANALYSIS:")
    logging.info("-" * 40)
    logging.info(f"Unique email addresses: {len(students_by_email)}")
    logging.info(f"Email addresses with duplicates: {len(duplicate_emails)}")
    
    if duplicate_emails:
        # Analyze the pattern of duplicates
        total_duplicate_records = sum(len(students) for students in duplicate_emails.values())
        logging.info(f"Total duplicate student records: {total_duplicate_records}")
        logging.info(f"Expected unique students: {len(students_by_email)}")
        logging.info(f"Actual records: {len(all_students.data)}")
        logging.info(f"Extra records due to duplicates: {len(all_students.data) - len(students_by_email)}")
        
        # Show some examples
        logging.info("\n📋 SAMPLE DUPLICATE RECORDS (first 5):")
        logging.info("-" * 40)
        
        for email, students in list(duplicate_emails.items())[:5]:
            logging.info(f"\nEmail: {email}")
            logging.info(f"  Number of records: {len(students)}")
            
            for student in students:
                created_date = student.get('created_at', 'Unknown')
                if created_date != 'Unknown':
                    try:
                        created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                logging.info(f"  - ID: {student['id'][:8]}...")
                logging.info(f"    Knack ID: {student.get('knack_id', 'None')}")
                logging.info(f"    Year Group: {student.get('year_group', 'None')}")
                logging.info(f"    Created: {created_date}")
                
                # Check if this student has VESPA scores
                vespa = supabase.table('vespa_scores')\
                    .select('cycle, academic_year, completion_date')\
                    .eq('student_id', student['id'])\
                    .execute()
                
                if vespa.data:
                    logging.info(f"    VESPA records: {len(vespa.data)}")
                    for v in vespa.data:
                        logging.info(f"      - Cycle {v['cycle']}, Year: {v['academic_year']}, Date: {v.get('completion_date', 'No date')[:10] if v.get('completion_date') else 'No date'}")
                else:
                    logging.info(f"    VESPA records: 0")
        
        # Analyze which duplicates have data
        logging.info("\n📈 DATA DISTRIBUTION IN DUPLICATES:")
        logging.info("-" * 40)
        
        old_records_with_data = 0
        new_records_with_data = 0
        both_have_data = 0
        neither_has_data = 0
        
        for email, students in duplicate_emails.items():
            # Sort by creation date to identify old vs new
            students_sorted = sorted(students, key=lambda x: x.get('created_at', ''))
            
            if len(students_sorted) >= 2:
                old_student = students_sorted[0]
                new_student = students_sorted[-1]
                
                # Check for VESPA data
                old_vespa = supabase.table('vespa_scores')\
                    .select('id', count='exact')\
                    .eq('student_id', old_student['id'])\
                    .execute()
                
                new_vespa = supabase.table('vespa_scores')\
                    .select('id', count='exact')\
                    .eq('student_id', new_student['id'])\
                    .execute()
                
                old_has_data = old_vespa.count > 0
                new_has_data = new_vespa.count > 0
                
                if old_has_data and new_has_data:
                    both_have_data += 1
                elif old_has_data:
                    old_records_with_data += 1
                elif new_has_data:
                    new_records_with_data += 1
                else:
                    neither_has_data += 1
        
        logging.info(f"Both old and new have data: {both_have_data}")
        logging.info(f"Only old record has data: {old_records_with_data}")
        logging.info(f"Only new record has data: {new_records_with_data}")
        logging.info(f"Neither has data: {neither_has_data}")
        
        # Calculate what this means for the dashboard
        logging.info("\n🎯 DASHBOARD COUNT EXPLANATION:")
        logging.info("-" * 40)
        
        # Count total VESPA records across all students
        all_student_ids = [s['id'] for s in all_students.data]
        
        # Process in batches
        batch_size = 50
        vespa_by_year = {'2024/2025': 0, '2025/2026': 0}
        unique_students_by_year = {'2024/2025': set(), '2025/2026': set()}
        
        for i in range(0, len(all_student_ids), batch_size):
            batch_ids = all_student_ids[i:i+batch_size]
            vespa_batch = supabase.table('vespa_scores')\
                .select('student_id, academic_year')\
                .in_('student_id', batch_ids)\
                .execute()
            
            for record in vespa_batch.data:
                year = record.get('academic_year')
                if year in vespa_by_year:
                    vespa_by_year[year] += 1
                    unique_students_by_year[year].add(record['student_id'])
        
        logging.info("VESPA Records by Academic Year:")
        logging.info(f"  2024/2025: {vespa_by_year['2024/2025']} records from {len(unique_students_by_year['2024/2025'])} unique students")
        logging.info(f"  2025/2026: {vespa_by_year['2025/2026']} records from {len(unique_students_by_year['2025/2026'])} unique students")
        
        logging.info(f"\n💡 LIKELY EXPLANATION:")
        logging.info(f"Dashboard shows 2303 for 2025/2026 because:")
        logging.info(f"  - It's counting VESPA records, not unique students")
        logging.info(f"  - Multiple cycles per student (Cycle 1, 2, 3)")
        logging.info(f"  - Duplicate student records with same email")
        
        return len(all_students.data), len(students_by_email), len(duplicate_emails)
    
    else:
        logging.info("No duplicate emails found!")
        return len(all_students.data), len(students_by_email), 0

def suggest_fix():
    """Suggest how to fix the duplicate issue"""
    logging.info("\n" + "=" * 60)
    logging.info("RECOMMENDED FIX")
    logging.info("=" * 60)
    
    logging.info("\n1. MERGE DUPLICATE RECORDS:")
    logging.info("   - Identify old and new records by creation date")
    logging.info("   - Move all VESPA scores to the newest student record")
    logging.info("   - Delete the old duplicate records")
    
    logging.info("\n2. FIX ACADEMIC YEARS:")
    logging.info("   - Update VESPA records based on completion dates")
    logging.info("   - Records before Aug 1, 2025 → 2024/2025")
    logging.info("   - Records after Aug 1, 2025 → 2025/2026")
    
    logging.info("\n3. UPDATE SYNC SCRIPT:")
    logging.info("   - Already uses email as identifier")
    logging.info("   - Should prevent future duplicates")

def main():
    """Main execution"""
    try:
        total_records, unique_emails, duplicate_count = investigate_email_duplicates()
        
        logging.info("\n" + "=" * 60)
        logging.info("SUMMARY")
        logging.info("=" * 60)
        logging.info(f"Total student records: {total_records}")
        logging.info(f"Unique email addresses: {unique_emails}")
        logging.info(f"Emails with duplicates: {duplicate_count}")
        
        if duplicate_count > 0:
            suggest_fix()
            
            logging.info("\n⚠️  WARNING:")
            logging.info("Running the academic year fix without merging duplicates first")
            logging.info("will only fix SOME of the data. We should merge duplicates first!")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
