"""
Forward VESPA Calculator
Calculates VESPA scores (1-10) from questionnaire statement scores (1-5).
Reads from CSV with responses and outputs VESPA scores to Trend columns.
"""

import csv
import pandas as pd
from typing import Dict, List, Tuple

class ForwardVESPACalculator:
    def __init__(self):
        # Define the VESPA score thresholds for each category
        # Each tuple contains (lower_bound, upper_bound) for the average statement score
        # that maps to VESPA scores 1-10
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
                (4.79, 5.01)    # VESPA 10 (upper bound slightly above 5 to include 5.0)
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
                (4.8, 5.01)     # VESPA 10
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
                (4.94, 5.01)    # VESPA 10
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
                (4.3, 5.01)     # VESPA 10
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
                (4.7, 5.01)     # VESPA 10
            ]
        }
        
        # Question mapping (0-indexed positions after email column)
        # Based on VESPA category definitions
        self.question_mapping = {
            'VISION': [0, 2, 28],  # Goals, career planning, grades
            'EFFORT': [3, 5, 8, 10, 20],  # Hard work, completing tasks, deadlines
            'SYSTEMS': [1, 11, 14, 17, 21],  # Organization, planning, study methods
            'PRACTICE': [6, 18, 22, 24],  # Revision techniques, testing, practice
            'ATTITUDE': [4, 7, 9, 12, 13, 15, 16, 19, 23, 25, 26, 27, 29, 30, 31]  # Mindset, confidence, resilience
        }
    
    def calculate_vespa_score(self, statement_scores: List[float], category: str) -> int:
        """
        Calculate VESPA score (1-10) from average of statement scores
        
        Args:
            statement_scores: List of statement scores (1-5)
            category: VESPA category name
            
        Returns:
            VESPA score (1-10)
        """
        if not statement_scores or all(s is None or s == '' for s in statement_scores):
            return None
        
        # Filter out None and empty values
        valid_scores = [float(s) for s in statement_scores if s is not None and s != '']
        
        if not valid_scores:
            return None
            
        avg = sum(valid_scores) / len(valid_scores)
        
        # Find which VESPA score this average maps to
        thresholds = self.vespa_thresholds[category]
        for vespa_score, (lower, upper) in enumerate(thresholds, 1):
            if lower <= avg < upper:
                return vespa_score
            # Special case for exactly 5.0 or above
            if vespa_score == 10 and avg >= lower:
                return vespa_score
        
        return 1  # Default to 1 if below all thresholds
    
    def process_csv(self, input_file: str, output_file: str = None):
        """
        Process CSV file with questionnaire responses and calculate VESPA scores
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output CSV file (if None, overwrites input file)
        """
        # Read CSV
        df = pd.read_csv(input_file)
        
        print(f"Processing {len(df)} rows from {input_file}")
        print(f"Columns found: {len(df.columns)}")
        
        # Get the column indices for responses (after VESPA Customer and Email)
        # Assuming first 2 columns are VESPA Customer and Email
        response_start_col = 2
        
        # Count how many response columns we have
        # Find where VTrend column starts (or where responses end)
        trend_cols = ['VTrend', 'ETrend', 'STrend', 'PTrend', 'ATrend', 'OTrend']
        
        # Check if trend columns exist, if not create them
        for col in trend_cols:
            if col not in df.columns:
                df[col] = ''
        
        # Process each row
        processed_count = 0
        for idx, row in df.iterrows():
            # Skip header row or rows without responses
            if idx == 0 or pd.isna(row.iloc[response_start_col]):
                continue
            
            # Extract all response values (columns 2 onwards until trend columns)
            responses = []
            for col_idx in range(response_start_col, len(df.columns) - 6):  # -6 for trend columns
                val = row.iloc[col_idx]
                if pd.isna(val) or val == '':
                    responses.append(None)
                else:
                    try:
                        responses.append(float(val))
                    except:
                        responses.append(None)
            
            # Skip if no valid responses
            if all(r is None for r in responses):
                continue
            
            # Calculate VESPA scores for each category
            vespa_scores = {}
            
            for category in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']:
                # Get question indices for this category
                question_indices = self.question_mapping.get(category, [])
                
                # Extract scores for this category
                category_scores = []
                for q_idx in question_indices:
                    if q_idx < len(responses):
                        category_scores.append(responses[q_idx])
                
                # Calculate VESPA score
                vespa_score = self.calculate_vespa_score(category_scores, category)
                vespa_scores[category] = vespa_score
            
            # Calculate overall VESPA score (average of all categories)
            valid_vespa_scores = [v for v in vespa_scores.values() if v is not None]
            if valid_vespa_scores:
                overall_score = round(sum(valid_vespa_scores) / len(valid_vespa_scores), 1)
            else:
                overall_score = None
            
            # Update trend columns
            df.at[idx, 'VTrend'] = vespa_scores.get('VISION', '')
            df.at[idx, 'ETrend'] = vespa_scores.get('EFFORT', '')
            df.at[idx, 'STrend'] = vespa_scores.get('SYSTEMS', '')
            df.at[idx, 'PTrend'] = vespa_scores.get('PRACTICE', '')
            df.at[idx, 'ATrend'] = vespa_scores.get('ATTITUDE', '')
            df.at[idx, 'OTrend'] = overall_score if overall_score else ''
            
            processed_count += 1
            
            # Print progress
            email = row.iloc[1] if len(row) > 1 else 'Unknown'
            print(f"Processed {email}: V={vespa_scores.get('VISION', 'N/A')}, "
                  f"E={vespa_scores.get('EFFORT', 'N/A')}, "
                  f"S={vespa_scores.get('SYSTEMS', 'N/A')}, "
                  f"P={vespa_scores.get('PRACTICE', 'N/A')}, "
                  f"A={vespa_scores.get('ATTITUDE', 'N/A')}, "
                  f"Overall={overall_score if overall_score else 'N/A'}")
        
        # Save to output file
        if output_file is None:
            output_file = input_file
        
        df.to_csv(output_file, index=False)
        print(f"\n✓ Processed {processed_count} students")
        print(f"✓ Results saved to {output_file}")
        
        return df


def main():
    """Main function to run the calculator"""
    calculator = ForwardVESPACalculator()
    
    # Process the Bedales responses (overwrites original file)
    input_file = 'Bedalesresponses.csv'
    
    try:
        result_df = calculator.process_csv(input_file, input_file)
        print("\n" + "="*60)
        print("VESPA Score Calculation Complete!")
        print("Original file updated with VESPA scores.")
        print("="*60)
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

