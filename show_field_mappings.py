#!/usr/bin/env python3
"""
Display field mappings in order for each cycle
"""

import json

with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
    questions = json.load(f)

print("=" * 80)
print("FIELD MAPPINGS BY CYCLE")
print("=" * 80)

# Extract and display by cycle
for cycle in [1, 2, 3]:
    print(f"\nCYCLE {cycle} FIELDS (in order):")
    print("-" * 60)
    
    field_numbers = []
    for i, q in enumerate(questions):
        field_key = f'fieldIdCycle{cycle}'
        field_id = q.get(field_key, 'MISSING')
        
        # Extract just the number
        if field_id.startswith('field_'):
            field_num = int(field_id.replace('field_', ''))
            field_numbers.append((i+1, q['questionId'], field_num, field_id))
    
    # Sort by field number to see the actual order
    field_numbers.sort(key=lambda x: x[2])
    
    # Display
    for q_num, q_id, f_num, f_id in field_numbers:
        print(f"  Q{q_num:2d} ({q_id:20s}): {f_id}")
    
    # Check for gaps
    print(f"\n  Field range: {field_numbers[0][2]} to {field_numbers[-1][2]}")
    print(f"  Total fields: {len(field_numbers)}")
    
    # Check sequential
    expected = field_numbers[0][2]
    gaps = []
    for i, (_, _, f_num, _) in enumerate(field_numbers):
        if i > 0 and f_num != expected:
            gaps.append(f"Gap: expected field_{expected}, got field_{f_num}")
        expected = f_num + 1
    
    if gaps:
        print(f"  Gaps found: {len(gaps)}")
        for gap in gaps[:5]:  # Show first 5 gaps
            print(f"    {gap}")

print("\n" + "=" * 80)
print("PATTERN ANALYSIS:")
print("=" * 80)

# Analyze the pattern
print("\nThe fields are interwoven across cycles:")
print("- Cycle 1: Uses every 3rd field starting from 1953")
print("- Cycle 2: Uses every 3rd field starting from 1955") 
print("- Cycle 3: Uses every 3rd field starting from 1956")

print("\nSequence pattern:")
for i in range(5):  # Show first 5 questions
    c1 = questions[i].get('fieldIdCycle1', 'MISSING')
    c2 = questions[i].get('fieldIdCycle2', 'MISSING')
    c3 = questions[i].get('fieldIdCycle3', 'MISSING')
    print(f"  Q{i+1}: {c1}, {c2}, {c3}")