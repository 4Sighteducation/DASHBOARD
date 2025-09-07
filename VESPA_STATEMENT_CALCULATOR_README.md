# VESPA Calculator from Statement Responses

## Overview

This script calculates VESPA scores from Object_29 statement responses in the Knack database. It's the inverse of the reverse calculator - instead of generating statement scores from VESPA scores, it calculates VESPA scores from actual statement responses.

## Features

- **Interactive Establishment Selection**: Search and select establishments by name
- **Multiple Establishment Support**: Process multiple schools in one run
- **Flexible Cycle Requirements**: Choose between 2+ cycles only or include single cycle data
- **Multi-Cycle Support**: Automatically identifies students with 1, 2, or 3 cycles of data
- **VESPA Calculation**: Converts statement averages (1-5) to VESPA scores (1-10)
- **Flexible Export Options**: Combined or separate CSV files for multiple establishments
- **Comprehensive Export**: CSV output with VESPA scores and all individual statement responses

## Prerequisites

1. Set up your `.env` file with:
   ```
   KNACK_APP_ID=your_app_id
   KNACK_API_KEY=your_api_key
   ```

2. Ensure `psychometric_question_details.json` exists in the `AIVESPACoach/` folder

## Usage

1. **Run the script**:
   ```bash
   python calculate_vespa_from_statements.py
   ```

2. **Select establishments**:
   - Option 1: Search by name (partial match supported)
   - Option 2: Browse all establishments
   - Option 3: Enter establishment ID directly
   - **NEW**: Select multiple establishments (comma-separated or 'all' for search results)
   - Continue adding until done, then choose option 5

3. **Choose cycle requirements**:
   - Option 1: Two or more cycles only (default)
   - Option 2: Include single cycle data

4. **Select output format** (if multiple establishments):
   - Option 1: Combined - All establishments in one file
   - Option 2: Separate - Individual file for each establishment

5. **Review results**:
   - The script shows cycle distribution for each establishment
   - Data is automatically exported to CSV

## How It Works

### Data Flow

1. **Fetches all establishments** from Object_2 (no filtering)
2. **Queries Object_29** records using field_1821 (establishment connection)
3. **Identifies valid students** with data in at least 2 cycles:
   - Cycle 1: field_1953
   - Cycle 2: field_1955
   - Cycle 3: field_1956
4. **Extracts statement scores** for each question (29 questions total)
5. **Calculates VESPA scores** using established thresholds

### VESPA Score Calculation

For each VESPA category (Vision, Effort, Systems, Practice, Attitude):
1. Averages the statement scores for questions in that category
2. Maps the average to a VESPA score (1-10) using threshold ranges
3. Calculates Overall VESPA as the average of all 5 categories

### Cycle Selection Logic

Depends on your cycle requirement setting:

**Two or more cycles mode (default)**:
- **3 cycles available**: Uses cycles 1 and 3 (start and end)
- **2 cycles available**: Uses both available cycles
- **1 cycle only**: Student is skipped

**Include single cycle mode**:
- **3 cycles available**: Uses cycles 1 and 3 (start and end)
- **2 cycles available**: Uses both available cycles
- **1 cycle only**: Uses the single available cycle (V2, E2, etc. columns will be empty)

## Output Format

The CSV file contains:

### Summary Columns
- `establishment`: Establishment name (only included when multiple establishments are combined)
- `email`: Student email address
- `cycles_present`: Which cycles have data (e.g., "1,2,3")
- `cycles_used`: Which cycles were used for VESPA calculation

### VESPA Score Columns
- `V1, E1, S1, P1, A1, O1`: First cycle's VESPA scores
- `V2, E2, S2, P2, A2, O2`: Second cycle's VESPA scores

### Statement Response Columns
- `c1q1` to `c1q29`: Cycle 1 individual responses
- `c2q1` to `c2q29`: Cycle 2 individual responses
- `c3q1` to `c3q29`: Cycle 3 individual responses

## Example Output

```
email,cycles_present,cycles_used,V1,E1,S1,P1,A1,O1,V2,E2,S2,P2,A2,O2,c1q1,c1q2...
student@school.edu,1,3,1,3,7,8,6,5,6,5.8,9,9,7,6,8,7.8,4,3,5...
```

## VESPA Score Thresholds

The script uses your established threshold ranges to map statement averages to VESPA scores:

| VESPA Score | Vision | Effort | Systems | Practice | Attitude |
|-------------|--------|--------|---------|----------|----------|
| 1 | < 2.26 | < 2.42 | < 2.36 | < 1.74 | < 2.31 |
| 2 | 2.26-2.70 | 2.42-2.73 | 2.36-2.76 | 1.74-2.10 | 2.31-2.72 |
| 3 | 2.70-3.02 | 2.73-3.04 | 2.76-3.16 | 2.10-2.46 | 2.72-3.01 |
| ... | ... | ... | ... | ... | ... |
| 10 | > 4.79 | > 4.80 | > 4.94 | > 4.30 | > 4.70 |

## Troubleshooting

### No establishments found
- Check your Knack API credentials in `.env`
- Verify network connection

### No Object_29 records found
- Verify the establishment has students who completed surveys
- Check that field_1821 is the correct establishment connection field

### Missing question mappings
- Ensure `AIVESPACoach/psychometric_question_details.json` exists
- Verify the file contains all 29 questions with field mappings

## Notes

- The script does NOT filter out cancelled establishments (as requested)
- Cycle requirement is configurable (1+ or 2+ cycles)
- VESPA scores are calculated independently for each cycle
- Overall VESPA (O) is the average of the 5 category scores

## New Features (Latest Update)

### Multiple Establishment Selection
- Select and process multiple establishments in a single run
- Search results can be added with comma-separated numbers or 'all'
- Clear and restart selection at any time

### Single Cycle Support
- Option to include students with only one cycle of data
- Useful for establishments with limited multi-cycle data
- Second cycle columns will be empty for single-cycle students

### Flexible Export Options
- **Combined mode**: All establishments in one CSV with an 'establishment' column
- **Separate mode**: Individual CSV file for each establishment
- Filename includes establishment name and timestamp for easy identification
