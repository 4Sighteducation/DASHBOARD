"""
Simple script to add students without Object_29 records (statement scores)
and generate plausible statement scores from desired VESPA scores
"""

from reverse_vespa_calculator import ReverseVESPACalculator
import json

def add_students_with_vespa_only():
    """
    Example of how to add students who only have VESPA scores but no statement scores
    """
    calculator = ReverseVESPACalculator()
    
    # Example: Students with only VESPA scores (no Object_29 records)
    students_vespa_only = [
        {
            'name': 'Alice Johnson',
            'vespa_scores': {'VISION': 8, 'EFFORT': 7, 'SYSTEMS': 9, 'PRACTICE': 6, 'ATTITUDE': 8}
        },
        {
            'name': 'Bob Smith',
            'vespa_scores': {'VISION': 5, 'EFFORT': 6, 'SYSTEMS': 5, 'PRACTICE': 4, 'ATTITUDE': 6}
        },
        {
            'name': 'Carol Davis',
            'vespa_scores': {'VISION': 3, 'EFFORT': 4, 'SYSTEMS': 3, 'PRACTICE': 5, 'ATTITUDE': 4}
        }
    ]
    
    # Generate statement scores for each student
    completed_students = []
    
    for student in students_vespa_only:
        print(f"\nProcessing {student['name']}...")
        
        # Generate complete record with statement scores
        complete_record = calculator.generate_student_record(
            student['vespa_scores'],
            student['name'],
            'realistic'  # Use realistic method for more natural-looking scores
        )
        
        # Display the results
        print(f"  Original VESPA scores: {student['vespa_scores']}")
        print(f"  Generated statement averages:")
        for cat, avg in complete_record['statement_averages'].items():
            print(f"    {cat}: {avg:.2f}")
        print(f"  Verified VESPA scores match: {complete_record['verified_vespa_scores'] == student['vespa_scores']}")
        
        completed_students.append(complete_record)
    
    return completed_students


def generate_class_without_surveys(class_size=30, performance_level='normal'):
    """
    Generate an entire class of students without survey responses
    
    Args:
        class_size: Number of students to generate
        performance_level: 'normal', 'high_performers', 'low_performers', or 'mixed'
    """
    calculator = ReverseVESPACalculator()
    
    print(f"\nGenerating {class_size} students with {performance_level} performance...")
    
    if performance_level == 'mixed':
        # Generate a mixed class
        high_performers = calculator.batch_generate_students(
            class_size // 3, 'high_performers', 'realistic'
        )
        normal_performers = calculator.batch_generate_students(
            class_size // 3, 'normal', 'realistic'
        )
        low_performers = calculator.batch_generate_students(
            class_size - 2 * (class_size // 3), 'low_performers', 'realistic'
        )
        
        students = high_performers + normal_performers + low_performers
    else:
        students = calculator.batch_generate_students(
            class_size, performance_level, 'realistic'
        )
    
    # Summary statistics
    all_vespa_scores = [s['vespa_scores']['OVERALL'] for s in students]
    avg_overall = sum(all_vespa_scores) / len(all_vespa_scores)
    
    print(f"  Generated {len(students)} students")
    print(f"  Average Overall VESPA Score: {avg_overall:.2f}")
    print(f"  VESPA Score Range: {min(all_vespa_scores)} - {max(all_vespa_scores)}")
    
    return students


def create_knack_import_format(students):
    """
    Convert generated students to a format suitable for Knack import
    
    This creates records that match your Object_29 structure
    """
    knack_records = []
    
    for student in students:
        # Create a record for each student's responses
        if 'detailed_responses' in student:
            for response in student['detailed_responses']:
                record = {
                    'student_name': student['student_name'],
                    'question_id': response['questionId'],
                    'question_text': response['questionText'],
                    'vespa_category': response['vespaCategory'],
                    'response_score': response['score'],
                    'field_id': response['fieldId']
                }
                knack_records.append(record)
    
    return knack_records


def main():
    """Main demonstration function"""
    print("VESPA Reverse Calculator - Adding Students Without Statement Scores")
    print("=" * 70)
    
    # Example 1: Add specific students with known VESPA scores
    print("\n1. Adding specific students with VESPA scores only:")
    specific_students = add_students_with_vespa_only()
    
    # Example 2: Generate a whole class
    print("\n2. Generating a mixed-ability class:")
    class_students = generate_class_without_surveys(20, 'mixed')
    
    # Example 3: Convert to Knack format
    print("\n3. Converting to Knack import format:")
    knack_data = create_knack_import_format(specific_students[:1])  # Just first student as example
    print(f"  Generated {len(knack_data)} records for Knack import")
    print(f"  Sample record: {json.dumps(knack_data[0], indent=2)}")
    
    # Save all generated data
    all_students = specific_students + class_students
    
    # Save student records
    with open('generated_student_records.json', 'w') as f:
        json.dump(all_students, f, indent=2)
    print(f"\nSaved {len(all_students)} complete student records to generated_student_records.json")
    
    # Save Knack import data
    all_knack_data = create_knack_import_format(all_students)
    with open('knack_import_data.json', 'w') as f:
        json.dump(all_knack_data, f, indent=2)
    print(f"Saved {len(all_knack_data)} Knack import records to knack_import_data.json")
    
    # Create summary statistics
    summary = {
        'total_students': len(all_students),
        'total_responses': len(all_knack_data),
        'vespa_averages': {},
        'overall_average': sum(s['vespa_scores']['OVERALL'] for s in all_students) / len(all_students)
    }
    
    # Calculate averages per VESPA category
    for category in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']:
        cat_scores = [s['vespa_scores'][category] for s in all_students]
        summary['vespa_averages'][category] = sum(cat_scores) / len(cat_scores)
    
    print(f"\nSummary Statistics:")
    print(f"  Overall VESPA Average: {summary['overall_average']:.2f}")
    for cat, avg in summary['vespa_averages'].items():
        print(f"  {cat} Average: {avg:.2f}")


if __name__ == "__main__":
    main() 