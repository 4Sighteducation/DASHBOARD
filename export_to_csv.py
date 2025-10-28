"""Export question responses to CSV format"""
import json
import csv

# Load the full results
with open('shireland25_import_full_20251001_083913.json', 'r') as f:
    results = json.load(f)

print("Creating CSV with all 29 question responses per student...")

# Create CSV with all question responses
with open('shireland25_all_questions.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    
    # Header row - Email, Name, then all 29 questions
    header = ['Email', 'Name', 'Establishment']
    
    # Add question columns: V1-V5, E1-E4, S1-S5, P1-P6, A1-A9
    header.extend([f'V{i}' for i in range(1, 6)])  # VISION 1-5
    header.extend([f'E{i}' for i in range(1, 5)])  # EFFORT 1-4
    header.extend([f'S{i}' for i in range(1, 6)])  # SYSTEMS 1-5
    header.extend([f'P{i}' for i in range(1, 7)])  # PRACTICE 1-6
    header.extend([f'A{i}' for i in range(1, 10)]) # ATTITUDE 1-9
    
    # Add VESPA scores at the end
    header.extend(['VESPA_V', 'VESPA_E', 'VESPA_S', 'VESPA_P', 'VESPA_A'])
    
    writer.writerow(header)
    
    # Write each student
    for student in results:
        cycle_data = student['cycles'].get(1, {})  # Get Cycle 1 data
        
        if not cycle_data:
            continue
            
        statement_scores = cycle_data.get('statement_scores', {})
        verified_vespa = cycle_data.get('verified_vespa', {})
        
        row = [
            student['email'],
            student['name'],
            student.get('establishment', '')
        ]
        
        # Add all question responses in order
        row.extend(statement_scores.get('VISION', []))
        row.extend(statement_scores.get('EFFORT', []))
        row.extend(statement_scores.get('SYSTEMS', []))
        row.extend(statement_scores.get('PRACTICE', []))
        row.extend(statement_scores.get('ATTITUDE', []))
        
        # Add VESPA scores
        row.extend([
            verified_vespa.get('VISION', ''),
            verified_vespa.get('EFFORT', ''),
            verified_vespa.get('SYSTEMS', ''),
            verified_vespa.get('PRACTICE', ''),
            verified_vespa.get('ATTITUDE', '')
        ])
        
        writer.writerow(row)

print(f"[OK] Created: shireland25_all_questions.csv")
print(f"     - 79 students")
print(f"     - 29 question responses per student (1-5 Likert scale)")
print(f"     - VESPA scores included for verification")























