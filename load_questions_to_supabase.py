"""
Load psychometric questions from JSON file to Supabase questions table
"""
import json
import os
from dotenv import load_dotenv
from supabase import create_client
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

def load_questions():
    """Load questions from JSON file to Supabase"""
    
    try:
        # Read the questions from JSON file
        with open('AIVESPACoach/psychometric_question_details.json', 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        logging.info(f"Found {len(questions_data)} questions to load")
        
        # Clear existing questions
        logging.info("Clearing existing questions...")
        result = supabase.table('questions').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        logging.info(f"Deleted {len(result.data)} existing questions")
        
        # Prepare questions for insertion
        questions_to_insert = []
        
        for index, q in enumerate(questions_data):
            question = {
                'question_id': q['questionId'],
                'question_text': q['questionText'],
                'vespa_category': q['vespaCategory'],
                'question_order': index + 1,  # 1-based ordering
                'current_cycle_field_id': q.get('currentCycleFieldId'),
                'historical_cycle_field_base': q.get('historicalCycleFieldBase'),
                'field_id_cycle_1': q.get('fieldIdCycle1'),
                'field_id_cycle_2': q.get('fieldIdCycle2'),
                'field_id_cycle_3': q.get('fieldIdCycle3'),
                'is_active': True
            }
            questions_to_insert.append(question)
        
        # Insert questions in batches
        batch_size = 50
        total_inserted = 0
        
        for i in range(0, len(questions_to_insert), batch_size):
            batch = questions_to_insert[i:i + batch_size]
            result = supabase.table('questions').insert(batch).execute()
            total_inserted += len(result.data)
            logging.info(f"Inserted batch {i//batch_size + 1}: {len(result.data)} questions")
        
        logging.info(f"Successfully loaded {total_inserted} questions")
        
        # Verify the data
        verify_questions()
        
    except Exception as e:
        logging.error(f"Error loading questions: {str(e)}")
        raise

def verify_questions():
    """Verify questions were loaded correctly"""
    
    # Count questions by category
    result = supabase.table('questions').select('vespa_category').execute()
    
    category_counts = {}
    for record in result.data:
        category = record['vespa_category']
        category_counts[category] = category_counts.get(category, 0) + 1
    
    logging.info("\nQuestions by category:")
    for category, count in sorted(category_counts.items()):
        logging.info(f"  {category}: {count} questions")
    
    # Show sample questions
    sample = supabase.table('questions').select('question_id, question_text, vespa_category').limit(5).execute()
    
    logging.info("\nSample questions:")
    for q in sample.data:
        logging.info(f"  {q['question_id']}: {q['question_text'][:50]}... ({q['vespa_category']})")
    
    # Check for any missing question IDs in question_responses
    logging.info("\nChecking question_responses compatibility...")
    
    # Get unique question IDs from question_responses
    responses_sample = supabase.table('question_responses').select('question_id').limit(100).execute()
    response_question_ids = set(r['question_id'] for r in responses_sample.data)
    
    # Get all question IDs from questions table
    all_questions = supabase.table('questions').select('question_id').execute()
    db_question_ids = set(q['question_id'] for q in all_questions.data)
    
    # Check for any response question IDs not in questions table
    missing_in_db = response_question_ids - db_question_ids
    if missing_in_db:
        logging.warning(f"Question IDs in responses but not in questions table: {missing_in_db}")
    else:
        logging.info("✓ All question IDs in responses exist in questions table")

if __name__ == "__main__":
    logging.info("Starting questions table load...")
    logging.info(f"Timestamp: {datetime.now()}")
    
    load_questions()
    
    logging.info("\n✅ Questions table successfully populated!")
    logging.info("You can now JOIN questions with question_responses and question_statistics")