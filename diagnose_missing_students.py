#!/usr/bin/env python3
"""
Diagnostic: Why are 13K question responses not syncing?
Find out which students exist in Knack but not in Supabase
"""

import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from collections import Counter

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# CSV Paths
OBJECT_10_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_10_2025.csv"
OBJECT_29_PATH = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\FullObject_29_2025.csv"

def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def get_supabase_student_emails():
    """Get all student emails from Supabase"""
    print_header("FETCHING SUPABASE STUDENTS")
    
    print("⏳ Loading all students from Supabase...")
    
    all_students = []
    page_size = 1000
    offset = 0
    
    while True:
        batch = supabase.table('students')\
            .select('email')\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not batch.data:
            break
        
        all_students.extend(batch.data)
        offset += page_size
        
        if len(all_students) % 5000 == 0:
            print(f"  Loaded {len(all_students):,} students...")
        
        if len(batch.data) < page_size:
            break
    
    # Extract emails and normalize
    emails = set()
    for student in all_students:
        email = student.get('email')
        if email:
            # Normalize: lowercase, strip whitespace
            emails.add(email.lower().strip())
    
    print(f"✅ Found {len(all_students):,} total student records in Supabase")
    print(f"✅ Found {len(emails):,} unique email addresses")
    
    return emails

def analyze_object_29_emails(supabase_emails):
    """Check which Object_29 emails are missing from Supabase"""
    print_header("ANALYZING OBJECT_29 QUESTION RESPONSES")
    
    print("⏳ Reading Object_29 CSV...")
    
    # Read in chunks
    chunks = []
    for chunk in pd.read_csv(OBJECT_29_PATH, chunksize=5000, low_memory=False):
        chunks.append(chunk)
    
    df = pd.concat(chunks, ignore_index=True)
    
    print(f"✅ Loaded {len(df):,} question response records")
    
    # Get student emails from Object_29
    # Field: field_2732_email
    emails_in_obj29 = df['field_2732_email'].dropna()
    
    print(f"📧 Records with email in Object_29: {len(emails_in_obj29):,}")
    print(f"📧 Records WITHOUT email: {len(df) - len(emails_in_obj29):,}")
    
    # Normalize emails
    normalized_emails = set()
    for email in emails_in_obj29:
        if email and isinstance(email, str):
            normalized_emails.add(email.lower().strip())
    
    print(f"📧 Unique emails in Object_29: {len(normalized_emails):,}")
    
    # Find missing emails
    missing_emails = normalized_emails - supabase_emails
    found_emails = normalized_emails & supabase_emails
    
    print(f"\n🔍 COMPARISON:")
    print(f"   Emails in Object_29: {len(normalized_emails):,}")
    print(f"   Emails in Supabase: {len(supabase_emails):,}")
    print(f"   ✅ Found in both: {len(found_emails):,}")
    print(f"   ❌ Missing from Supabase: {len(missing_emails):,}")
    
    # Count how many responses would be skipped
    df['email_normalized'] = df['field_2732_email'].apply(
        lambda x: x.lower().strip() if x and isinstance(x, str) else None
    )
    
    skipped_responses = df[df['email_normalized'].isin(missing_emails)]
    
    print(f"\n⚠️  RESPONSES THAT WOULD BE SKIPPED:")
    print(f"   Total responses for missing students: {len(skipped_responses):,}")
    
    # Sample missing emails
    if missing_emails:
        print(f"\n📧 Sample of missing emails (first 10):")
        for i, email in enumerate(list(missing_emails)[:10], 1):
            # Count responses for this email
            count = len(df[df['email_normalized'] == email])
            print(f"   {i}. {email} ({count} responses)")
    
    return missing_emails, skipped_responses

def analyze_object_10_emails(supabase_emails):
    """Check which Object_10 emails are missing from Supabase"""
    print_header("ANALYZING OBJECT_10 VESPA RESULTS")
    
    print("⏳ Reading Object_10 CSV (sample of 10,000)...")
    
    # Read sample
    df = pd.read_csv(OBJECT_10_PATH, nrows=10000, low_memory=False)
    
    print(f"✅ Loaded {len(df):,} VESPA result records (sample)")
    
    # Get student emails from Object_10
    # Field: field_197_email
    emails_in_obj10 = df['field_197_email'].dropna()
    
    print(f"📧 Records with email in Object_10: {len(emails_in_obj10):,}")
    
    # Normalize emails
    normalized_emails = set()
    for email in emails_in_obj10:
        if email and isinstance(email, str):
            normalized_emails.add(email.lower().strip())
    
    print(f"📧 Unique emails in Object_10 (sample): {len(normalized_emails):,}")
    
    # Find missing emails
    missing_emails = normalized_emails - supabase_emails
    found_emails = normalized_emails & supabase_emails
    
    print(f"\n🔍 COMPARISON (sample):")
    print(f"   Emails in Object_10 sample: {len(normalized_emails):,}")
    print(f"   ✅ Found in Supabase: {len(found_emails):,}")
    print(f"   ❌ Missing from Supabase: {len(missing_emails):,}")
    
    if missing_emails:
        print(f"\n📧 Sample of missing emails from Object_10 (first 10):")
        for i, email in enumerate(list(missing_emails)[:10], 1):
            print(f"   {i}. {email}")
    
    return missing_emails

def check_email_case_sensitivity():
    """Check if email case sensitivity is causing issues"""
    print_header("EMAIL CASE SENSITIVITY CHECK")
    
    # Get sample from Supabase
    sample = supabase.table('students').select('email').limit(100).execute()
    
    case_issues = []
    for student in sample.data:
        email = student.get('email')
        if email:
            if email != email.lower():
                case_issues.append(email)
    
    if case_issues:
        print(f"⚠️  Found {len(case_issues)} emails with mixed case in Supabase:")
        for email in case_issues[:5]:
            print(f"   - {email}")
        print(f"\nThis could cause sync issues!")
    else:
        print(f"✅ All sampled emails are lowercase (good!)")

def main():
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "MISSING STUDENTS DIAGNOSTIC" + " " * 31 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Get Supabase emails
        supabase_emails = get_supabase_student_emails()
        
        # Check Object_29
        missing_obj29, skipped = analyze_object_29_emails(supabase_emails)
        
        # Check Object_10
        missing_obj10 = analyze_object_10_emails(supabase_emails)
        
        # Check case sensitivity
        check_email_case_sensitivity()
        
        # Summary
        print_header("DIAGNOSTIC SUMMARY")
        
        print(f"""
🔍 FINDINGS:

Object_29 (Question Responses):
  ❌ {len(missing_obj29):,} unique student emails NOT in Supabase
  ⚠️  {len(skipped):,} question responses would be skipped
  
Object_10 (VESPA Results) - Sample:
  ❌ {len(missing_obj10):,} student emails NOT in Supabase (from sample)

LIKELY CAUSES:
1. Students in Knack haven't synced to Supabase yet
2. Students were deleted from Supabase during cleanup
3. Email format mismatches (case, spaces)
4. Old academic year students removed

RECOMMENDATION:
{'⚠️  CRITICAL: Many students are missing from Supabase!' if len(missing_obj29) > 1000 else '✅ Only minor missing student issues'}
{'   The archive import will help populate historical students.' if len(missing_obj29) > 1000 else ''}
{'   Current sync may need student re-import from Object_10.' if len(missing_obj10) > 100 else ''}

NEXT STEPS:
1. Run the archive import (will add 2024-2025 students)
2. Check if sync is properly importing from Object_10
3. Consider one-time sync of all current Object_10 students
        """)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()










