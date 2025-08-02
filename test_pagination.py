#!/usr/bin/env python3
"""
Test the correct way to paginate Supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Testing Supabase pagination...")

# Method 1: Using range
print("\nMethod 1: Using range()")
students = supabase.table('students').select('id', count='exact').execute()
print(f"Total students: {students.count}")

# Test range
print("\nTesting range(0, 999):")
batch1 = supabase.table('students').select('id').range(0, 999).execute()
print(f"  Returned: {len(batch1.data)} records")

print("\nTesting range(1000, 1999):")
batch2 = supabase.table('students').select('id').range(1000, 1999).execute()
print(f"  Returned: {len(batch2.data)} records")

# Method 2: Using limit and offset
print("\n\nMethod 2: Using limit() and offset()")
print("\nTesting limit(1000).offset(0):")
batch3 = supabase.table('students').select('id').limit(1000).offset(0).execute()
print(f"  Returned: {len(batch3.data)} records")

print("\nTesting limit(1000).offset(1000):")
batch4 = supabase.table('students').select('id').limit(1000).offset(1000).execute()
print(f"  Returned: {len(batch4.data)} records")

# Show correct approach
print("\n" + "=" * 60)
print("CORRECT APPROACH:")
print("=" * 60)

student_count = 0
offset = 0
limit = 1000

while True:
    # Using limit and offset (more reliable)
    batch = supabase.table('students').select('id').limit(limit).offset(offset).execute()
    
    if not batch.data:
        break
        
    student_count += len(batch.data)
    print(f"Batch at offset {offset}: {len(batch.data)} records (total so far: {student_count})")
    
    if len(batch.data) < limit:
        break
        
    offset += limit

print(f"\nTotal loaded: {student_count}")