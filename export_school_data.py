"""
Supabase Data Export Script for Specific Schools
Exports VESPA scores and question responses for cycles 1 & 2 to CSV files
"""

import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# School IDs to export
SCHOOL_IDS = {
    '53e70907-bd30-46fb-b870-e4d4a9c1d06b': 'Tonyrefail Community School',
    '1a327b33-d924-453c-803e-82671f94a242': 'Whitchurch High School',
    '65f4eb79-6f08-4797-83ae-c09b8ae3c194': 'Ysgol Garth Olwg',
    '027ede5d-3384-419e-8390-c86d81cc08ab': 'Llanishen High School'
}

def get_vespa_scores(school_ids, cycles=[1, 2]):
    """
    Fetch VESPA scores for specified schools and cycles
    """
    logging.info("Fetching VESPA scores...")
    
    # Get establishments
    establishments = supabase.table('establishments')\
        .select('*')\
        .in_('id', list(school_ids))\
        .execute()
    
    if not establishments.data:
        logging.warning("No establishments found with the provided IDs")
        return pd.DataFrame()
    
    # Get students for these establishments
    students = supabase.table('students')\
        .select('*')\
        .in_('establishment_id', list(school_ids))\
        .execute()
    
    if not students.data:
        logging.warning("No students found for the specified schools")
        return pd.DataFrame()
    
    student_ids = [s['id'] for s in students.data]
    
    # Get VESPA scores for these students and cycles
    scores = supabase.table('vespa_scores')\
        .select('*')\
        .in_('student_id', student_ids)\
        .in_('cycle', cycles)\
        .execute()
    
    if not scores.data:
        logging.warning("No VESPA scores found for cycles 1 and 2")
        return pd.DataFrame()
    
    # Create DataFrames
    df_establishments = pd.DataFrame(establishments.data)
    df_students = pd.DataFrame(students.data)
    df_scores = pd.DataFrame(scores.data)
    
    # Merge data
    df = df_scores.merge(df_students, left_on='student_id', right_on='id', suffixes=('_score', '_student'))
    df = df.merge(df_establishments, left_on='establishment_id', right_on='id', suffixes=('', '_establishment'))
    
    # Select and rename columns
    df_final = df[[
        'name_establishment', 'name_student', 'email', 'year_group', 'course', 'faculty',
        'cycle', 'vision', 'effort', 'systems', 'practice', 'attitude', 'overall',
        'completion_date', 'academic_year', 'created_at_score'
    ]].copy()
    
    df_final.columns = [
        'school_name', 'student_name', 'student_email', 'year_group', 'course', 'faculty',
        'cycle', 'vision', 'effort', 'systems', 'practice', 'attitude', 'overall',
        'completion_date', 'academic_year', 'score_created_at'
    ]
    
    logging.info(f"Retrieved {len(df_final)} VESPA score records")
    return df_final

def get_question_responses(school_ids, cycles=[1, 2]):
    """
    Fetch question responses for specified schools and cycles
    """
    logging.info("Fetching question responses...")
    
    # Get establishments
    establishments = supabase.table('establishments')\
        .select('*')\
        .in_('id', list(school_ids))\
        .execute()
    
    if not establishments.data:
        logging.warning("No establishments found with the provided IDs")
        return pd.DataFrame()
    
    # Get students for these establishments
    students = supabase.table('students')\
        .select('*')\
        .in_('establishment_id', list(school_ids))\
        .execute()
    
    if not students.data:
        logging.warning("No students found for the specified schools")
        return pd.DataFrame()
    
    student_ids = [s['id'] for s in students.data]
    
    # Get question responses for these students and cycles
    responses = supabase.table('question_responses')\
        .select('*')\
        .in_('student_id', student_ids)\
        .in_('cycle', cycles)\
        .execute()
    
    if not responses.data:
        logging.warning("No question responses found for cycles 1 and 2")
        return pd.DataFrame()
    
    # Get questions metadata
    questions = supabase.table('questions')\
        .select('*')\
        .execute()
    
    # Create DataFrames
    df_establishments = pd.DataFrame(establishments.data)
    df_students = pd.DataFrame(students.data)
    df_responses = pd.DataFrame(responses.data)
    df_questions = pd.DataFrame(questions.data) if questions.data else pd.DataFrame()
    
    # Merge data
    df = df_responses.merge(df_students, left_on='student_id', right_on='id', suffixes=('_response', '_student'))
    df = df.merge(df_establishments, left_on='establishment_id', right_on='id', suffixes=('', '_establishment'))
    
    # Add question metadata if available
    if not df_questions.empty:
        df = df.merge(df_questions[['question_id', 'question_text', 'vespa_category', 'question_order']], 
                     on='question_id', how='left')
    
    # Select and rename columns
    columns_to_select = [
        'name_establishment', 'name_student', 'email', 'year_group', 'course', 'faculty',
        'cycle', 'question_id', 'response_value', 'created_at_response'
    ]
    
    # Add question metadata columns if they exist
    if 'question_text' in df.columns:
        columns_to_select.extend(['question_text', 'vespa_category', 'question_order'])
    
    df_final = df[columns_to_select].copy()
    
    # Rename columns
    rename_dict = {
        'name_establishment': 'school_name',
        'name_student': 'student_name',
        'email': 'student_email',
        'created_at_response': 'response_created_at'
    }
    df_final.rename(columns=rename_dict, inplace=True)
    
    # Sort by school, cycle, student, and question order (if available)
    sort_columns = ['school_name', 'cycle', 'year_group', 'student_name']
    if 'question_order' in df_final.columns:
        sort_columns.append('question_order')
    df_final.sort_values(sort_columns, inplace=True)
    
    logging.info(f"Retrieved {len(df_final)} question response records")
    return df_final

def create_summary_report(df_scores, df_responses):
    """
    Create a summary report of the data
    """
    summary = []
    
    for school_id, school_name in SCHOOL_IDS.items():
        school_scores = df_scores[df_scores['school_name'] == school_name] if not df_scores.empty else pd.DataFrame()
        school_responses = df_responses[df_responses['school_name'] == school_name] if not df_responses.empty else pd.DataFrame()
        
        summary.append({
            'School': school_name,
            'Total Students with Scores': school_scores['student_name'].nunique() if not school_scores.empty else 0,
            'Cycle 1 Score Records': len(school_scores[school_scores['cycle'] == 1]) if not school_scores.empty else 0,
            'Cycle 2 Score Records': len(school_scores[school_scores['cycle'] == 2]) if not school_scores.empty else 0,
            'Total Response Records': len(school_responses) if not school_responses.empty else 0,
            'Cycle 1 Responses': len(school_responses[school_responses['cycle'] == 1]) if not school_responses.empty else 0,
            'Cycle 2 Responses': len(school_responses[school_responses['cycle'] == 2]) if not school_responses.empty else 0
        })
    
    return pd.DataFrame(summary)

def main():
    """
    Main function to export data
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = f'school_data_export_{timestamp}'
    os.makedirs(output_dir, exist_ok=True)
    
    logging.info(f"Starting data export for {len(SCHOOL_IDS)} schools...")
    logging.info(f"Output directory: {output_dir}")
    
    # Fetch data
    df_scores = get_vespa_scores(SCHOOL_IDS.keys())
    df_responses = get_question_responses(SCHOOL_IDS.keys())
    
    # Save VESPA scores
    if not df_scores.empty:
        scores_file = os.path.join(output_dir, f'vespa_scores_cycles_1_2_{timestamp}.csv')
        df_scores.to_csv(scores_file, index=False)
        logging.info(f"✓ Saved VESPA scores to {scores_file}")
    else:
        logging.warning("No VESPA scores data to export")
    
    # Save question responses
    if not df_responses.empty:
        responses_file = os.path.join(output_dir, f'question_responses_cycles_1_2_{timestamp}.csv')
        df_responses.to_csv(responses_file, index=False)
        logging.info(f"✓ Saved question responses to {responses_file}")
    else:
        logging.warning("No question responses data to export")
    
    # Create and save summary report
    df_summary = create_summary_report(df_scores, df_responses)
    summary_file = os.path.join(output_dir, f'export_summary_{timestamp}.csv')
    df_summary.to_csv(summary_file, index=False)
    logging.info(f"✓ Saved summary report to {summary_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("EXPORT SUMMARY")
    print("="*60)
    print(df_summary.to_string(index=False))
    print("="*60)
    
    logging.info(f"Export completed successfully! All files saved to {output_dir}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Error during export: {str(e)}")
        raise
