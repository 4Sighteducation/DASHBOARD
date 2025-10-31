"""Create CSV with Knack field names as headers"""
import json
import csv

# Load the question mappings to get field order
with open('AIVESPACoach/psychometric_question_output_object_120.json', 'r') as f:
    question_mappings = json.load(f)

# Load the generated data
with open('shireland25_import_cycle1_knack_20251001_083913.json', 'r') as f:
    students = json.load(f)

print("Creating CSV with Knack field names...")

# Get all question field IDs for Cycle 1 (excluding NA_OUTCOME questions)
field_ids = []
for q in question_mappings:
    if q['vespaCategory'] != 'NA_OUTCOME':
        field_id = q['fieldIdCycle1']
        if field_id not in field_ids:
            field_ids.append(field_id)

print(f"Found {len(field_ids)} question fields")

# Create CSV
with open('shireland25_knack_import.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    
    # Header: Email, Name, then all field IDs
    header = ['Email', 'Name'] + field_ids
    writer.writerow(header)
    
    # Write each student
    for student in students:
        row = [
            student.get('field_2732', ''),  # Email
            student.get('field_1823', '')   # Name
        ]
        
        # Add score for each field
        for field_id in field_ids:
            row.append(student.get(field_id, ''))
        
        writer.writerow(row)

print(f"[OK] Created: shireland25_knack_import.csv")
print(f"     - {len(students)} students")
print(f"     - {len(field_ids)} question columns")
print(f"     - Headers: Email, Name, {field_ids[0]}, {field_ids[1]}, ... {field_ids[-1]}")
























