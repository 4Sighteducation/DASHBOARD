# Reverse VESPA Calculator

## Overview

The Reverse VESPA Calculator generates plausible statement scores (1-5 Likert scale) from desired VESPA scores (1-10). This is useful when you need to add students who have VESPA scores but no Object_29 records (statement responses).

## How It Works

The calculator uses your existing VESPA calculation algorithms in reverse:

1. **Input**: Desired VESPA scores (1-10) for each category
2. **Process**: Finds the average statement score range that maps to each VESPA score
3. **Output**: Individual statement scores (1-5) that would produce those VESPA scores

### VESPA Score Mappings

Based on your algorithms:

- **VISION**: 5 statements
  - VESPA 1: average < 2.26
  - VESPA 2: 2.26 ≤ average < 2.7
  - VESPA 3: 2.7 ≤ average < 3.02
  - ... and so on

- **EFFORT**: 4 statements
- **SYSTEMS**: 5 statements  
- **PRACTICE**: 6 statements
- **ATTITUDE**: 9 statements

## Usage

### Basic Usage

```python
from reverse_vespa_calculator import ReverseVESPACalculator

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
student = calculator.generate_student_record(desired_scores, "John Doe")
```

### Running the Examples

1. **Test the calculator**:
   ```bash
   python reverse_vespa_calculator.py
   ```

2. **Add students without surveys**:
   ```bash
   python add_missing_students.py
   ```

## Generation Methods

The calculator offers three methods for generating statement scores:

1. **Balanced**: Creates evenly distributed scores around the target average
2. **Random**: Uses normal distribution to create more varied scores
3. **Realistic** (recommended): Creates natural-looking score patterns that mirror real student responses

## Output Files

Running the scripts will generate:

- `generated_students.json`: Complete student records with all scores
- `generated_student_records.json`: Records from the add_missing_students script
- `knack_import_data.json`: Data formatted for Knack import

## Important Notes

1. **Approximation**: The generated statement scores are approximations. They won't reflect actual student opinions but will produce the correct VESPA scores.

2. **Verification**: The calculator verifies that generated statement scores produce the expected VESPA scores.

3. **Flexibility**: You can generate individual students or entire classes with different performance distributions.

## Integration with Your Dashboard

The generated data can be:
- Imported into Knack as Object_29 records
- Used to test your dashboard with students who lack survey responses
- Mixed with real data to fill gaps in your dataset

## Customization

You can modify:
- Number of questions per category (in `load_question_mappings`)
- Score generation patterns (in `_generate_realistic_scores`)
- Output formats (in `create_knack_import_format`) 