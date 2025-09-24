import os
import requests
import logging
import json # Required for json.dumps in find_target_record_id and other API interactions
from datetime import datetime, date, timedelta # Added timedelta
from pathlib import Path # For robust path handling to JSON files
import math # For statistical calculations
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration from Environment Variables ---
KNACK_APP_ID = os.environ.get("KNACK_APP_ID")
KNACK_API_KEY = os.environ.get("KNACK_API_KEY")
VESPA_SOURCE_OBJECT_KEY = "object_10"      # VESPA Results
PSYCHOMETRIC_SOURCE_OBJECT_KEY = "object_29" # Psychometric Question Scores
TARGET_OBJECT_KEY = "object_120"         # National Averages Data

# Supabase configuration for syncing
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Initialize Supabase client if configured
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Supabase client initialized for syncing national statistics")

# Configuration flag for Overall calculation method
USE_CALCULATED_OVERALL = os.environ.get("USE_CALCULATED_OVERALL", "true").lower() == "true"
if USE_CALCULATED_OVERALL:
    logging.info("Using CALCULATED Overall scores (average of V,E,S,P,A)")
else:
    logging.info("Using STORED Overall scores from field_152")

# --- Field Definitions ---

# VESPA Score fields from object_10
VESPA_CURRENT_CYCLE_FIELD_ID = "field_146"
VESPA_RAW_SCORE_FIELDS = {
    "V": "field_147",
    "E": "field_148",
    "S": "field_149",
    "P": "field_150",
    "A": "field_151",
    "O": "field_152"  # Overall score
}
VESPA_COMPLETED_DATE_FIELD_ID = "field_855"
VESPA_EMAIL_FIELD_ID = "field_197"

# Psychometric Question completed date field from object_29
PSYCHOMETRIC_COMPLETED_DATE_FIELD_ID = "field_856"
PSYCHOMETRIC_EMAIL_FIELD_ID = "field_2732"

# Fields to request (dynamically built later for psychometric)
REQUEST_FIELDS_FROM_VESPA_SOURCE = [
    VESPA_CURRENT_CYCLE_FIELD_ID,
    VESPA_COMPLETED_DATE_FIELD_ID,
    VESPA_EMAIL_FIELD_ID
] + list(VESPA_RAW_SCORE_FIELDS.values())

# Target fields in object_120 (Structure for VESPA and Psychometric)
TARGET_FIELDS_STRUCTURE = {
    "name_base": "field_3290",
    "academic_year": "field_3308",
    "date_time": "field_3307",  # Date/Time field for when the record was last updated
    "vespa_cycle1": {"V": "field_3292", "E": "field_3293", "S": "field_3294", "P": "field_3295", "A": "field_3296", "O": "field_3406"},
    "vespa_cycle2": {"V": "field_3297", "E": "field_3298", "S": "field_3299", "P": "field_3300", "A": "field_3301", "O": "field_3407"},
    "vespa_cycle3": {"V": "field_3302", "E": "field_3303", "S": "field_3304", "P": "field_3305", "A": "field_3306", "O": "field_3408"},
    # Histogram fields for VESPA score distributions (JSON format)
    "vespa_histogram_cycle1": "field_3409",  # distribution_json_cycle1
    "vespa_histogram_cycle2": "field_3410",  # distribution_json_cycle2  
    "vespa_histogram_cycle3": "field_3411",  # distribution_json_cycle3
    # Response count fields
    "vespa_responses_cycle1": "field_3412",  # C1_responses
    "vespa_responses_cycle2": "field_3413",  # C2_responses
    "vespa_responses_cycle3": "field_3414",  # C3_responses
    # Statistics fields (JSON format)
    "vespa_stats_cycle1": "field_3429",  # cycle1_stats
    "vespa_stats_cycle2": "field_3430",  # cycle2_stats
    "vespa_stats_cycle3": "field_3431",  # cycle3_stats
    # Psychometric target fields will be added dynamically from JSON
    "eri_cycle1": "field_3432",
    "eri_cycle2": "field_3433",
    "eri_cycle3": "field_3434",
}
BASE_TARGET_RECORD_NAME = "National VESPA Averages by Cycle"

# --- Path to JSON mapping files (relative to this script in heroku_backend) ---
SCRIPT_DIR = Path(__file__).resolve().parent
PSYCHOMETRIC_DETAILS_JSON_PATH = SCRIPT_DIR / "AIVESPACoach" / "psychometric_question_details.json"
PSYCHOMETRIC_OUTPUT_JSON_PATH = SCRIPT_DIR / "AIVESPACoach" / "psychometric_question_output_object_120.json"

# --- Helper Functions ---

def get_current_academic_year_info():
    """Determines the current academic year (Aug 1 - Jul 31) and its date range."""
    today = date.today()
    current_year = today.year
    if today.month >= 8:
        ay_start_year = current_year
        ay_end_year = current_year + 1
    else:
        ay_start_year = current_year - 1
        ay_end_year = current_year
    
    academic_year_str = f"{ay_start_year}-{ay_end_year}"
    # Actual start and end of the academic period
    start_date_of_ay = date(ay_start_year, 8, 1)
    end_date_of_ay = date(ay_end_year, 7, 31)
    
    logging.info(f"Current Academic Year: {academic_year_str} (Range: {start_date_of_ay.strftime('%Y-%m-%d')} to {end_date_of_ay.strftime('%Y-%m-%d')})")
    # For Knack 'is after date' and 'is before date' filtering to be inclusive:
    # 'is after date' X  => effectively > X (so use day before AY start)
    # 'is before date' Y => effectively < Y (so use day after AY end)
    filter_start_date = start_date_of_ay - timedelta(days=1)
    filter_end_date = end_date_of_ay + timedelta(days=1)
    
    return academic_year_str, filter_start_date, filter_end_date, start_date_of_ay, end_date_of_ay

def get_knack_headers():
    """Returns headers for Knack API requests."""
    if not KNACK_APP_ID or not KNACK_API_KEY:
        logging.error("KNACK_APP_ID or KNACK_API_KEY environment variables not set.")
        raise ValueError("Missing Knack credentials in environment variables.")
    return {
        "X-Knack-Application-Id": KNACK_APP_ID,
        "X-Knack-REST-API-Key": KNACK_API_KEY,
        "Content-Type": "application/json"
    }

def fetch_knack_records_by_page(object_key, fields_to_request, date_filter_field_id, filter_start_date_for_knack=None, filter_end_date_for_knack=None):
    """Fetches records from a Knack object, page by page (as a generator), handling pagination and date filtering."""
    logging.info(f"Initiating paged fetching from Knack object: {object_key}")
    knack_filter_date_format = "%Y-%m-%d"

    if date_filter_field_id and filter_start_date_for_knack and filter_end_date_for_knack:
        logging.info(f"Using Knack API date filters on field {date_filter_field_id}: after {filter_start_date_for_knack.strftime(knack_filter_date_format)} and before {filter_end_date_for_knack.strftime(knack_filter_date_format)}")

    current_page_num = 1
    total_pages = None

    filters = []
    if date_filter_field_id and filter_start_date_for_knack and filter_end_date_for_knack:
        filters.extend([
            {"field": date_filter_field_id, "operator": "is not blank"},
            {"field": date_filter_field_id, "operator": "is after", "value": filter_start_date_for_knack.strftime(knack_filter_date_format)},
            {"field": date_filter_field_id, "operator": "is before", "value": filter_end_date_for_knack.strftime(knack_filter_date_format)}
        ])

    while True:
        params = {
            "page": current_page_num,
            "rows_per_page": 1000, # Adjust as needed, max is 1000
            "fields": ",".join(fields_to_request)
        }
        if filters:
            params["filters"] = json.dumps(filters)

        api_url = f"https://api.knack.com/v1/objects/{object_key}/records"
        response = None
        try:
            logging.debug(f"Fetching page {current_page_num} from {object_key} with params: {params}")
            response = requests.get(api_url, headers=get_knack_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            
            current_page_records = data.get("records", [])
            if not current_page_records and current_page_num == 1 and not data.get("total_pages", 0) > 0 :
                 # No records found at all, even on the first page and total_pages isn't set higher
                logging.info(f"No records found for object {object_key} with current filters.")
                return # Stop generation

            yield current_page_records # Yield the current page of records

            if total_pages is None: # First page successfully fetched
                total_pages = data.get("total_pages", 1)
                logging.info(f"Total pages to fetch for {object_key}: {total_pages}")

            if current_page_num >= total_pages:
                logging.info(f"Finished fetching all {total_pages} pages for {object_key}.")
                break # Exit loop if all pages fetched
            
            current_page_num += 1
            # Minimal logging per page to reduce noise, more detailed if debug needed
            if current_page_num % 5 == 0 or current_page_num == total_pages : # Log every 5 pages or on last page
                 logging.info(f"Fetched page {current_page_num-1}/{total_pages} for {object_key}. Proceeding to page {current_page_num}.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching page {current_page_num} from Knack object {object_key}: {e}")
            if response is not None: logging.error(f"Response: {response.status_code}, {response.text}")
            raise # Re-raise to stop processing
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {object_key} page {current_page_num}: {e}")
            if response is not None: logging.error(f"Response content: {response.text}")
            raise # Re-raise
            
def find_target_record_id(object_key, name_field_id, record_name):
    """Finds the ID of a record in a Knack object by a name field."""
    logging.info(f"Searching for record '{record_name}' in object {object_key} using field {name_field_id}")
    filters = [{
        "field": name_field_id,
        "operator": "is",
        "value": record_name
    }]
    params = {"filters": json.dumps(filters), "rows_per_page": 1}
    api_url = f"https://api.knack.com/v1/objects/{object_key}/records"
    response = None
    try:
        response = requests.get(api_url, headers=get_knack_headers(), params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("records") and len(data["records"]) > 0:
            record_id = data["records"][0]["id"]
            logging.info(f"Found record with ID: {record_id}")
            return record_id
        else:
            logging.info(f"No record found with name '{record_name}'.")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error finding target record in {object_key}: {e}")
        if response is not None:
            logging.error(f"Response status: {response.status_code}, Response content: {response.text}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response while finding target record: {e}")
        if response is not None:
            logging.error(f"Response content causing decode error: {response.text}")
        raise

def update_knack_record(object_key, record_id, payload):
    """Updates an existing record in a Knack object."""
    logging.info(f"Updating record ID {record_id} in object {object_key}.")
    api_url = f"https://api.knack.com/v1/objects/{object_key}/records/{record_id}"
    response = None
    try:
        response = requests.put(api_url, headers=get_knack_headers(), json=payload)
        response.raise_for_status()
        logging.info(f"Successfully updated record ID {record_id}.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating Knack record ID {record_id}: {e}")
        if response is not None:
            logging.error(f"Response status: {response.status_code}, Response content: {response.text}")
        raise

def create_knack_record(object_key, payload):
    """Creates a new record in a Knack object."""
    logging.info(f"Creating new record in object {object_key}.")
    api_url = f"https://api.knack.com/v1/objects/{object_key}/records"
    response = None
    try:
        response = requests.post(api_url, headers=get_knack_headers(), json=payload)
        response.raise_for_status()
        logging.info(f"Successfully created new record. Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error creating Knack record in {object_key}: {e}")
        if response is not None:
            logging.error(f"Response status: {response.status_code}, Response content: {response.text}")
        raise
    except json.JSONDecodeError as e: # If Knack returns non-JSON on successful POST (unlikely but good to catch)
        logging.error(f"Error decoding JSON response after creating record in {object_key}: {e}")
        if response is not None:
            logging.error(f"Response content: {response.text}")
        # Not re-raising here as record might have been created despite bad JSON response

# --- Main Processing Logic ---

def calculate_statistics(scores):
    """Calculate comprehensive statistics for a list of scores."""
    if not scores:
        return {
            "mean": 0,
            "std_dev": 0,
            "min": 0,
            "max": 0,
            "percentile_25": 0,
            "percentile_50": 0,
            "percentile_75": 0,
            "confidence_interval_lower": 0,
            "confidence_interval_upper": 0,
            "skewness": 0,
            "count": 0
        }
    
    n = len(scores)
    sorted_scores = sorted(scores)
    
    # Mean
    mean = sum(scores) / n
    
    # Standard deviation
    variance = sum((x - mean) ** 2 for x in scores) / n
    std_dev = math.sqrt(variance)
    
    # Min and Max
    min_score = min(scores)
    max_score = max(scores)
    
    # Percentiles
    def percentile(sorted_list, p):
        """Calculate percentile using linear interpolation."""
        if not sorted_list:
            return 0
        k = (len(sorted_list) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_list[int(k)]
        d0 = sorted_list[int(f)] * (c - k)
        d1 = sorted_list[int(c)] * (k - f)
        return d0 + d1
    
    percentile_25 = percentile(sorted_scores, 25)
    percentile_50 = percentile(sorted_scores, 50)  # Median
    percentile_75 = percentile(sorted_scores, 75)
    
    # 95% Confidence interval for the mean
    # CI = mean ± 1.96 * (std_dev / sqrt(n))
    margin_of_error = 1.96 * (std_dev / math.sqrt(n)) if n > 1 else 0
    ci_lower = mean - margin_of_error
    ci_upper = mean + margin_of_error
    
    # Skewness (third standardized moment)
    # Skewness = (1/n) * Σ((xi - mean) / std_dev)^3
    if std_dev > 0:
        skewness = sum(((x - mean) / std_dev) ** 3 for x in scores) / n
    else:
        skewness = 0
    
    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "min": round(min_score, 2),
        "max": round(max_score, 2),
        "percentile_25": round(percentile_25, 2),
        "percentile_50": round(percentile_50, 2),
        "percentile_75": round(percentile_75, 2),
        "confidence_interval_lower": round(ci_lower, 2),
        "confidence_interval_upper": round(ci_upper, 2),
        "skewness": round(skewness, 3),
        "count": n
    }

def load_json_mapping(file_path):
    logging.info(f"Loading JSON mapping from: {file_path}")
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"JSON mapping file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {file_path}: {e}")
        raise

def process_vespa_scores(payload_for_target_object, academic_year_str, filter_start_date, filter_end_date):
    logging.info("Processing VESPA scores (batched)...")
    
    vespa_cycle_aggregates = {f"cycle{i}": {comp: {"sum": 0, "count": 0} for comp in VESPA_RAW_SCORE_FIELDS.keys()} for i in range(1, 4)}
    
    # Initialize histogram data structure for score distributions
    vespa_histograms = {
        f"cycle{i}": {
            comp: {str(score): 0 for score in range(1, 11)} 
            for comp in VESPA_RAW_SCORE_FIELDS.keys()
        } 
        for i in range(1, 4)
    }
    
    # Store individual scores for statistical analysis
    vespa_raw_scores = {
        f"cycle{i}": {
            comp: []
            for comp in VESPA_RAW_SCORE_FIELDS.keys()
        }
        for i in range(1, 4)
    }
    
    total_vespa_records_processed = 0
    records_with_cycle_errors = 0
    test_accounts_skipped_vespa = 0
    overall_discrepancy_count = 0  # Track records with Overall score mismatches

    try:
        for page_of_records in fetch_knack_records_by_page(
            VESPA_SOURCE_OBJECT_KEY, 
            REQUEST_FIELDS_FROM_VESPA_SOURCE,
            VESPA_COMPLETED_DATE_FIELD_ID,
            filter_start_date_for_knack=filter_start_date,
            filter_end_date_for_knack=filter_end_date
        ):
            if not page_of_records: continue

            total_vespa_records_processed += len(page_of_records)
            for record in page_of_records:
                record_id_for_logging = record.get('id','N/A')
                try:
                    cycle_num_raw = record.get(f"{VESPA_CURRENT_CYCLE_FIELD_ID}_raw")
                    if cycle_num_raw is None or str(cycle_num_raw).strip() == "": # Check for None or empty/whitespace string
                        logging.debug(f"VESPA: Record {record_id_for_logging} - cycle number is missing or empty. Skipping record for VESPA cycle aggregation.")
                        records_with_cycle_errors += 1
                        continue
                    
                    try:
                        cycle_num = int(cycle_num_raw) 
                    except ValueError:
                        logging.debug(f"VESPA: Record {record_id_for_logging} - cycle number '{cycle_num_raw}' is not a valid integer. Skipping record for VESPA cycle aggregation.")
                        records_with_cycle_errors += 1
                        continue

                    if cycle_num not in [1, 2, 3]:
                        logging.debug(f"VESPA: Record {record_id_for_logging} - cycle number {cycle_num} is not in [1,2,3]. Skipping record for VESPA cycle aggregation.")
                        records_with_cycle_errors += 1
                        continue
                    
                    cycle_key = f"cycle{cycle_num}"

                    # Test account email check
                    email_raw = record.get(f"{VESPA_EMAIL_FIELD_ID}_raw")
                    if email_raw and isinstance(email_raw, str) and "@vespa.academy" in email_raw.lower():
                        logging.debug(f"VESPA: Record {record_id_for_logging} - Skipping test account email: {email_raw}")
                        test_accounts_skipped_vespa += 1
                        continue

                    for component_key, raw_field_id in VESPA_RAW_SCORE_FIELDS.items():
                        # Skip aggregating the stored 'O' score if using calculated overall
                        if component_key == 'O' and USE_CALCULATED_OVERALL:
                            continue

                        score_raw = record.get(f"{raw_field_id}_raw")
                        if score_raw is not None:
                            try:
                                score = float(score_raw)
                                vespa_cycle_aggregates[cycle_key][component_key]["sum"] += score
                                vespa_cycle_aggregates[cycle_key][component_key]["count"] += 1
                                
                                # Add to histogram - round to nearest integer and clamp to 1-10 range
                                score_bucket = max(1, min(10, round(score)))
                                
                                # For Overall histogram when using calculated method, we'll handle it separately
                                if not (component_key == 'O' and USE_CALCULATED_OVERALL):
                                    vespa_histograms[cycle_key][component_key][str(score_bucket)] += 1
                                
                                # Store individual scores for statistical analysis (except Overall if using calculated)
                                if not (component_key == 'O' and USE_CALCULATED_OVERALL):
                                    vespa_raw_scores[cycle_key][component_key].append(score)
                                
                            except (ValueError, TypeError):
                                logging.debug(f"VESPA: Record {record_id_for_logging} has non-numeric score ('{score_raw}') for {component_key}. Skipping score.")
                                continue
                        # else: # Optionally log if a specific score field is missing, though often normal
                        #    logging.debug(f"VESPA: Record {record_id_for_logging} missing score for {component_key}.")
                    
                    # Calculate what Overall SHOULD be based on V,E,S,P,A average
                    vespa_components = ['V', 'E', 'S', 'P', 'A']
                    component_scores = []
                    for comp in vespa_components:
                        comp_score_raw = record.get(f"{VESPA_RAW_SCORE_FIELDS[comp]}_raw")
                        if comp_score_raw is not None:
                            try:
                                comp_score = float(comp_score_raw)
                                component_scores.append(comp_score)
                            except (ValueError, TypeError):
                                pass
                    
                    if len(component_scores) == 5:  # Only if we have all 5 components
                        calculated_overall = sum(component_scores) / len(component_scores)
                        
                        # If using calculated overall, add to histogram using the calculated value
                        if USE_CALCULATED_OVERALL:
                            overall_bucket = max(1, min(10, round(calculated_overall)))
                            vespa_histograms[cycle_key]['O'][str(overall_bucket)] += 1
                            
                            # Also track this for aggregation
                            vespa_cycle_aggregates[cycle_key]['O']["sum"] += calculated_overall
                            vespa_cycle_aggregates[cycle_key]['O']["count"] += 1
                            
                            # Store for statistical analysis
                            vespa_raw_scores[cycle_key]['O'].append(calculated_overall)
                        
                        # Log comparison with stored value (if exists)
                        stored_overall_raw = record.get(f"{VESPA_RAW_SCORE_FIELDS['O']}_raw")
                        if stored_overall_raw is not None:
                            try:
                                stored_overall = float(stored_overall_raw)
                                diff = abs(stored_overall - calculated_overall)
                                if diff > 0.1:  # More than 0.1 difference
                                    logging.debug(f"VESPA: Record {record_id_for_logging} Cycle {cycle_num} - Overall score mismatch. Stored: {stored_overall:.2f}, Calculated: {calculated_overall:.2f}, Diff: {diff:.2f}")
                                    overall_discrepancy_count += 1
                            except (ValueError, TypeError):
                                pass

                except Exception as e_rec:
                    logging.warning(f"VESPA: Unhandled error processing record {record_id_for_logging}: {e_rec}. Skipping record.")
                    records_with_cycle_errors += 1 # Count this as a record that couldn't be fully processed
                    continue
        
        logging.info(f"Finished processing {total_vespa_records_processed} VESPA records. Skipped {test_accounts_skipped_vespa} test accounts. Encountered {records_with_cycle_errors} records with cycle data issues.")
        
        if USE_CALCULATED_OVERALL and overall_discrepancy_count > 0:
            logging.warning(f"Found {overall_discrepancy_count} records with Overall score discrepancies between stored and calculated values.")

    except Exception as e_fetch:
        logging.error(f"Error during VESPA data fetching/page processing: {e_fetch}")
        pass 

    actual_records_for_aggregation_vespa = total_vespa_records_processed - test_accounts_skipped_vespa - records_with_cycle_errors
    if actual_records_for_aggregation_vespa <= 0:
        logging.warning(f"No valid VESPA source records were available for aggregation for academic year {academic_year_str}. VESPA averages will be zero.")
    
    # Calculate and populate averages into the main payload
    for cycle_key_num in range(1, 4):
        vespa_target_cycle_key = f"vespa_cycle{cycle_key_num}"
        source_agg_cycle_key = f"cycle{cycle_key_num}"
        
        # First calculate averages for V, E, S, P, A
        component_averages = {}
        for component_key in ['V', 'E', 'S', 'P', 'A']:
            agg_data = vespa_cycle_aggregates[source_agg_cycle_key][component_key]
            average = (agg_data["sum"] / agg_data["count"]) if agg_data["count"] > 0 else 0.0
            component_averages[component_key] = average
            target_field_id = TARGET_FIELDS_STRUCTURE[vespa_target_cycle_key][component_key]
            payload_for_target_object[target_field_id] = average
            if total_vespa_records_processed > 0:
                logging.info(f"VESPA Average for {vespa_target_cycle_key} {component_key} ({academic_year_str}): {average:.2f} (sum: {agg_data['sum']}, count: {agg_data['count']}) -> {target_field_id}")
            elif not payload_for_target_object.get(target_field_id):
                payload_for_target_object[target_field_id] = 0.0
        
        # Handle Overall score based on configuration
        if USE_CALCULATED_OVERALL:
            # We've already calculated and aggregated Overall scores during record processing
            agg_data = vespa_cycle_aggregates[source_agg_cycle_key]['O']
            average = (agg_data["sum"] / agg_data["count"]) if agg_data["count"] > 0 else 0.0
            target_field_id = TARGET_FIELDS_STRUCTURE[vespa_target_cycle_key]['O']
            payload_for_target_object[target_field_id] = average
            if total_vespa_records_processed > 0 and agg_data["count"] > 0:
                logging.info(f"VESPA Average for {vespa_target_cycle_key} O (CALCULATED) ({academic_year_str}): {average:.2f} (sum: {agg_data['sum']:.2f}, count: {agg_data['count']}) -> {target_field_id}")
            else:
                payload_for_target_object[target_field_id] = 0.0
        else:
            # Use stored Overall from field_152
            agg_data = vespa_cycle_aggregates[source_agg_cycle_key]['O']
            average = (agg_data["sum"] / agg_data["count"]) if agg_data["count"] > 0 else 0.0
            target_field_id = TARGET_FIELDS_STRUCTURE[vespa_target_cycle_key]['O']
            payload_for_target_object[target_field_id] = average
            if total_vespa_records_processed > 0:
                logging.info(f"VESPA Average for {vespa_target_cycle_key} O (STORED) ({academic_year_str}): {average:.2f} (sum: {agg_data['sum']}, count: {agg_data['count']}) -> {target_field_id}")
            elif not payload_for_target_object.get(target_field_id):
                payload_for_target_object[target_field_id] = 0.0
    
    # Convert histogram data to JSON and add to payload
    for cycle_num in range(1, 4):
        cycle_key = f"cycle{cycle_num}"
        histogram_field_key = f"vespa_histogram_cycle{cycle_num}"
        
        # Create histogram JSON structure with proper component names
        histogram_json = {}
        component_name_map = {
            "V": "Vision",
            "E": "Effort", 
            "S": "Systems",
            "P": "Practice",
            "A": "Attitude",
            "O": "Overall"
        }
        
        for component_key, component_name in component_name_map.items():
            histogram_json[component_name] = vespa_histograms[cycle_key][component_key]
        
        # Convert to JSON string and add to payload if field ID exists
        if histogram_field_key in TARGET_FIELDS_STRUCTURE:
            histogram_field_id = TARGET_FIELDS_STRUCTURE[histogram_field_key]
            if histogram_field_id and not histogram_field_id.startswith("field_X"):  # Check if actual field ID is set
                payload_for_target_object[histogram_field_id] = json.dumps(histogram_json, indent=2)
                logging.info(f"Added VESPA histogram data for cycle {cycle_num} to field {histogram_field_id}")
    
    # Add response counts to payload
    for cycle_num in range(1, 4):
        response_count_field_key = f"vespa_responses_cycle{cycle_num}"
        if response_count_field_key in TARGET_FIELDS_STRUCTURE:
            # Get the count from any component (they should all be the same for valid records)
            # Using 'V' as reference, but could use any component
            cycle_key = f"cycle{cycle_num}"
            response_count = vespa_cycle_aggregates[cycle_key]['V']["count"]
            
            response_count_field_id = TARGET_FIELDS_STRUCTURE[response_count_field_key]
            payload_for_target_object[response_count_field_id] = response_count
            logging.info(f"VESPA Response count for Cycle {cycle_num}: {response_count} -> {response_count_field_id}")
    
    # Calculate and store comprehensive statistics
    for cycle_num in range(1, 4):
        stats_field_key = f"vespa_stats_cycle{cycle_num}"
        if stats_field_key in TARGET_FIELDS_STRUCTURE:
            cycle_key = f"cycle{cycle_num}"
            stats_json = {}
            
            # Component name mapping for JSON output
            component_name_map = {
                "V": "Vision",
                "E": "Effort", 
                "S": "Systems",
                "P": "Practice",
                "A": "Attitude",
                "O": "Overall"
            }
            
            # Calculate statistics for each component
            for component_key, component_name in component_name_map.items():
                scores = vespa_raw_scores[cycle_key][component_key]
                stats = calculate_statistics(scores)
                stats_json[component_name] = stats
                
                if scores:  # Only log if there are scores
                    logging.info(f"Statistics for {component_name} Cycle {cycle_num}: "
                               f"Mean={stats['mean']}, SD={stats['std_dev']}, "
                               f"Median={stats['percentile_50']}, "
                               f"25th-75th=[{stats['percentile_25']}-{stats['percentile_75']}]")
            
            # Convert to JSON and store
            stats_field_id = TARGET_FIELDS_STRUCTURE[stats_field_key]
            payload_for_target_object[stats_field_id] = json.dumps(stats_json, indent=2)
            logging.info(f"Added comprehensive statistics for cycle {cycle_num} to field {stats_field_id}")

def process_psychometric_scores(psychometric_details, psychometric_output_mapping, payload_for_target_object, academic_year_str, filter_start_date, filter_end_date):
    logging.info("Processing psychometric question scores (batched)...")

    psychometric_fields_to_request = [PSYCHOMETRIC_COMPLETED_DATE_FIELD_ID, PSYCHOMETRIC_EMAIL_FIELD_ID]
    # Add fields for outcome questions (Support, Equipped, Confident)
    outcome_q_ids = ["outcome_q_support", "outcome_q_equipped", "outcome_q_confident"]
    outcome_field_ids_to_request = set() # Use a set to avoid duplicates, like field_2042

    for q_detail in psychometric_details:
        for c in range(1, 4):
            field_key = f"fieldIdCycle{c}"
            if q_detail.get(field_key) and q_detail[field_key] not in psychometric_fields_to_request:
                psychometric_fields_to_request.append(q_detail[field_key])
            # Collect outcome question field IDs
            if q_detail.get("questionId") in outcome_q_ids and q_detail.get(field_key):
                outcome_field_ids_to_request.add(q_detail[field_key])

    # Add collected outcome field IDs to the main request list if they aren't already there
    for field_id in outcome_field_ids_to_request:
        if field_id not in psychometric_fields_to_request:
            psychometric_fields_to_request.append(field_id)

    question_aggregates = {}
    eri_aggregates = {f"cycle{c}": {"sum": 0, "count": 0} for c in range(1,4)}

    total_psychometric_records_processed = 0
    test_accounts_skipped_psychometric = 0

    try:
        for page_of_records in fetch_knack_records_by_page(
            PSYCHOMETRIC_SOURCE_OBJECT_KEY,
            psychometric_fields_to_request,
            PSYCHOMETRIC_COMPLETED_DATE_FIELD_ID,
            filter_start_date_for_knack=filter_start_date,
            filter_end_date_for_knack=filter_end_date
        ):
            if not page_of_records: continue

            total_psychometric_records_processed += len(page_of_records)
            for record in page_of_records:
                for question_detail in psychometric_details:
                    q_id = question_detail["questionId"]
                    if q_id not in question_aggregates:
                        question_aggregates[q_id] = {f"cycle{c}": {"sum": 0, "count": 0} for c in range(1,4)}
                    
                    for cycle_num in range(1, 4):
                        cycle_key_in_json = f"fieldIdCycle{cycle_num}"
                        source_field_id = question_detail.get(cycle_key_in_json)
                        if not source_field_id: continue

                        score_raw = record.get(f"{source_field_id}_raw")
                        if score_raw is not None:
                            try:
                                score = float(score_raw)
                                question_aggregates[q_id][f"cycle{cycle_num}"]["sum"] += score
                                question_aggregates[q_id][f"cycle{cycle_num}"]["count"] += 1
                            except (ValueError, TypeError):
                                logging.debug(f"Psychometric: Record {record.get('id','N/A')} q_id {q_id} non-numeric for {cycle_key_in_json}")
                                continue 

                # Test account email check
                email_raw = record.get(f"{PSYCHOMETRIC_EMAIL_FIELD_ID}_raw")
                if email_raw and isinstance(email_raw, str) and "@vespa.academy" in email_raw.lower():
                    logging.debug(f"Psychometric: Record {record.get('id','N/A')} - Skipping test account email: {email_raw}")
                    test_accounts_skipped_psychometric += 1
                    continue # Skip this record entirely

                # Calculate and aggregate ERI for this record
                record_id_for_logging = record.get('id','N/A') # Get record ID for logging
                eri_scores_for_record = []
                valid_eri_record = False

                for cycle_num in range(1, 4):
                    cycle_key = f"cycle{cycle_num}"
                    # Find the question details for the outcome questions for this cycle
                    outcome_scores = {}
                    for q_detail in psychometric_details:
                        q_id = q_detail.get("questionId")
                        if q_id in outcome_q_ids:
                            field_key = f"fieldIdCycle{cycle_num}"
                            source_field_id = q_detail.get(field_key)
                            if source_field_id:
                                score_raw = record.get(f"{source_field_id}_raw")
                                if score_raw is not None:
                                    try:
                                        outcome_scores[q_id] = float(score_raw)
                                    except (ValueError, TypeError):
                                        logging.debug(f"Psychometric: Record {record_id_for_logging} Cycle {cycle_num} - Non-numeric score for outcome question {q_id} field {source_field_id}")
                                        pass # Ignore non-numeric scores
                                else:
                                    logging.debug(f"Psychometric: Record {record_id_for_logging} Cycle {cycle_num} - Missing score for outcome question {q_id} field {source_field_id}")
                                    pass # Ignore missing scores

                # Calculate ERI for this cycle if all 3 outcome scores are present
                if len(outcome_scores) == 3:
                    valid_eri_record = True # Mark that at least one cycle had valid ERI scores
                    individual_eri = sum(outcome_scores.values()) / 3.0
                    eri_aggregates[cycle_key]["sum"] += individual_eri
                    eri_aggregates[cycle_key]["count"] += 1
                    logging.debug(f"Psychometric: Record {record_id_for_logging} Cycle {cycle_num} - Calculated ERI: {individual_eri:.2f}")
                elif len(outcome_scores) > 0:
                    logging.debug(f"Psychometric: Record {record_id_for_logging} Cycle {cycle_num} - Not all 3 outcome scores present ({len(outcome_scores)}/3). Skipping ERI calculation for this cycle.")

                if not valid_eri_record:
                    # If no cycle had all 3 outcome questions answered, and it wasn't a test account, log.
                    # We skip logging for test accounts as they might have incomplete data by design.
                    email_raw = record.get(f"{PSYCHOMETRIC_EMAIL_FIELD_ID}_raw")
                    if not (email_raw and isinstance(email_raw, str) and "@vespa.academy" in email_raw.lower()):
                        logging.debug(f"Psychometric: Record {record_id_for_logging} - No valid ERI scores found across any cycle (less than 3 outcome questions answered in all cycles). Skipping ERI for this record.")

        logging.info(f"Finished processing {total_psychometric_records_processed} psychometric records. Skipped {test_accounts_skipped_psychometric} test accounts.")

    except Exception as e_fetch_psych:
        logging.error(f"Error during Psychometric data fetching/page processing: {e_fetch_psych}")
        pass # Allow averages to be 0 if error

    actual_records_for_aggregation_psychometric = total_psychometric_records_processed - test_accounts_skipped_psychometric
    if actual_records_for_aggregation_psychometric <= 0:
        logging.warning(f"No valid psychometric source records were available for aggregation for {academic_year_str}. Question averages will be zero.")

    for q_output_map in psychometric_output_mapping:
        q_id = q_output_map["questionId"]
        if q_id not in question_aggregates:
             # Initialize if no data at all for this question_id, to ensure all target fields are set
            if total_psychometric_records_processed == 0: # Only if absolutely no records were processed
                question_aggregates[q_id] = {f"cycle{c}": {"sum": 0, "count": 0} for c in range(1,4)}
            else:
                # Some records were processed, but not for this specific q_id. Log and skip.
                logging.debug(f"No data aggregated for psychometric question {q_id}, possibly no scores recorded or q_id mismatch.")
                continue

        for cycle_num in range(1, 4):
            cycle_key_in_json = f"fieldIdCycle{cycle_num}"
            target_field_id = q_output_map.get(cycle_key_in_json)
            if not target_field_id: continue

            agg_data = question_aggregates[q_id][f"cycle{cycle_num}"]
            average = (agg_data["sum"] / agg_data["count"]) if agg_data["count"] > 0 else 0.0
            payload_for_target_object[target_field_id] = average
            if total_psychometric_records_processed > 0:
                logging.info(f"Psychometric Avg for {q_id} Cycle{cycle_num} ({academic_year_str}): {average:.2f} (sum: {agg_data['sum']}, count: {agg_data['count']}) -> {target_field_id}")
            elif not payload_for_target_object.get(target_field_id):
                payload_for_target_object[target_field_id] = 0.0

    # Calculate and add ERI averages to the payload
    logging.info("Calculating ERI averages...")
    for cycle_num in range(1, 4):
        cycle_key = f"cycle{cycle_num}"
        eri_sum = eri_aggregates[cycle_key]["sum"]
        eri_count = eri_aggregates[cycle_key]["count"]
        eri_average = (eri_sum / eri_count) if eri_count > 0 else 0.0
        
        target_field_key = f"eri_cycle{cycle_num}"
        if target_field_key in TARGET_FIELDS_STRUCTURE:
            target_field_id = TARGET_FIELDS_STRUCTURE[target_field_key]
            payload_for_target_object[target_field_id] = eri_average
            logging.info(f"ERI Average for Cycle {cycle_num} ({academic_year_str}): {eri_average:.2f} (sum: {eri_sum:.2f}, count: {eri_count}) -> {target_field_id}")
        else:
            logging.warning(f"Target field ID for {target_field_key} not found in TARGET_FIELDS_STRUCTURE.")

def sync_to_supabase_national_statistics(payload_for_target_object, academic_year_str):
    """
    Sync the calculated national averages to Supabase national_statistics table.
    This ensures the frontend can access historical data even after student re-uploads.
    """
    try:
        logging.info(f"Syncing national averages to Supabase for academic year {academic_year_str}")
        
        # Convert academic year from Knack format (2024-2025) to Supabase format (2024/2025)
        supabase_year = academic_year_str.replace('-', '/')
        
        # Field mappings for each cycle
        cycle_field_mappings = {
            1: {
                'vision': 'field_3292',
                'effort': 'field_3293',
                'systems': 'field_3294',
                'practice': 'field_3295',
                'attitude': 'field_3296',
                'overall': 'field_3297'
            },
            2: {
                'vision': 'field_3298',
                'effort': 'field_3299',
                'systems': 'field_3300',
                'practice': 'field_3301',
                'attitude': 'field_3302',
                'overall': 'field_3303'
            },
            3: {
                'vision': 'field_3304',
                'effort': 'field_3348',
                'systems': 'field_3349',
                'practice': 'field_3350',
                'attitude': 'field_3351',
                'overall': 'field_3352'
            }
        }
        
        # ERI field mappings
        eri_field_mappings = {
            1: 'field_3432',
            2: 'field_3433',
            3: 'field_3434'
        }
        
        records_synced = 0
        
        # Process each cycle
        for cycle, fields in cycle_field_mappings.items():
            # Delete existing records for this year/cycle to avoid duplicates
            logging.info(f"Clearing existing national_statistics for {supabase_year} cycle {cycle}")
            supabase_client.table('national_statistics').delete().eq(
                'academic_year', supabase_year
            ).eq('cycle', cycle).execute()
            
            # Process VESPA components
            for element, field_id in fields.items():
                value = payload_for_target_object.get(field_id)
                if value is not None and value != '':
                    try:
                        # Insert into national_statistics table
                        stat_data = {
                            'academic_year': supabase_year,
                            'cycle': cycle,
                            'element': element,
                            'mean': float(value),
                            'std_dev': 0,  # These will be calculated by the sync process
                            'count': 0,  
                            'percentile_25': 0,
                            'percentile_50': float(value),  # Use mean as median
                            'percentile_75': 0,
                            'distribution': []  
                        }
                        
                        supabase_client.table('national_statistics').insert(stat_data).execute()
                        records_synced += 1
                        logging.debug(f"Synced {element} for cycle {cycle}: {value}")
                    except Exception as e:
                        logging.error(f"Error syncing {element} for cycle {cycle}: {e}")
            
            # Process ERI
            eri_field = eri_field_mappings.get(cycle)
            if eri_field:
                eri_value = payload_for_target_object.get(eri_field)
                if eri_value is not None and eri_value != '':
                    try:
                        eri_data = {
                            'academic_year': supabase_year,
                            'cycle': cycle,
                            'element': 'ERI',
                            'eri_score': float(eri_value),
                            'mean': 0,  # ERI is stored in eri_score field
                            'std_dev': 0,
                            'count': 0,
                            'percentile_25': 0,
                            'percentile_50': 0,
                            'percentile_75': 0,
                            'distribution': []
                        }
                        
                        supabase_client.table('national_statistics').insert(eri_data).execute()
                        records_synced += 1
                        logging.debug(f"Synced ERI for cycle {cycle}: {eri_value}")
                    except Exception as e:
                        logging.error(f"Error syncing ERI for cycle {cycle}: {e}")
        
        logging.info(f"Successfully synced {records_synced} records to Supabase national_statistics table")
        return True
        
    except Exception as e:
        logging.error(f"Error syncing to Supabase national_statistics: {e}")
        # Don't fail the main process if Supabase sync fails
        return False

def main():
    today = date.today()
    
    # Log that we're running the calculation
    logging.info(f"Starting national average calculation for {today.strftime('%Y-%m-%d')}")
    
    # Check for force run environment variable (keeping for backward compatibility)
    FORCE_RUN = os.environ.get("FORCE_RUN_NATIONAL_AVERAGES", "false").lower() == "true"
    if FORCE_RUN:
        logging.info("FORCE_RUN_NATIONAL_AVERAGES is set to true.")

    academic_year_str, filter_start_date, filter_end_date, ay_actual_start, ay_actual_end = get_current_academic_year_info()
    dynamic_target_record_name = f"{BASE_TARGET_RECORD_NAME} {academic_year_str}"
    logging.info(f"Processing national averages for: {dynamic_target_record_name}")
    logging.info(f"Date range: {filter_start_date} to {filter_end_date}")

    if not KNACK_APP_ID or not KNACK_API_KEY: return

    try:
        # Load JSON mappings
        psychometric_details = load_json_mapping(PSYCHOMETRIC_DETAILS_JSON_PATH)
        psychometric_output_mapping = load_json_mapping(PSYCHOMETRIC_OUTPUT_JSON_PATH)

        # Prepare payload for the target object_120 record
        payload_for_target_object = {
            TARGET_FIELDS_STRUCTURE["name_base"]: dynamic_target_record_name,
            TARGET_FIELDS_STRUCTURE["academic_year"]: academic_year_str,
            TARGET_FIELDS_STRUCTURE["date_time"]: today.strftime("%d/%m/%Y")  # Update the date to today (UK format)
        }

        # 1. Process VESPA Scores from object_10 (batched)
        logging.info("--- Starting VESPA Score Processing ---")
        process_vespa_scores(payload_for_target_object, academic_year_str, filter_start_date, filter_end_date)
        logging.info("--- Finished VESPA Score Processing ---")

        # 2. Process Psychometric Question Scores from object_29 (now batched)
        logging.info("--- Starting Psychometric Question Score Processing ---")
        process_psychometric_scores(
            psychometric_details, 
            psychometric_output_mapping, 
            payload_for_target_object, 
            academic_year_str, 
            filter_start_date, 
            filter_end_date
        )
        logging.info("--- Finished Psychometric Question Score Processing ---")

        # 3. Find or Create/Update record in the target object_120
        target_record_id = find_target_record_id(
            TARGET_OBJECT_KEY, 
            TARGET_FIELDS_STRUCTURE["name_base"], 
            dynamic_target_record_name
        )
        if target_record_id:
            update_knack_record(TARGET_OBJECT_KEY, target_record_id, payload_for_target_object)
        else:
            create_knack_record(TARGET_OBJECT_KEY, payload_for_target_object)
        
        # 4. Sync to Supabase national_statistics table
        if supabase_client:
            sync_to_supabase_national_statistics(payload_for_target_object, academic_year_str)
        else:
            logging.warning("Supabase not configured - skipping sync to national_statistics table")
            
        logging.info("National average calculation task completed successfully.")

    except ValueError as ve: logging.error(f"Configuration error: {ve}")
    except requests.exceptions.RequestException as re: logging.error(f"A network-related error occurred: {re}")
    except Exception as e: logging.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main() 