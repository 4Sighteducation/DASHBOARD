#!/usr/bin/env python3
"""
Load coaching content from reporttext_fiveband.json into Supabase
This populates the coaching_content table with statements, questions, and coaching comments
"""

import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load the JSON file
# Adjust path to point to Homepage directory
json_path = os.path.join('..', '..', 'Homepage', 'reporttext_fiveband.json')

print(f"Loading coaching content from: {json_path}")

with open(json_path, 'r', encoding='utf-8') as f:
    coaching_data = json.load(f)

print(f"Loaded {len(coaching_data)} coaching content entries")

# Transform and insert data
inserted_count = 0
errors = []

for entry in coaching_data:
    try:
        # Extract score range from ShowForScore array
        scores = entry.get('ShowForScore', [])
        if not scores or len(scores) < 2:
            print(f"Skipping entry with invalid scores: {entry.get('Category')} - {scores}")
            continue
        
        # Helper function to clean NaN values from arrays
        def clean_array(arr):
            if not arr or not isinstance(arr, list):
                return []
            # Filter out NaN, None, and "nan" strings
            return [item for item in arr if item and str(item).lower() != 'nan']
        
        # Map the data structure
        coaching_record = {
            'level': entry.get('Level', ''),
            'category': entry.get('Category', ''),
            'score_min': min(scores),
            'score_max': max(scores),
            'rating': entry.get('ShowForRating', ''),
            'statement_text': entry.get('Text', ''),
            'questions': clean_array(entry.get('questions_list', [])),
            'coaching_comments': clean_array(entry.get('coaching_comments_list', [])),
            'suggested_tools': entry.get('Suggested Tools', '') if str(entry.get('Suggested Tools', '')).lower() != 'nan' else '',
            'welsh_text': entry.get('Welsh Text', ''),
            'welsh_questions': entry.get('Welsh Questions', '') if str(entry.get('Welsh Questions', '')).lower() != 'nan' else '',
            'welsh_tools': entry.get('Welsh Tools', '') if str(entry.get('Welsh Tools', '')).lower() != 'nan' else '',
            'welsh_coaching_comments': entry.get('Welsh Coaching Comments', '')
        }
        
        # Upsert to Supabase
        result = supabase.table('coaching_content').upsert(
            coaching_record,
            on_conflict='level,category,score_min,score_max'
        ).execute()
        
        inserted_count += 1
        
        if inserted_count % 10 == 0:
            print(f"Processed {inserted_count} entries...")
            
    except Exception as e:
        error_msg = f"Error processing {entry.get('Category')} ({entry.get('Level')}, scores {scores}): {e}"
        print(error_msg)
        errors.append(error_msg)

print(f"\n✅ Successfully loaded {inserted_count} coaching content entries")

if errors:
    print(f"\n⚠️  {len(errors)} errors encountered:")
    for error in errors[:10]:  # Show first 10 errors
        print(f"  - {error}")
else:
    print("\n🎉 No errors!")

# Verify the data
result = supabase.table('coaching_content').select('level, category, score_min, score_max', count='exact').execute()
print(f"\nTotal records in coaching_content table: {result.count}")

# Show breakdown by category
categories = supabase.table('coaching_content').select('category', count='exact').execute()
print(f"\nBreakdown by category:")
for cat in ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude', 'Overall']:
    count = supabase.table('coaching_content').select('id', count='exact').eq('category', cat).execute()
    print(f"  {cat}: {count.count} entries")

