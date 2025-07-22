"""
Reverse VESPA Calculator
This calculator generates statement scores (1-5) that would produce desired VESPA scores (1-10).
It works backwards from the existing VESPA calculation algorithms.
"""

import random
import json
from typing import Dict, List, Tuple
import numpy as np

class ReverseVESPACalculator:
    def __init__(self):
        # Define the VESPA score thresholds for each category
        # Each tuple contains (lower_bound, upper_bound) for the average statement score
        self.vespa_thresholds = {
            'VISION': [
                (0, 2.26),      # VESPA 1
                (2.26, 2.7),    # VESPA 2
                (2.7, 3.02),    # VESPA 3
                (3.02, 3.33),   # VESPA 4
                (3.33, 3.52),   # VESPA 5
                (3.52, 3.84),   # VESPA 6
                (3.84, 4.15),   # VESPA 7
                (4.15, 4.47),   # VESPA 8
                (4.47, 4.79),   # VESPA 9
                (4.79, 5.0)     # VESPA 10
            ],
            'EFFORT': [
                (0, 2.42),      # VESPA 1
                (2.42, 2.73),   # VESPA 2
                (2.73, 3.04),   # VESPA 3
                (3.04, 3.36),   # VESPA 4
                (3.36, 3.67),   # VESPA 5
                (3.67, 3.86),   # VESPA 6
                (3.86, 4.17),   # VESPA 7
                (4.17, 4.48),   # VESPA 8
                (4.48, 4.8),    # VESPA 9
                (4.8, 5.0)      # VESPA 10
            ],
            'SYSTEMS': [
                (0, 2.36),      # VESPA 1
                (2.36, 2.76),   # VESPA 2
                (2.76, 3.16),   # VESPA 3
                (3.16, 3.46),   # VESPA 4
                (3.46, 3.75),   # VESPA 5
                (3.75, 4.05),   # VESPA 6
                (4.05, 4.35),   # VESPA 7
                (4.35, 4.64),   # VESPA 8
                (4.64, 4.94),   # VESPA 9
                (4.94, 5.0)     # VESPA 10
            ],
            'PRACTICE': [
                (0, 1.74),      # VESPA 1
                (1.74, 2.1),    # VESPA 2
                (2.1, 2.46),    # VESPA 3
                (2.46, 2.74),   # VESPA 4
                (2.74, 3.02),   # VESPA 5
                (3.02, 3.3),    # VESPA 6
                (3.3, 3.66),    # VESPA 7
                (3.66, 3.94),   # VESPA 8
                (3.94, 4.3),    # VESPA 9
                (4.3, 5.0)      # VESPA 10
            ],
            'ATTITUDE': [
                (0, 2.31),      # VESPA 1
                (2.31, 2.72),   # VESPA 2
                (2.72, 3.01),   # VESPA 3
                (3.01, 3.3),    # VESPA 4
                (3.3, 3.53),    # VESPA 5
                (3.53, 3.83),   # VESPA 6
                (3.83, 4.06),   # VESPA 7
                (4.06, 4.35),   # VESPA 8
                (4.35, 4.7),    # VESPA 9
                (4.7, 5.0)      # VESPA 10
            ]
        }
        
        # Load question mappings
        self.load_question_mappings()
    
    def load_question_mappings(self):
        """Load the psychometric question details to map questions to VESPA categories"""
        try:
            with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
                questions = json.load(f)
                
            # Group questions by VESPA category
            self.questions_by_category = {}
            for q in questions:
                category = q['vespaCategory']
                if category not in self.questions_by_category:
                    self.questions_by_category[category] = []
                self.questions_by_category[category].append(q)
                
            # Count questions per category
            self.questions_per_category = {
                cat: len(questions) for cat, questions in self.questions_by_category.items()
            }
        except Exception as e:
            print(f"Warning: Could not load question mappings: {e}")
            # Default counts if file not available
            self.questions_per_category = {
                'VISION': 5,
                'EFFORT': 4,
                'SYSTEMS': 5,
                'PRACTICE': 6,
                'ATTITUDE': 9
            }
            self.questions_by_category = None
    
    def generate_statement_scores(self, desired_vespa_scores: Dict[str, int], 
                                generation_method: str = 'balanced') -> Dict[str, List[int]]:
        """
        Generate statement scores that would produce the desired VESPA scores
        
        Args:
            desired_vespa_scores: Dict mapping category to desired VESPA score (1-10)
            generation_method: 'balanced', 'random', or 'realistic'
            
        Returns:
            Dict mapping category to list of statement scores
        """
        statement_scores = {}
        
        for category, vespa_score in desired_vespa_scores.items():
            if category not in self.vespa_thresholds:
                continue
                
            # Get the average range for this VESPA score
            score_index = vespa_score - 1  # Convert 1-10 to 0-9 index
            if score_index < 0 or score_index >= len(self.vespa_thresholds[category]):
                raise ValueError(f"Invalid VESPA score {vespa_score} for category {category}")
                
            lower_bound, upper_bound = self.vespa_thresholds[category][score_index]
            
            # Generate statement scores based on method
            num_questions = self.questions_per_category.get(category, 5)
            
            if generation_method == 'balanced':
                scores = self._generate_balanced_scores(lower_bound, upper_bound, num_questions)
            elif generation_method == 'random':
                scores = self._generate_random_scores(lower_bound, upper_bound, num_questions)
            elif generation_method == 'realistic':
                scores = self._generate_realistic_scores(lower_bound, upper_bound, num_questions)
            else:
                raise ValueError(f"Unknown generation method: {generation_method}")
                
            statement_scores[category] = scores
            
        return statement_scores
    
    def _generate_balanced_scores(self, lower_bound: float, upper_bound: float, 
                                num_questions: int) -> List[int]:
        """Generate balanced statement scores that average to the target range"""
        # Calculate target average (middle of the range)
        target_avg = (lower_bound + upper_bound) / 2
        
        # Start with all scores at the rounded target average
        base_score = round(target_avg)
        scores = [base_score] * num_questions
        
        # Adjust scores to create variation while maintaining average
        current_avg = sum(scores) / len(scores)
        
        # Add variation
        for i in range(num_questions // 2):
            # Increase one score and decrease another to maintain average
            if scores[i] < 5:
                scores[i] += 1
                if i + num_questions // 2 < num_questions and scores[i + num_questions // 2] > 1:
                    scores[i + num_questions // 2] -= 1
        
        # Fine-tune to ensure average is in range
        self._adjust_scores_to_target(scores, lower_bound, upper_bound)
        
        return scores
    
    def _generate_random_scores(self, lower_bound: float, upper_bound: float, 
                              num_questions: int) -> List[int]:
        """Generate random statement scores that average to the target range"""
        scores = []
        
        # Generate random scores until we get an average in the target range
        max_attempts = 1000
        for _ in range(max_attempts):
            # Generate random scores weighted towards the middle of the range
            target_avg = (lower_bound + upper_bound) / 2
            
            # Use normal distribution centered on target
            raw_scores = np.random.normal(target_avg, 0.8, num_questions)
            
            # Clip to 1-5 range and round
            scores = [max(1, min(5, round(s))) for s in raw_scores]
            
            # Check if average is in range
            avg = sum(scores) / len(scores)
            if lower_bound <= avg <= upper_bound:
                return scores
        
        # Fallback to balanced method if random fails
        return self._generate_balanced_scores(lower_bound, upper_bound, num_questions)
    
    def _generate_realistic_scores(self, lower_bound: float, upper_bound: float, 
                                 num_questions: int) -> List[int]:
        """Generate realistic statement scores with natural clustering"""
        target_avg = (lower_bound + upper_bound) / 2
        
        # Determine score distribution based on target average
        if target_avg < 2.5:  # Low scores
            # Most scores low with few medium
            weights = [0.4, 0.3, 0.2, 0.08, 0.02]  # Weights for scores 1-5
        elif target_avg < 3.5:  # Medium scores
            # Bell curve centered on 3
            weights = [0.1, 0.2, 0.4, 0.2, 0.1]
        else:  # High scores
            # Most scores high with few medium
            weights = [0.02, 0.08, 0.2, 0.3, 0.4]
        
        # Generate scores based on weights
        scores = []
        for _ in range(num_questions):
            score = np.random.choice([1, 2, 3, 4, 5], p=weights)
            scores.append(score)
        
        # Adjust to ensure average is in range
        self._adjust_scores_to_target(scores, lower_bound, upper_bound)
        
        return scores
    
    def _adjust_scores_to_target(self, scores: List[int], lower_bound: float, 
                               upper_bound: float, max_iterations: int = 100):
        """Adjust scores to ensure average falls within target range"""
        for _ in range(max_iterations):
            avg = sum(scores) / len(scores)
            
            if lower_bound <= avg <= upper_bound:
                return  # We're in range
            
            if avg < lower_bound:
                # Need to increase average - find lowest score to increase
                min_idx = scores.index(min(scores))
                if scores[min_idx] < 5:
                    scores[min_idx] += 1
            else:
                # Need to decrease average - find highest score to decrease
                max_idx = scores.index(max(scores))
                if scores[max_idx] > 1:
                    scores[max_idx] -= 1
    
    def verify_vespa_calculation(self, category: str, statement_scores: List[int]) -> int:
        """Verify that the generated statement scores produce the expected VESPA score"""
        avg = sum(statement_scores) / len(statement_scores)
        
        # Find which VESPA score this average maps to
        thresholds = self.vespa_thresholds[category]
        for vespa_score, (lower, upper) in enumerate(thresholds, 1):
            if lower <= avg < upper or (vespa_score == 10 and avg >= lower):
                return vespa_score
        
        return 1  # Default to 1 if something goes wrong
    
    def generate_student_record(self, desired_vespa_scores: Dict[str, int], 
                              student_name: str = None,
                              generation_method: str = 'realistic') -> Dict:
        """Generate a complete student record with statement scores"""
        statement_scores = self.generate_statement_scores(desired_vespa_scores, generation_method)
        
        # Create record structure
        record = {
            'student_name': student_name or f"Generated_Student_{random.randint(1000, 9999)}",
            'vespa_scores': desired_vespa_scores,
            'statement_scores': {},
            'statement_averages': {},
            'verified_vespa_scores': {}
        }
        
        # Add statement scores and verify calculations
        for category, scores in statement_scores.items():
            record['statement_scores'][category] = scores
            record['statement_averages'][category] = round(sum(scores) / len(scores), 2)
            record['verified_vespa_scores'][category] = self.verify_vespa_calculation(category, scores)
        
        # Calculate overall VESPA score
        vespa_values = list(desired_vespa_scores.values())
        record['vespa_scores']['OVERALL'] = round(sum(vespa_values) / len(vespa_values), 1)
        
        # If we have question mappings, create detailed response record
        if self.questions_by_category:
            record['detailed_responses'] = self._create_detailed_responses(statement_scores)
        
        return record
    
    def _create_detailed_responses(self, statement_scores: Dict[str, List[int]]) -> List[Dict]:
        """Create detailed response records for each question"""
        responses = []
        
        for category, scores in statement_scores.items():
            if category in self.questions_by_category:
                questions = self.questions_by_category[category]
                for i, (question, score) in enumerate(zip(questions[:len(scores)], scores)):
                    response = {
                        'questionId': question['questionId'],
                        'questionText': question['questionText'],
                        'vespaCategory': category,
                        'score': score,
                        'fieldId': question.get('currentCycleFieldId', f'field_{category}_{i}')
                    }
                    responses.append(response)
        
        return responses
    
    def batch_generate_students(self, num_students: int, 
                              vespa_distribution: str = 'normal',
                              generation_method: str = 'realistic') -> List[Dict]:
        """Generate multiple student records with specified VESPA score distribution"""
        students = []
        
        for i in range(num_students):
            # Generate VESPA scores based on distribution
            if vespa_distribution == 'normal':
                # Normal distribution centered on 5.5
                vespa_scores = {}
                for category in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']:
                    score = int(np.random.normal(5.5, 1.5))
                    score = max(1, min(10, score))  # Clip to 1-10
                    vespa_scores[category] = score
            elif vespa_distribution == 'uniform':
                # Uniform distribution across all scores
                vespa_scores = {
                    category: random.randint(1, 10) 
                    for category in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']
                }
            elif vespa_distribution == 'high_performers':
                # Skewed towards high scores
                vespa_scores = {}
                for category in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']:
                    score = int(np.random.normal(7.5, 1.2))
                    score = max(1, min(10, score))
                    vespa_scores[category] = score
            elif vespa_distribution == 'low_performers':
                # Skewed towards low scores
                vespa_scores = {}
                for category in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']:
                    score = int(np.random.normal(3.5, 1.2))
                    score = max(1, min(10, score))
                    vespa_scores[category] = score
            else:
                raise ValueError(f"Unknown distribution: {vespa_distribution}")
            
            student = self.generate_student_record(
                vespa_scores, 
                f"Student_{i+1}",
                generation_method
            )
            students.append(student)
        
        return students


# Example usage functions
def example_single_student():
    """Example: Generate a single student with specific VESPA scores"""
    calculator = ReverseVESPACalculator()
    
    # Define desired VESPA scores
    desired_scores = {
        'VISION': 7,
        'EFFORT': 8,
        'SYSTEMS': 6,
        'PRACTICE': 7,
        'ATTITUDE': 9
    }
    
    # Generate student record
    student = calculator.generate_student_record(desired_scores, "John Doe", "realistic")
    
    print("\n=== Single Student Generation ===")
    print(f"Student: {student['student_name']}")
    print(f"\nDesired VESPA Scores: {student['vespa_scores']}")
    print(f"\nGenerated Statement Averages:")
    for cat, avg in student['statement_averages'].items():
        print(f"  {cat}: {avg}")
    print(f"\nVerified VESPA Scores: {student['verified_vespa_scores']}")
    print(f"\nStatement Scores by Category:")
    for cat, scores in student['statement_scores'].items():
        print(f"  {cat}: {scores}")
    
    return student


def example_batch_generation():
    """Example: Generate multiple students with different distributions"""
    calculator = ReverseVESPACalculator()
    
    print("\n=== Batch Student Generation ===")
    
    # Generate different cohorts
    distributions = ['normal', 'high_performers', 'low_performers']
    
    for dist in distributions:
        students = calculator.batch_generate_students(5, dist, 'realistic')
        
        print(f"\n{dist.upper()} Distribution (5 students):")
        for student in students:
            vespa_avg = student['vespa_scores']['OVERALL']
            print(f"  {student['student_name']}: Overall VESPA = {vespa_avg}")


def example_comparison():
    """Example: Compare different generation methods"""
    calculator = ReverseVESPACalculator()
    
    desired_scores = {
        'VISION': 5,
        'EFFORT': 5,
        'SYSTEMS': 5,
        'PRACTICE': 5,
        'ATTITUDE': 5
    }
    
    print("\n=== Generation Method Comparison ===")
    print("Target VESPA scores: all 5s")
    
    methods = ['balanced', 'random', 'realistic']
    
    for method in methods:
        student = calculator.generate_student_record(desired_scores, f"Test_{method}", method)
        print(f"\n{method.upper()} Method:")
        for cat, scores in student['statement_scores'].items():
            avg = student['statement_averages'][cat]
            print(f"  {cat}: {scores} (avg: {avg})")


def save_generated_students_to_file(students: List[Dict], filename: str):
    """Save generated students to a JSON file"""
    with open(filename, 'w') as f:
        json.dump(students, f, indent=2)
    print(f"\nSaved {len(students)} students to {filename}")


if __name__ == "__main__":
    # Run examples
    print("VESPA Reverse Calculator - Generating Statement Scores from VESPA Scores")
    print("=" * 70)
    
    # Single student example
    student = example_single_student()
    
    # Batch generation example
    example_batch_generation()
    
    # Compare generation methods
    example_comparison()
    
    # Generate and save a larger batch
    calculator = ReverseVESPACalculator()
    large_batch = calculator.batch_generate_students(50, 'normal', 'realistic')
    save_generated_students_to_file(large_batch, 'generated_students.json') 