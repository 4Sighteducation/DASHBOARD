#!/usr/bin/env python3
"""
Export complete data for specific students
"""
import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Students to export
student_emails = [
    'alannah_will@britishschool.edu.my',
    'thomas_park@britishschool.edu.my',
    'sebastian_wang@britishschool.edu.my',
    'emily_moore@britishschool.edu.my'
]

print("Fetching student data...")

# Get students
students = supabase.table('students')\
    .select('*')\
    .in_('email', student_emails)\
    .execute()

if not students.data:
    print("No students found!")
    exit()

student_ids = [s['id'] for s in students.data]

print(f"Found {len(students.data)} student records")

# Get VESPA scores
vespa_scores = supabase.table('vespa_scores')\
    .select('*')\
    .in_('student_id', student_ids)\
    .execute()

print(f"Found {len(vespa_scores.data)} VESPA scores")

# Get question responses
question_responses = supabase.table('question_responses')\
    .select('*')\
    .in_('student_id', student_ids)\
    .execute()

print(f"Found {len(question_responses.data)} question responses")

# Export to CSV
timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')

# Students
df_students = pd.DataFrame(students.data)
filename_students = f'students_export_{timestamp}.csv'
df_students.to_csv(filename_students, index=False)
print(f"\nStudents exported to: {filename_students}")

# VESPA Scores
if vespa_scores.data:
    df_vespa = pd.DataFrame(vespa_scores.data)
    # Join with student email for readability
    df_vespa = df_vespa.merge(
        df_students[['id', 'email', 'name']], 
        left_on='student_id', 
        right_on='id', 
        how='left'
    )
    filename_vespa = f'vespa_scores_export_{timestamp}.csv'
    df_vespa.to_csv(filename_vespa, index=False)
    print(f"VESPA scores exported to: {filename_vespa}")

# Question Responses
if question_responses.data:
    df_questions = pd.DataFrame(question_responses.data)
    # Join with student email
    df_questions = df_questions.merge(
        df_students[['id', 'email', 'name']], 
        left_on='student_id', 
        right_on='id', 
        how='left'
    )
    filename_questions = f'question_responses_export_{timestamp}.csv'
    df_questions.to_csv(filename_questions, index=False)
    print(f"Question responses exported to: {filename_questions}")

print("\nExport complete!")

