"""
Knack VESPA Automation Script
Automatically generates and adds Object_29 records for students with missing statement scores
by reading their VESPA scores from Object_10 and using the reverse calculator.
"""

import json
import requests
from typing import Dict, List, Optional, Tuple
from reverse_vespa_calculator import ReverseVESPACalculator
import time
from datetime import datetime

class KnackVESPAAutomation:
    def __init__(self, app_id: str, api_key: str):
        """
        Initialize the Knack automation with API credentials
        
        Args:
            app_id: Your Knack application ID
            api_key: Your Knack API key
        """
        self.app_id = app_id
        self.api_key = api_key
        self.base_url = f"https://api.knack.com/v1/objects"
        self.headers = {
            'X-Knack-Application-Id': app_id,
            'X-Knack-REST-API-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        # Initialize the reverse calculator
        self.calculator = ReverseVESPACalculator()
        
        # Load question mappings
        with open('AIVESPACoach/psychometric_question_output_object_120.json', 'r') as f:
            self.question_mappings = json.load(f)
            
        # Create lookup dictionaries for field mappings
        self.create_field_mappings()
        
    def create_field_mappings(self):
        """Create lookup dictionaries for easy field access"""
        self.vespa_to_questions = {}
        self.cycle_field_mappings = {1: {}, 2: {}, 3: {}}
        
        for question in self.question_mappings:
            if question['vespaCategory'] != 'NA_OUTCOME':
                vespa_cat = question['vespaCategory']
                if vespa_cat not in self.vespa_to_questions:
                    self.vespa_to_questions[vespa_cat] = []
                self.vespa_to_questions[vespa_cat].append(question)
                
                # Map question IDs to field IDs for each cycle
                self.cycle_field_mappings[1][question['questionId']] = question['fieldIdCycle1']
                self.cycle_field_mappings[2][question['questionId']] = question['fieldIdCycle2']
                self.cycle_field_mappings[3][question['questionId']] = question['fieldIdCycle3']
    
    def find_student_by_email(self, email: str) -> Optional[Dict]:
        """
        Find a student record in Object_10 by email
        
        Args:
            email: Student email address
            
        Returns:
            Student record from Object_10 or None if not found
        """
        # Search Object_10 for the student
        url = f"{self.base_url}/object_10/records"
        
        # Use filters to find by email (adjust field name as needed)
        filters = {
            'match': 'and',
            'rules': [
                {
                    'field': 'field_email',  # Adjust this field ID to match your email field in Object_10
                    'operator': 'is',
                    'value': email
                }
            ]
        }
        
        params = {'filters': json.dumps(filters)}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data['records']:
                return data['records'][0]  # Return first matching record
            else:
                print(f"No record found for email: {email}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error finding student {email}: {e}")
            return None
    
    def extract_vespa_scores(self, student_record: Dict) -> Dict[int, Dict[str, int]]:
        """
        Extract VESPA scores from Object_10 record for all available cycles
        
        Args:
            student_record: Student record from Object_10
            
        Returns:
            Dict mapping cycle number to VESPA scores
        """
        vespa_scores_by_cycle = {}
        
        # Field mappings for VESPA scores in Object_10
        # Adjust these field IDs to match your actual Object_10 structure
        vespa_field_mappings = {
            1: {  # Cycle 1: V1-O1
                'VISION': 'field_V1',
                'EFFORT': 'field_E1',
                'SYSTEMS': 'field_S1',
                'PRACTICE': 'field_P1',
                'ATTITUDE': 'field_A1',
                'OVERALL': 'field_O1'
            },
            2: {  # Cycle 2: V2-O2
                'VISION': 'field_V2',
                'EFFORT': 'field_E2',
                'SYSTEMS': 'field_S2',
                'PRACTICE': 'field_P2',
                'ATTITUDE': 'field_A2',
                'OVERALL': 'field_O2'
            },
            3: {  # Cycle 3: V3-O3
                'VISION': 'field_V3',
                'EFFORT': 'field_E3',
                'SYSTEMS': 'field_S3',
                'PRACTICE': 'field_P3',
                'ATTITUDE': 'field_A3',
                'OVERALL': 'field_O3'
            }
        }
        
        # Extract scores for each cycle
        for cycle, field_map in vespa_field_mappings.items():
            cycle_scores = {}
            has_scores = False
            
            for vespa_cat, field_id in field_map.items():
                if field_id in student_record and student_record[field_id]:
                    score = int(student_record[field_id])
                    if vespa_cat != 'OVERALL':  # Skip overall for generation
                        cycle_scores[vespa_cat] = score
                    has_scores = True
            
            if has_scores and len(cycle_scores) == 5:  # All 5 VESPA categories present
                vespa_scores_by_cycle[cycle] = cycle_scores
                
        return vespa_scores_by_cycle
    
    def check_existing_object_29_records(self, student_email: str) -> Tuple[List[int], Optional[str]]:
        """
        Check which cycles already have Object_29 records for this student
        
        Args:
            student_email: Student email
            
        Returns:
            Tuple of (List of cycle numbers that already have records, record ID if exists)
        """
        url = f"{self.base_url}/object_29/records"
        
        filters = {
            'match': 'and',
            'rules': [
                {
                    'field': 'field_2732',  # Email field in Object_29
                    'operator': 'is',
                    'value': student_email
                }
            ]
        }
        
        params = {'filters': json.dumps(filters)}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            existing_cycles = []
            record_id = None
            
            # Check which cycles have data
            if data['records']:
                record = data['records'][0]  # Should only be one record per student
                record_id = record.get('id')
                
                # Check for cycle 1 data
                if any(field in record and record[field] for field in ['field_3309', 'field_3312', 'field_3315']):
                    existing_cycles.append(1)
                # Check for cycle 2 data
                if any(field in record and record[field] for field in ['field_3310', 'field_3313', 'field_3316']):
                    existing_cycles.append(2)
                # Check for cycle 3 data
                if any(field in record and record[field] for field in ['field_3311', 'field_3314', 'field_3317']):
                    existing_cycles.append(3)
            
            return existing_cycles, record_id
            
        except requests.exceptions.RequestException as e:
            print(f"Error checking existing records: {e}")
            return [], None
    
    def create_object_29_record(self, student_record: Dict, student_email: str, 
                              vespa_scores_by_cycle: Dict[int, Dict[str, int]]) -> bool:
        """
        Create Object_29 record with generated statement scores
        
        Args:
            student_record: Original student record from Object_10
            student_email: Student email
            vespa_scores_by_cycle: VESPA scores for each cycle
            
        Returns:
            True if successful, False otherwise
        """
        # Check which cycles already exist and get record ID if exists
        existing_cycles, existing_record_id = self.check_existing_object_29_records(student_email)
        
        # Get list of cycles to process (excluding existing ones)
        cycles_to_process = []
        for cycle in sorted(vespa_scores_by_cycle.keys()):
            if cycle not in existing_cycles:
                cycles_to_process.append(cycle)
        
        if not cycles_to_process:
            print(f"  No new cycles to process for {student_email}")
            return True
        
        print(f"  Cycles to process: {cycles_to_process}")
        print(f"  Existing record ID: {existing_record_id}")
        
        # Determine if we need to create or update
        if existing_record_id:
            # UPDATE existing record
            print(f"\n  Updating existing record {existing_record_id} with new cycles...")
            record_id = existing_record_id
            
            # Process each new cycle
            for cycle in cycles_to_process:
                print(f"\n  Updating record for Cycle {cycle}...")
                
                # Prepare update data
                update_data = {
                    'field_863': str(cycle),  # Update cycle field
                }
                
                # Generate statement scores for this cycle
                vespa_scores = vespa_scores_by_cycle[cycle]
                print(f"  DEBUG - VESPA scores for cycle {cycle}: {vespa_scores}")
                
                statement_scores = self.calculator.generate_statement_scores(
                    vespa_scores, 
                    generation_method='realistic'
                )
                
                # Map scores to currentCycleFieldId fields
                for vespa_cat, scores in statement_scores.items():
                    questions = self.vespa_to_questions.get(vespa_cat, [])
                    
                    for i, (question, score) in enumerate(zip(questions, scores)):
                        field_id = question.get('currentCycleFieldId')
                        if field_id:
                            update_data[field_id] = str(score)
                
                # Add outcome questions (set to 3 for all)
                update_data['field_801'] = '3'
                update_data['field_802'] = '3'
                update_data['field_803'] = '3'
                
                # Add VESPA scores if this is the highest cycle
                highest_cycle = max(vespa_scores_by_cycle.keys())
                if cycle == highest_cycle:
                    print(f"  Adding VESPA scores from highest cycle {highest_cycle}")
                    update_data['field_857'] = str(vespa_scores.get('VISION', ''))
                    update_data['field_858'] = str(vespa_scores.get('EFFORT', ''))
                    update_data['field_859'] = str(vespa_scores.get('SYSTEMS', ''))
                    update_data['field_861'] = str(vespa_scores.get('PRACTICE', ''))
                    update_data['field_860'] = str(vespa_scores.get('ATTITUDE', ''))
                    # Calculate overall
                    vespa_values = [vespa_scores.get(cat, 0) for cat in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']]
                    overall = round(sum(vespa_values) / len(vespa_values), 1)
                    update_data['field_862'] = str(overall)
                
                # Update the record
                update_url = f"{self.base_url}/object_29/records/{record_id}"
                
                try:
                    update_response = requests.put(update_url, headers=self.headers, json=update_data)
                    update_response.raise_for_status()
                    
                    print(f"  Successfully updated record for Cycle {cycle}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"  Error updating record for Cycle {cycle}: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"  Response: {e.response.text}")
                    return False
            
            print(f"\n  Completed updating existing record for {student_email}")
            return True
            
        else:
            # CREATE new record (existing logic)
            first_cycle = cycles_to_process[0]
            print(f"\n  Creating new record with Cycle {first_cycle}...")
        
        # Build the initial record with connected fields and first cycle
        new_record = {
            'field_2732': student_email,  # Email field
            'field_863': str(first_cycle),  # Cycle field
            'field_1823': student_record.get('field_187', ''),  # User name from Object_10
            'field_792': [student_record.get('id')],  # Connection to Object_10 record
        }
        
        # Add connected fields from Object_10
        connected_field_mappings = {
            'field_133': 'field_1821',  # VESPA Customer (Object_10 -> Object_29)
            'field_439': 'field_2069',  # Staff Admin (Object_10 -> Object_29)
            'field_145': 'field_2070'   # Tutors (Object_10 -> Object_29)
        }
        
        for source_field, target_field in connected_field_mappings.items():
            if source_field in student_record and student_record[source_field]:
                connection_data = student_record[source_field]
                
                if isinstance(connection_data, list):
                    if connection_data and isinstance(connection_data[0], dict):
                        new_record[target_field] = [item.get('id', item) for item in connection_data]
                    else:
                        new_record[target_field] = connection_data
                else:
                    new_record[target_field] = [connection_data]
        
        # Generate and add statement scores for the first cycle using currentCycleFieldId
        vespa_scores = vespa_scores_by_cycle[first_cycle]
        print(f"  DEBUG - VESPA scores for cycle {first_cycle}: {vespa_scores}")
        
        statement_scores = self.calculator.generate_statement_scores(
            vespa_scores, 
            generation_method='realistic'
        )
        
        print(f"  DEBUG - Generated statement scores:")
        for cat, scores in statement_scores.items():
            print(f"    {cat}: {scores}")
        
        # Map scores to currentCycleFieldId fields (not cycle-specific fields)
        for vespa_cat, scores in statement_scores.items():
            questions = self.vespa_to_questions.get(vespa_cat, [])
            
            for i, (question, score) in enumerate(zip(questions, scores)):
                # Use currentCycleFieldId instead of cycle-specific field
                field_id = question.get('currentCycleFieldId')
                if field_id:
                    new_record[field_id] = str(score)
                    print(f"    Setting {field_id} = {score}")
        
        # Add outcome questions (set to 3 for all)
        new_record['field_801'] = '3'  # Outcome question 1
        new_record['field_802'] = '3'  # Outcome question 2
        new_record['field_803'] = '3'  # Outcome question 3
        print(f"    Setting outcome questions (801, 802, 803) = 3")
        
        # Add VESPA scores if this is the highest cycle
        highest_cycle = max(vespa_scores_by_cycle.keys())
        if first_cycle == highest_cycle:
            print(f"  Adding VESPA scores from highest cycle {highest_cycle}")
            new_record['field_857'] = str(vespa_scores.get('VISION', ''))
            new_record['field_858'] = str(vespa_scores.get('EFFORT', ''))
            new_record['field_859'] = str(vespa_scores.get('SYSTEMS', ''))
            new_record['field_861'] = str(vespa_scores.get('PRACTICE', ''))
            new_record['field_860'] = str(vespa_scores.get('ATTITUDE', ''))
            # Calculate overall
            vespa_values = [vespa_scores.get(cat, 0) for cat in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']]
            overall = round(sum(vespa_values) / len(vespa_values), 1)
            new_record['field_862'] = str(overall)
        
        cycles_processed = [first_cycle]
        
        # Create the record in Object_29
        url = f"{self.base_url}/object_29/records"
        
        print(f"\n  Creating initial record...")
        print(f"  - Cycle: {first_cycle}")
        print(f"  - Fields being sent: {len(new_record)}")
        print(f"  - User name: {new_record.get('field_1823')}")
        print(f"  - Object_10 connection: {new_record.get('field_792')}")
        
        try:
            response = requests.post(url, headers=self.headers, json=new_record)
            response.raise_for_status()
            
            created_record = response.json()
            record_id = created_record.get('id')
            print(f"  Successfully created Object_29 record ID: {record_id}")
            
            # Now update the record for additional cycles
            for cycle in cycles_to_process[1:]:
                print(f"\n  Updating record for Cycle {cycle}...")
                
                # Prepare update data
                update_data = {
                    'field_863': str(cycle),  # Update cycle field
                }
                
                # Generate statement scores for this cycle
                vespa_scores = vespa_scores_by_cycle[cycle]
                print(f"  DEBUG - VESPA scores for cycle {cycle}: {vespa_scores}")
                
                statement_scores = self.calculator.generate_statement_scores(
                    vespa_scores, 
                    generation_method='realistic'
                )
                
                # Map scores to currentCycleFieldId fields
                for vespa_cat, scores in statement_scores.items():
                    questions = self.vespa_to_questions.get(vespa_cat, [])
                    
                    for i, (question, score) in enumerate(zip(questions, scores)):
                        field_id = question.get('currentCycleFieldId')
                        if field_id:
                            update_data[field_id] = str(score)
                
                # Add outcome questions (set to 3 for all)
                update_data['field_801'] = '3'  # Outcome question 1
                update_data['field_802'] = '3'  # Outcome question 2
                update_data['field_803'] = '3'  # Outcome question 3
                
                # Add VESPA scores if this is the highest cycle
                highest_cycle = max(vespa_scores_by_cycle.keys())
                if cycle == highest_cycle:
                    print(f"  Adding VESPA scores from highest cycle {highest_cycle}")
                    update_data['field_857'] = str(vespa_scores.get('VISION', ''))
                    update_data['field_858'] = str(vespa_scores.get('EFFORT', ''))
                    update_data['field_859'] = str(vespa_scores.get('SYSTEMS', ''))
                    update_data['field_861'] = str(vespa_scores.get('PRACTICE', ''))
                    update_data['field_860'] = str(vespa_scores.get('ATTITUDE', ''))
                    # Calculate overall
                    vespa_values = [vespa_scores.get(cat, 0) for cat in ['VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE']]
                    overall = round(sum(vespa_values) / len(vespa_values), 1)
                    update_data['field_862'] = str(overall)
                
                # Update the record
                update_url = f"{self.base_url}/object_29/records/{record_id}"
                
                try:
                    update_response = requests.put(update_url, headers=self.headers, json=update_data)
                    update_response.raise_for_status()
                    
                    print(f"  Successfully updated record for Cycle {cycle}")
                    cycles_processed.append(cycle)
                    
                except requests.exceptions.RequestException as e:
                    print(f"  Error updating record for Cycle {cycle}: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"  Response: {e.response.text}")
            
            print(f"\n  Completed processing for {student_email}")
            print(f"  Processed cycles: {cycles_processed}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"  Error creating Object_29 record: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text}")
            return False
    
    def process_student_list(self, student_emails: List[str], dry_run: bool = False) -> Dict:
        """
        Process a list of student emails
        
        Args:
            student_emails: List of student email addresses
            dry_run: If True, only simulate without creating records
            
        Returns:
            Summary of processing results
        """
        results = {
            'processed': 0,
            'created': 0,
            'failed': 0,
            'not_found': 0,
            'details': []
        }
        
        print(f"\nProcessing {len(student_emails)} students...")
        if dry_run:
            print("DRY RUN MODE - No records will be created")
        
        for i, email in enumerate(student_emails, 1):
            print(f"\n[{i}/{len(student_emails)}] Processing {email}...")
            
            # Find student in Object_10
            student_record = self.find_student_by_email(email)
            
            if not student_record:
                results['not_found'] += 1
                results['details'].append({
                    'email': email,
                    'status': 'not_found',
                    'message': 'Student not found in Object_10'
                })
                continue
            
            # Extract VESPA scores
            vespa_scores = self.extract_vespa_scores(student_record)
            
            if not vespa_scores:
                results['failed'] += 1
                results['details'].append({
                    'email': email,
                    'status': 'no_vespa_scores',
                    'message': 'No VESPA scores found in Object_10'
                })
                continue
            
            print(f"  Found VESPA scores for cycles: {list(vespa_scores.keys())}")
            
            if not dry_run:
                # Create Object_29 record
                success = self.create_object_29_record(student_record, email, vespa_scores)
                
                if success:
                    results['created'] += 1
                    results['details'].append({
                        'email': email,
                        'status': 'success',
                        'cycles': list(vespa_scores.keys())
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'email': email,
                        'status': 'failed',
                        'message': 'Failed to create Object_29 record'
                    })
            else:
                # Dry run - show what would actually be done
                existing_cycles, existing_record_id = self.check_existing_object_29_records(email)
                new_cycles = [c for c in vespa_scores.keys() if c not in existing_cycles]
                
                if existing_record_id:
                    print(f"  Existing record found with cycles: {existing_cycles}")
                    if new_cycles:
                        print(f"  Would UPDATE existing record with cycles: {new_cycles}")
                    else:
                        print(f"  All cycles already exist - no action needed")
                else:
                    print(f"  No existing record found")
                    print(f"  Would CREATE new record with cycles: {new_cycles}")
                
                results['details'].append({
                    'email': email,
                    'status': 'dry_run',
                    'existing_cycles': existing_cycles,
                    'new_cycles': new_cycles,
                    'existing_record_id': existing_record_id
                })
            
            results['processed'] += 1
            
            # Rate limiting - adjust as needed for your Knack plan
            time.sleep(0.5)
        
        return results
    
    def generate_summary_report(self, results: Dict) -> str:
        """Generate a summary report of the processing results"""
        report = f"""
VESPA Automation Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

Total Students Processed: {results['processed']}
Records Created: {results['created']}
Students Not Found: {results['not_found']}
Failed: {results['failed']}

Detailed Results:
"""
        
        for detail in results['details']:
            email = detail['email']
            status = detail['status']
            
            if status == 'success':
                report += f"\n✓ {email} - Created records for cycles: {detail['cycles']}"
            elif status == 'not_found':
                report += f"\n✗ {email} - Not found in Object_10"
            elif status == 'no_vespa_scores':
                report += f"\n✗ {email} - No VESPA scores in Object_10"
            elif status == 'failed':
                report += f"\n✗ {email} - Failed to create record"
            elif status == 'dry_run':
                if detail.get('existing_record_id'):
                    if detail.get('new_cycles'):
                        report += f"\n• {email} - Would UPDATE existing record with cycles: {detail['new_cycles']} (existing cycles: {detail['existing_cycles']})"
                    else:
                        report += f"\n• {email} - All cycles already exist, no action needed (existing cycles: {detail['existing_cycles']})"
                else:
                    report += f"\n• {email} - Would CREATE new record with cycles: {detail['new_cycles']}"
        
        return report


def main():
    """Main function to run the automation"""
    # Configuration
    APP_ID = "your-app-id"  # Replace with your Knack app ID
    API_KEY = "your-api-key"  # Replace with your Knack API key
    
    # Example student emails
    student_emails = [
        "student1@example.com",
        "student2@example.com",
        "student3@example.com"
    ]
    
    # Initialize automation
    automation = KnackVESPAAutomation(APP_ID, API_KEY)
    
    # First, do a dry run to see what would happen
    print("\n" + "="*50)
    print("STARTING DRY RUN")
    print("="*50)
    
    dry_run_results = automation.process_student_list(student_emails, dry_run=True)
    
    # Show dry run report
    print(automation.generate_summary_report(dry_run_results))
    
    # Ask for confirmation
    response = input("\nProceed with creating records? (yes/no): ")
    
    if response.lower() == 'yes':
        print("\n" + "="*50)
        print("CREATING RECORDS")
        print("="*50)
        
        # Process for real
        results = automation.process_student_list(student_emails, dry_run=False)
        
        # Generate and save report
        report = automation.generate_summary_report(results)
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"vespa_automation_report_{timestamp}.txt"
        
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_filename}")
        
        # Also save detailed results as JSON
        results_filename = f"vespa_automation_results_{timestamp}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Detailed results saved to: {results_filename}")


if __name__ == "__main__":
    main() 