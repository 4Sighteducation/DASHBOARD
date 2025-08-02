#!/usr/bin/env python3
"""
Check if field numbers in psychometric_question_details.json are sequential
"""

import json

with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
    questions = json.load(f)

print("Checking field number consistency...")
print("=" * 60)

for i, q in enumerate(questions):
    q_num = i + 1
    print(f"\nQuestion {q_num} ({q['questionId']}):")
    print(f"  Cycle 1: {q.get('fieldIdCycle1', 'MISSING')}")
    print(f"  Cycle 2: {q.get('fieldIdCycle2', 'MISSING')}")
    print(f"  Cycle 3: {q.get('fieldIdCycle3', 'MISSING')}")
    
    # Check if sequential
    if i > 0:
        prev_q = questions[i-1]
        
        # Extract field numbers
        try:
            curr_c1 = int(q.get('fieldIdCycle1', '0').replace('field_', ''))
            prev_c1 = int(prev_q.get('fieldIdCycle1', '0').replace('field_', ''))
            
            if curr_c1 != prev_c1 + 1 and curr_c1 != 0:
                print(f"  ⚠️  GAP DETECTED! Expected field_{prev_c1 + 1}, got field_{curr_c1}")
        except:
            pass

print("\n" + "=" * 60)
print("SUMMARY:")
print("If there are gaps after Q9, that explains why sync stops there!")