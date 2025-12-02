"""
Backfill student_email in vespa_scores table
This is a one-time fix for records created before student_email was added
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def backfill_student_emails():
    """
    Update all vespa_scores records to populate student_email from students table
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    print("Checking vespa_scores records missing student_email...")
    
    # Get all records where student_email is null
    result = supabase.table('vespa_scores')\
        .select('id, student_id')\
        .is_('student_email', 'null')\
        .execute()
    
    records_to_update = result.data
    print(f"Found {len(records_to_update)} records missing student_email")
    
    if not records_to_update:
        print("All records already have student_email!")
        return
    
    # Get unique student_ids
    unique_student_ids = list(set([r['student_id'] for r in records_to_update]))
    print(f"{len(unique_student_ids)} unique students affected")
    
    # Fetch email for each student_id
    student_emails = {}
    for student_id in unique_student_ids:
        student_result = supabase.table('students')\
            .select('email')\
            .eq('id', student_id)\
            .limit(1)\
            .execute()
        
        if student_result.data:
            student_emails[student_id] = student_result.data[0]['email']
    
    print(f"Found emails for {len(student_emails)} students")
    
    # Update each record
    updated_count = 0
    failed_count = 0
    
    for record in records_to_update:
        student_id = record['student_id']
        record_id = record['id']
        
        if student_id not in student_emails:
            print(f"WARNING: No email found for student_id: {student_id}")
            failed_count += 1
            continue
        
        email = student_emails[student_id]
        
        try:
            supabase.table('vespa_scores')\
                .update({'student_email': email})\
                .eq('id', record_id)\
                .execute()
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"   Updated {updated_count}/{len(records_to_update)}...")
        
        except Exception as e:
            print(f"ERROR: Failed to update record {record_id}: {e}")
            failed_count += 1
    
    print(f"\nBackfill complete!")
    print(f"   Updated: {updated_count}")
    print(f"   Failed: {failed_count}")
    print(f"   Total: {len(records_to_update)}")

if __name__ == '__main__':
    backfill_student_emails()

