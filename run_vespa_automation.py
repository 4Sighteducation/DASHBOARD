"""
Simple script to run VESPA automation for students missing Object_29 records
"""

import json
import sys
import os
from datetime import datetime
from typing import List

# Import the automation class
from knack_vespa_automation import KnackVESPAAutomation

# Try to import configuration
try:
    import knack_config as config
except ImportError:
    print("ERROR: knack_config.py not found!")
    print("Please copy knack_config_example.py to knack_config.py and fill in your values.")
    sys.exit(1)


def load_emails_from_file(filename: str) -> List[str]:
    """Load email addresses from a text file (one per line)"""
    emails = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                email = line.strip()
                if email and '@' in email:  # Basic validation
                    emails.append(email)
        return emails
    except FileNotFoundError:
        print(f"ERROR: File '{filename}' not found!")
        return []


def get_student_emails() -> List[str]:
    """Get student emails from user input"""
    print("\nHow would you like to provide student emails?")
    print("1. Type/paste emails manually")
    print("2. Load from a text file")
    print("3. Use test data")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        print("\nEnter student emails (one per line, empty line to finish):")
        emails = []
        while True:
            email = input().strip()
            if not email:
                break
            if '@' in email:
                emails.append(email)
            else:
                print(f"Invalid email format: {email}")
        return emails
        
    elif choice == '2':
        filename = input("\nEnter filename containing emails: ").strip()
        emails = load_emails_from_file(filename)
        if emails:
            print(f"Loaded {len(emails)} emails from {filename}")
        return emails
        
    elif choice == '3':
        # Test data
        return [
            "test.student1@example.com",
            "test.student2@example.com",
            "test.student3@example.com"
        ]
    else:
        print("Invalid choice!")
        return []


def create_enhanced_automation():
    """Create an enhanced automation instance with config-based field mappings"""
    
    class ConfiguredKnackVESPAAutomation(KnackVESPAAutomation):
        def find_student_by_email(self, email: str):
            """Override to use configured email field"""
            # Update the base method to use configured field
            url = f"{self.base_url}/object_10/records"
            
            filters = {
                'match': 'and',
                'rules': [
                    {
                        'field': config.OBJECT_10_FIELDS['email'],
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
                    return data['records'][0]
                else:
                    print(f"No record found for email: {email}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"Error finding student {email}: {e}")
                return None
        
        def extract_vespa_scores(self, student_record):
            """Override to use configured field mappings"""
            vespa_scores_by_cycle = {}
            
            # Use configured field mappings
            vespa_field_mappings = {
                1: config.OBJECT_10_FIELDS['cycle_1'],
                2: config.OBJECT_10_FIELDS['cycle_2'],
                3: config.OBJECT_10_FIELDS['cycle_3']
            }
            
            # Extract scores for each cycle
            for cycle, field_map in vespa_field_mappings.items():
                cycle_scores = {}
                has_scores = False
                
                for vespa_cat, field_id in field_map.items():
                    if field_id in student_record and student_record[field_id]:
                        try:
                            score = int(student_record[field_id])
                            if vespa_cat != 'OVERALL':  # Skip overall for generation
                                cycle_scores[vespa_cat] = score
                            has_scores = True
                        except (ValueError, TypeError):
                            print(f"  Warning: Invalid score value for {vespa_cat} in cycle {cycle}")
                
                if has_scores and len(cycle_scores) == 5:  # All 5 VESPA categories present
                    vespa_scores_by_cycle[cycle] = cycle_scores
                    
            return vespa_scores_by_cycle
        
        def create_object_29_record(self, student_record, student_email, vespa_scores_by_cycle):
            """Override to use configured connected fields"""
            # Check which cycles already exist
            existing_cycles, existing_record_id = self.check_existing_object_29_records(student_email)
            
            # Build the record (cycle field will be added later)
            new_record = {
                'field_2732': student_email,  # Email field in Object_29
                'field_1823': student_record.get('field_187', ''),  # User name from Object_10
                'field_792': [student_record.get('id')],  # Connection to Object_10 record
            }
            
            # Add connected fields using configuration
            # These are many-to-many connections, so we need to handle arrays
            for source_field, target_field in config.CONNECTED_FIELDS.items():
                if source_field in student_record and student_record[source_field]:
                    # Knack connections can be arrays of objects or IDs
                    connection_data = student_record[source_field]
                    
                    # If it's already an array of IDs, use it directly
                    if isinstance(connection_data, list):
                        cleaned_ids = []
                        for item in connection_data:
                            if isinstance(item, dict):
                                # Array of objects with 'id' field
                                cleaned_ids.append(item.get('id', item))
                            elif isinstance(item, str) and '<span' in item:
                                # Extract ID from HTML span
                                import re
                                match = re.search(r'class="([a-f0-9]+)"', item)
                                if match:
                                    cleaned_ids.append(match.group(1))
                            else:
                                # Already an ID
                                cleaned_ids.append(str(item))
                        new_record[target_field] = cleaned_ids
                    else:
                        # Single value
                        if isinstance(connection_data, str) and '<span' in connection_data:
                            # Extract ID from HTML
                            import re
                            match = re.search(r'class="([a-f0-9]+)"', connection_data)
                            if match:
                                new_record[target_field] = [match.group(1)]
                        else:
                            new_record[target_field] = [str(connection_data)]
            
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
            
            if existing_record_id:
                # UPDATE existing record - delegate to base class with only new cycles
                # IMPORTANT: Only pass cycles that need to be added, not all cycles
                # This prevents overwriting existing cycle data
                new_cycles_only = {cycle: vespa_scores_by_cycle[cycle] for cycle in cycles_to_process}
                return super().create_object_29_record(student_record, student_email, new_cycles_only)
            
            # CREATE new record
            first_cycle = cycles_to_process[0]
            print(f"\n  Creating new record with Cycle {first_cycle}...")
            
            # Add the cycle field to the record
            new_record['field_863'] = str(first_cycle)  # Cycle field
            
            # Generate and add statement scores for the first cycle using currentCycleFieldId
            vespa_scores = vespa_scores_by_cycle[first_cycle]
            print(f"  DEBUG - VESPA scores for cycle {first_cycle}: {vespa_scores}")
            
            statement_scores = self.calculator.generate_statement_scores(
                vespa_scores, 
                generation_method='realistic'
            )
            
            print(f"  DEBUG - Generated scores: {statement_scores}")
            
            # Map scores to currentCycleFieldId fields (not cycle-specific fields)
            fields_added = 0
            for vespa_cat, scores in statement_scores.items():
                questions = self.vespa_to_questions.get(vespa_cat, [])
                print(f"  DEBUG - {vespa_cat}: {len(questions)} questions, {len(scores)} scores")
                
                for i, (question, score) in enumerate(zip(questions, scores)):
                    # Use currentCycleFieldId instead of cycle-specific field
                    field_id = question.get('currentCycleFieldId')
                    if field_id:
                        # Convert numpy int to regular int, then to string
                        new_record[field_id] = str(int(score))
                        fields_added += 1
                        print(f"    Setting {field_id} = {score}")
                    else:
                        print(f"  WARNING - No currentCycleFieldId for {question['questionId']}")
            
            print(f"  DEBUG - Added {fields_added} statement fields for cycle {first_cycle}")
            
            # Add outcome questions (set to 3 for all)
            new_record['field_801'] = '3'  # Outcome question 1
            new_record['field_802'] = '3'  # Outcome question 2
            new_record['field_803'] = '3'  # Outcome question 3
            print(f"    Setting outcome questions (801, 802, 803) = 3")
            
            # Add VESPA scores if this is the highest cycle
            highest_cycle = max(vespa_scores_by_cycle.keys())
            if first_cycle == highest_cycle:
                print(f"  Adding VESPA scores from highest cycle {highest_cycle}")
                vespa_scores = vespa_scores_by_cycle[first_cycle]
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
            print(f"  - Email: {new_record.get('field_2732')}")
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
                    fields_added = 0
                    for vespa_cat, scores in statement_scores.items():
                        questions = self.vespa_to_questions.get(vespa_cat, [])
                        
                        for i, (question, score) in enumerate(zip(questions, scores)):
                            field_id = question.get('currentCycleFieldId')
                            if field_id:
                                update_data[field_id] = str(int(score))
                                fields_added += 1
                    
                    print(f"  - Updating {fields_added} statement fields")
                    
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
                    print(f"  Response status: {e.response.status_code}")
                    print(f"  Response text: {e.response.text}")
                return False
    
    # Need to import requests for the overridden methods
    import requests
    
    return ConfiguredKnackVESPAAutomation(config.KNACK_APP_ID, config.KNACK_API_KEY)


def main():
    """Main function to run the automation"""
    print("="*60)
    print("VESPA Statement Score Generator for Knack")
    print("="*60)
    
    # Check configuration
    if config.KNACK_APP_ID == "your-app-id-here":
        print("\nERROR: Please update knack_config.py with your actual Knack credentials!")
        sys.exit(1)
    
    # Get student emails
    student_emails = get_student_emails()
    
    if not student_emails:
        print("\nNo emails provided. Exiting.")
        return
    
    print(f"\nFound {len(student_emails)} student emails to process.")
    
    # Initialize automation with enhanced configuration
    automation = create_enhanced_automation()
    
    # Set rate limit from config
    if hasattr(config, 'API_RATE_LIMIT'):
        automation.rate_limit = config.API_RATE_LIMIT
    
    # Ask for dry run
    dry_run = input("\nPerform dry run first? (yes/no) [yes]: ").strip().lower()
    dry_run = dry_run != 'no'  # Default to yes
    
    if dry_run:
        print("\n" + "="*50)
        print("STARTING DRY RUN")
        print("="*50)
        
        dry_run_results = automation.process_student_list(student_emails, dry_run=True)
        
        # Show dry run report
        print(automation.generate_summary_report(dry_run_results))
        
        # Ask for confirmation to proceed
        if dry_run_results['processed'] > 0:
            proceed = input("\nProceed with creating records? (yes/no): ").strip().lower()
            
            if proceed != 'yes':
                print("\nOperation cancelled.")
                return
        else:
            print("\nNo students to process.")
            return
    
    # Process for real
    print("\n" + "="*50)
    print("CREATING RECORDS")
    print("="*50)
    
    results = automation.process_student_list(student_emails, dry_run=False)
    
    # Generate and save report
    report = automation.generate_summary_report(results)
    print(report)
    
    # Save reports
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save text report
    report_filename = f"vespa_automation_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport saved to: {report_filename}")
    
    # Save detailed JSON results
    results_filename = f"vespa_automation_results_{timestamp}.json"
    with open(results_filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Detailed results saved to: {results_filename}")
    
    # Save successful emails for reference
    if results['created'] > 0:
        success_emails = [
            d['email'] for d in results['details'] 
            if d['status'] == 'success'
        ]
        success_filename = f"vespa_automation_success_{timestamp}.txt"
        with open(success_filename, 'w', encoding='utf-8') as f:
            for email in success_emails:
                f.write(email + '\n')
        print(f"Successfully processed emails saved to: {success_filename}")


if __name__ == "__main__":
    main() 