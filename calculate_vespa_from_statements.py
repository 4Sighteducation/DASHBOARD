"""
Calculate VESPA Scores from Statement Responses
This script fetches Object_29 records from Knack, calculates VESPA scores from statement responses,
and exports the data to CSV format.
"""

import os
import sys
import json
import csv
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Knack API credentials
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
KNACK_API_URL = "https://api.knack.com/v1/objects"

if not KNACK_APP_ID or not KNACK_API_KEY:
    print("Error: Please set KNACK_APP_ID and KNACK_API_KEY in your .env file")
    sys.exit(1)

class VESPACalculator:
    def __init__(self):
        # Load question mappings
        self.load_question_mappings()
        
        # Define VESPA score thresholds (from reverse calculator)
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
        
    def load_question_mappings(self):
        """Load psychometric question details"""
        try:
            with open('AIVESPACoach/psychometric_question_details.json', 'r') as f:
                self.questions = json.load(f)
                
            # Group questions by VESPA category and cycle
            self.questions_by_category = {}
            self.field_mappings = {}
            
            for q in self.questions:
                if q['vespaCategory'] == 'NA_OUTCOME':
                    continue  # Skip outcome questions
                    
                category = q['vespaCategory']
                if category not in self.questions_by_category:
                    self.questions_by_category[category] = []
                    
                self.questions_by_category[category].append({
                    'questionId': q['questionId'],
                    'questionText': q['questionText'],
                    'cycle1_field': q.get('fieldIdCycle1'),
                    'cycle2_field': q.get('fieldIdCycle2'),
                    'cycle3_field': q.get('fieldIdCycle3')
                })
                
                # Store field mappings for easy lookup
                self.field_mappings[q.get('fieldIdCycle1')] = (category, q['questionId'], 1)
                self.field_mappings[q.get('fieldIdCycle2')] = (category, q['questionId'], 2)
                self.field_mappings[q.get('fieldIdCycle3')] = (category, q['questionId'], 3)
                
            print(f"Loaded {len(self.questions)} questions")
            for category, questions in self.questions_by_category.items():
                print(f"  {category}: {len(questions)} questions")
                
        except Exception as e:
            print(f"Error loading question mappings: {e}")
            sys.exit(1)
    
    def calculate_vespa_score(self, category: str, average: float) -> int:
        """Calculate VESPA score (1-10) from statement average (1-5)"""
        if category not in self.vespa_thresholds:
            return 0
            
        thresholds = self.vespa_thresholds[category]
        for vespa_score, (lower, upper) in enumerate(thresholds, 1):
            if lower <= average < upper or (vespa_score == 10 and average >= lower):
                return vespa_score
        return 1

def make_knack_request(object_key: str, filters: List = None, page: int = 1, 
                      rows_per_page: int = 1000) -> Dict:
    """Make a request to Knack API"""
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    
    url = f"{KNACK_API_URL}/{object_key}/records"
    params = {
        'page': page,
        'rows_per_page': rows_per_page
    }
    
    if filters:
        params['filters'] = json.dumps(filters)
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def fetch_all_establishments() -> List[Dict]:
    """Fetch all establishments from Object_2 (no filtering)"""
    print("\nFetching establishments from Knack...")
    all_establishments = []
    page = 1
    
    while True:
        data = make_knack_request('object_2', page=page)
        records = data.get('records', [])
        
        if not records:
            break
            
        all_establishments.extend(records)
        
        if len(records) < 1000:
            break
            
        page += 1
    
    print(f"Found {len(all_establishments)} establishments")
    return all_establishments

def select_establishments(establishments: List[Dict]) -> List[Dict]:
    """Interactive establishment selection (supports multiple)"""
    # Sort establishments by name
    establishments.sort(key=lambda x: x.get('field_44', '').lower())
    
    selected_establishments = []
    
    print("\n" + "="*60)
    print("ESTABLISHMENT SELECTION")
    print("="*60)
    print("You can select multiple establishments. Choose 'Done' when finished.")
    
    while True:
        if selected_establishments:
            print(f"\nCurrently selected ({len(selected_establishments)}):")
            for est in selected_establishments:
                print(f"  - {est.get('field_44', 'Unknown')} [{est.get('field_2209', 'Active')}]")
        
        print("\nSearch options:")
        print("1. Search by name")
        print("2. List all establishments")
        print("3. Enter establishment ID directly")
        if selected_establishments:
            print("4. Clear selections")
            print("5. Done - Process selected establishments")
        print("0. Exit")
        
        choice = input(f"\nSelect option (0-{5 if selected_establishments else 3}): ").strip()
        
        if choice == '0':
            return []
            
        elif choice == '1':
            search_term = input("Enter search term: ").strip().lower()
            matches = [e for e in establishments 
                      if search_term in e.get('field_44', '').lower()
                      and e not in selected_establishments]
            
            if not matches:
                print("No matching establishments found (or already selected)")
                continue
                
            print(f"\nFound {len(matches)} matching establishment(s):")
            for i, est in enumerate(matches[:20], 1):  # Show max 20 results
                status = est.get('field_2209', 'Active')
                print(f"{i:3}. {est.get('field_44', 'Unknown')} [{status}]")
            
            if len(matches) > 20:
                print(f"     ... and {len(matches) - 20} more")
                
            selections = input("\nSelect numbers (comma-separated, or 'all' for all matches): ").strip()
            
            if selections.lower() == 'all':
                selected_establishments.extend(matches)
                print(f"Added {len(matches)} establishments")
            else:
                for sel in selections.split(','):
                    sel = sel.strip()
                    if sel.isdigit() and 1 <= int(sel) <= len(matches):
                        est = matches[int(sel) - 1]
                        if est not in selected_establishments:
                            selected_establishments.append(est)
                            print(f"Added: {est.get('field_44')}")
                    
        elif choice == '2':
            available = [e for e in establishments if e not in selected_establishments]
            print(f"\nAvailable establishments ({len(available)} total):")
            print("(Showing first 50, use search for specific establishments)")
            for i, est in enumerate(available[:50], 1):
                status = est.get('field_2209', 'Active')
                print(f"{i:3}. {est.get('field_44', 'Unknown')} [{status}]")
            
            selections = input("\nSelect numbers (comma-separated, or 0 to go back): ").strip()
            
            if selections != '0':
                for sel in selections.split(','):
                    sel = sel.strip()
                    if sel.isdigit() and 1 <= int(sel) <= min(50, len(available)):
                        est = available[int(sel) - 1]
                        selected_establishments.append(est)
                        print(f"Added: {est.get('field_44')}")
                        
        elif choice == '3':
            est_ids = input("Enter establishment ID(s) (comma-separated): ").strip()
            for est_id in est_ids.split(','):
                est_id = est_id.strip()
                matching = [e for e in establishments if e['id'] == est_id]
                if matching and matching[0] not in selected_establishments:
                    selected_establishments.append(matching[0])
                    print(f"Added: {matching[0].get('field_44')}")
                elif not matching:
                    print(f"No establishment found with ID: {est_id}")
                    
        elif choice == '4' and selected_establishments:
            selected_establishments.clear()
            print("Selections cleared")
            
        elif choice == '5' and selected_establishments:
            return selected_establishments

def fetch_object29_records(establishment_id: str) -> List[Dict]:
    """Fetch all Object_29 records for an establishment"""
    print(f"\nFetching Object_29 records for establishment {establishment_id}...")
    
    filters = [
        {
            'field': 'field_1821',  # Establishment connection field
            'operator': 'is',
            'value': establishment_id
        }
    ]
    
    all_records = []
    page = 1
    
    while True:
        data = make_knack_request('object_29', filters=filters, page=page)
        records = data.get('records', [])
        
        if not records:
            break
            
        all_records.extend(records)
        
        if len(records) < 1000:
            break
            
        page += 1
    
    print(f"Found {len(all_records)} Object_29 records")
    return all_records

def analyze_cycles(record: Dict, debug: bool = False) -> Tuple[List[int], Dict]:
    """Determine which cycles have data and extract cycle data"""
    cycles_present = []
    cycle_data = {}
    
    # Check each cycle for data
    cycle_checks = {
        1: 'field_1953',
        2: 'field_1955',
        3: 'field_1956'
    }
    
    if debug:
        email = record.get('field_2732', '') or record.get('field_2732_raw', '')
        print(f"\n  DEBUG - Analyzing cycles for {email}:")
    
    for cycle_num, field_id in cycle_checks.items():
        # Check multiple ways - field itself, _raw version, and check for actual question data
        field_value = record.get(field_id)
        field_raw = record.get(f"{field_id}_raw")
        
        # Also check if there's actual question data for this cycle
        has_question_data = False
        if cycle_num == 1:
            # Check a sample field from cycle 1 (q1 field_1953)
            has_question_data = bool(record.get('field_1953_raw')) or bool(record.get('field_1953'))
        elif cycle_num == 2:
            # Check a sample field from cycle 2 (q1 field_1955)
            has_question_data = bool(record.get('field_1955_raw')) or bool(record.get('field_1955'))
        elif cycle_num == 3:
            # Check a sample field from cycle 3 (q1 field_1956)
            has_question_data = bool(record.get('field_1956_raw')) or bool(record.get('field_1956'))
        
        if debug:
            print(f"    Cycle {cycle_num} ({field_id}): value={field_value}, raw={field_raw}, has_data={has_question_data}")
        
        # Consider cycle present if field exists and has value, or if there's question data
        if field_value or field_raw or has_question_data:
            cycles_present.append(cycle_num)
            cycle_data[cycle_num] = True
            
    if debug:
        print(f"    Result: cycles_present = {cycles_present}")
            
    return cycles_present, cycle_data

def extract_statement_scores(record: Dict, calculator: VESPACalculator) -> Dict:
    """Extract statement scores for each cycle"""
    scores_by_cycle = {}
    
    # Process each question
    for question in calculator.questions:
        if question['vespaCategory'] == 'NA_OUTCOME':
            continue
            
        # Check each cycle's field
        for cycle_num, field_key in [(1, 'fieldIdCycle1'), (2, 'fieldIdCycle2'), (3, 'fieldIdCycle3')]:
            field_id = question.get(field_key)
            if not field_id:
                continue
                
            # Get raw value (numeric score)
            raw_field = f"{field_id}_raw"
            if raw_field in record and record[raw_field]:
                try:
                    score = int(record[raw_field])
                    
                    # Initialize cycle dict if needed
                    if cycle_num not in scores_by_cycle:
                        scores_by_cycle[cycle_num] = {}
                    
                    # Initialize category dict if needed
                    category = question['vespaCategory']
                    if category not in scores_by_cycle[cycle_num]:
                        scores_by_cycle[cycle_num][category] = []
                    
                    # Add score
                    scores_by_cycle[cycle_num][category].append(score)
                    
                    # Also store individual question response
                    question_key = f"c{cycle_num}q{question['questionId'].replace('q', '')}"
                    if cycle_num not in scores_by_cycle:
                        scores_by_cycle[cycle_num] = {}
                    scores_by_cycle[cycle_num][question_key] = score
                    
                except (ValueError, TypeError):
                    pass  # Skip invalid scores
                    
    return scores_by_cycle

def calculate_vespa_scores_for_cycles(scores_by_cycle: Dict, calculator: VESPACalculator) -> Dict:
    """Calculate VESPA scores for each cycle"""
    vespa_by_cycle = {}
    
    for cycle_num, cycle_scores in scores_by_cycle.items():
        vespa_by_cycle[cycle_num] = {}
        
        # Calculate VESPA score for each category
        for category in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']:
            if category in cycle_scores and isinstance(cycle_scores[category], list):
                scores = cycle_scores[category]
                if scores:
                    average = sum(scores) / len(scores)
                    vespa_score = calculator.calculate_vespa_score(category, average)
                    vespa_by_cycle[cycle_num][category] = vespa_score
                else:
                    vespa_by_cycle[cycle_num][category] = None
            else:
                vespa_by_cycle[cycle_num][category] = None
        
        # Calculate overall VESPA
        valid_scores = [v for v in vespa_by_cycle[cycle_num].values() if v is not None]
        if valid_scores:
            vespa_by_cycle[cycle_num]['OVERALL'] = round(sum(valid_scores) / len(valid_scores), 1)
        else:
            vespa_by_cycle[cycle_num]['OVERALL'] = None
            
    return vespa_by_cycle

def process_establishment_data(establishment: Dict, min_cycles_required: int = 2) -> List[Dict]:
    """Process all Object_29 records for an establishment
    
    Args:
        establishment: The establishment record
        min_cycles_required: Minimum number of cycles required (1 or 2)
    """
    calculator = VESPACalculator()
    
    # Fetch Object_29 records
    records = fetch_object29_records(establishment['id'])
    
    if not records:
        print(f"  No Object_29 records found for {establishment.get('field_44', 'Unknown')}")
        return []
    
    # Process each record
    results = []
    students_with_required_cycles = 0
    students_with_1_cycle = 0
    students_with_2_cycles = 0
    students_with_3_cycles = 0
    
    for record in records:
        # Get student email
        email = record.get('field_2732', '') or record.get('field_2732_raw', '')
        if not email:
            continue
            
        # Check which cycles have data
        cycles_present, _ = analyze_cycles(record)
        
        # Count cycle distribution
        if len(cycles_present) == 1:
            students_with_1_cycle += 1
        elif len(cycles_present) == 2:
            students_with_2_cycles += 1
        elif len(cycles_present) == 3:
            students_with_3_cycles += 1
            
        # Skip if less than required cycles
        if len(cycles_present) < min_cycles_required:
            continue
            
        students_with_required_cycles += 1
        
        # Extract statement scores
        scores_by_cycle = extract_statement_scores(record, calculator)
        
        # Calculate VESPA scores
        vespa_by_cycle = calculate_vespa_scores_for_cycles(scores_by_cycle, calculator)
        
        # Determine which cycles to use
        if min_cycles_required == 1 and len(cycles_present) == 1:
            # Single cycle mode - use the one available
            selected_cycles = cycles_present
        elif len(cycles_present) >= 2:
            # Multiple cycles available
            if 1 in cycles_present and 3 in cycles_present:
                selected_cycles = [1, 3]
            else:
                selected_cycles = sorted(cycles_present)[:2]
        else:
            selected_cycles = cycles_present
        
        # Build result row
        result = {
            'establishment': establishment.get('field_44', 'Unknown'),
            'email': email,
            'cycles_present': ','.join(map(str, cycles_present)),
            'cycles_used': ','.join(map(str, selected_cycles))
        }
        
        # Add VESPA scores for selected cycles
        for i, cycle_num in enumerate(selected_cycles[:2], 1):
            if cycle_num in vespa_by_cycle:
                vespa_scores = vespa_by_cycle[cycle_num]
                result[f'V{i}'] = vespa_scores.get('VISION', '')
                result[f'E{i}'] = vespa_scores.get('EFFORT', '')
                result[f'S{i}'] = vespa_scores.get('SYSTEMS', '')
                result[f'P{i}'] = vespa_scores.get('PRACTICE', '')
                result[f'A{i}'] = vespa_scores.get('ATTITUDE', '')
                result[f'O{i}'] = vespa_scores.get('OVERALL', '')
            else:
                # Fill with empty values if cycle missing
                for cat in ['V', 'E', 'S', 'P', 'A', 'O']:
                    result[f'{cat}{i}'] = ''
        
        # If only one cycle, fill second cycle columns with empty values
        if len(selected_cycles) == 1:
            for cat in ['V', 'E', 'S', 'P', 'A', 'O']:
                result[f'{cat}2'] = ''
        
        # Add all individual question scores
        for question in calculator.questions:
            if question['vespaCategory'] == 'NA_OUTCOME':
                continue
                
            question_num = question['questionId'].replace('q', '').replace('_vision_grades', '29')
            
            # Add scores for each cycle
            for cycle_num in [1, 2, 3]:
                field_key = f"fieldIdCycle{cycle_num}"
                field_id = question.get(field_key)
                
                if field_id:
                    raw_field = f"{field_id}_raw"
                    col_name = f"c{cycle_num}q{question_num}"
                    
                    if raw_field in record and record[raw_field]:
                        try:
                            result[col_name] = int(record[raw_field])
                        except:
                            result[col_name] = ''
                    else:
                        result[col_name] = ''
        
        results.append(result)
    
    # Print summary for this establishment
    print(f"  {establishment.get('field_44', 'Unknown')}:")
    print(f"    - 1 cycle: {students_with_1_cycle} students")
    print(f"    - 2 cycles: {students_with_2_cycles} students")
    print(f"    - 3 cycles: {students_with_3_cycles} students")
    print(f"    - Included in export: {students_with_required_cycles} students")
    
    return results

def export_to_csv(results: List[Dict], description: str, is_multi_establishment: bool = False):
    """Export results to CSV file
    
    Args:
        results: List of result dictionaries
        description: Description for filename (establishment name or "multiple")
        is_multi_establishment: Whether this contains data from multiple establishments
    """
    if not results:
        print("No data to export")
        return
        
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = "".join(c for c in description if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"vespa_calculations_{safe_name}_{timestamp}.csv"
    
    # Define column order
    columns = []
    if is_multi_establishment:
        columns.append('establishment')  # Add establishment column if multiple
    columns.extend(['email', 'cycles_present', 'cycles_used',
                   'V1', 'E1', 'S1', 'P1', 'A1', 'O1',
                   'V2', 'E2', 'S2', 'P2', 'A2', 'O2'])
    
    # Add question columns (29 questions x 3 cycles)
    for cycle in [1, 2, 3]:
        for q in range(1, 30):
            columns.append(f'c{cycle}q{q}')
    
    # Write CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\nData exported to: {filename}")
    print(f"Total records: {len(results)}")
    
    # Show summary statistics
    if results:
        # Establishment summary if multiple
        if is_multi_establishment:
            est_count = {}
            for r in results:
                est = r.get('establishment', 'Unknown')
                if est in est_count:
                    est_count[est] += 1
                else:
                    est_count[est] = 1
            
            print("\nRecords by establishment:")
            for est, count in sorted(est_count.items()):
                print(f"  {est}: {count} students")
        
        # Cycle distribution
        cycles_count = {}
        for r in results:
            cycles = r.get('cycles_present', '')
            if cycles in cycles_count:
                cycles_count[cycles] += 1
            else:
                cycles_count[cycles] = 1
        
        print("\nOverall cycle distribution:")
        for cycles, count in sorted(cycles_count.items()):
            print(f"  Cycles {cycles}: {count} students")

def main():
    print("\n" + "="*60)
    print("VESPA CALCULATOR FROM STATEMENT RESPONSES")
    print("="*60)
    
    # Fetch all establishments
    establishments = fetch_all_establishments()
    
    if not establishments:
        print("No establishments found")
        return
    
    # Select establishments (now supports multiple)
    selected_establishments = select_establishments(establishments)
    
    if not selected_establishments:
        print("\nNo establishments selected. Exiting.")
        return
    
    # Ask about cycle requirements
    print("\n" + "="*60)
    print("CYCLE REQUIREMENTS")
    print("="*60)
    print("How many cycles of data should students have?")
    print("1. Two or more cycles only (default)")
    print("2. Include single cycle data")
    
    cycle_choice = input("\nSelect option (1-2) [default: 1]: ").strip()
    
    if cycle_choice == '2':
        min_cycles_required = 1
        print("Including students with 1+ cycles")
    else:
        min_cycles_required = 2
        print("Including students with 2+ cycles only")
    
    # Ask about file output if multiple establishments
    combine_files = True
    if len(selected_establishments) > 1:
        print("\n" + "="*60)
        print("OUTPUT OPTIONS")
        print("="*60)
        print("How would you like to export the data?")
        print("1. Combined - All establishments in one file")
        print("2. Separate - Individual file for each establishment")
        
        output_choice = input("\nSelect option (1-2) [default: 1]: ").strip()
        combine_files = output_choice != '2'
    
    # Process establishments
    print("\n" + "="*60)
    print("PROCESSING ESTABLISHMENTS")
    print("="*60)
    
    all_results = []
    establishment_results = {}
    
    for establishment in selected_establishments:
        print(f"\nProcessing: {establishment.get('field_44', 'Unknown')}")
        results = process_establishment_data(establishment, min_cycles_required)
        
        if results:
            establishment_results[establishment['id']] = results
            all_results.extend(results)
    
    # Export to CSV
    if combine_files and len(selected_establishments) > 1:
        # Combined export
        if all_results:
            export_to_csv(all_results, "multiple_establishments", is_multi_establishment=True)
            print("\nProcessing complete!")
        else:
            print("\nNo data found for selected establishments")
    else:
        # Separate exports
        for establishment in selected_establishments:
            est_id = establishment['id']
            if est_id in establishment_results and establishment_results[est_id]:
                export_to_csv(establishment_results[est_id], 
                            establishment.get('field_44', 'Unknown'),
                            is_multi_establishment=False)
        
        if any(establishment_results.values()):
            print("\nProcessing complete!")
        else:
            print("\nNo data found for selected establishments")

if __name__ == "__main__":
    main()
