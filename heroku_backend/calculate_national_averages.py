import os
import requests
import logging
import json # Required for json.dumps in find_target_record_id and other API interactions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration from Environment Variables ---
KNACK_APP_ID = os.environ.get("KNACK_APP_ID")
KNACK_API_KEY = os.environ.get("KNACK_API_KEY")
SOURCE_OBJECT_KEY = "object_10"  # VESPA Results
TARGET_OBJECT_KEY = "object_120" # National Averages Data

# --- Field Definitions ---

# Source fields in object_10 (VESPA Results)
SOURCE_FIELDS = {
    "cycle1": {
        "V": "field_155", "E": "field_156", "S": "field_157", "P": "field_158", "A": "field_159"
    },
    "cycle2": {
        "V": "field_161", "E": "field_162", "S": "field_163", "P": "field_164", "A": "field_165"
    },
    "cycle3": {
        "V": "field_167", "E": "field_168", "S": "field_169", "P": "field_170", "A": "field_171"
    }
}

ALL_SOURCE_FIELDS_FLAT = [field_id for cycle_fields in SOURCE_FIELDS.values() for field_id in cycle_fields.values()]

# Target fields in object_120 (National Averages Data)
TARGET_FIELDS = {
    "name": "field_3290",
    "cycle1": {
        "V": "field_3292", "E": "field_3293", "S": "field_3294", "P": "field_3295", "A": "field_3296"
    },
    "cycle2": {
        "V": "field_3297", "E": "field_3298", "S": "field_3299", "P": "field_3300", "A": "field_3301"
    },
    "cycle3": {
        "V": "field_3302", "E": "field_3303", "S": "field_3304", "P": "field_3305", "A": "field_3306"
    }
}
TARGET_RECORD_NAME = "National VESPA Averages by Cycle"

# --- Helper Functions ---

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

def fetch_knack_stats(object_key, fields_to_sum, fields_to_count):
    """Fetches sums and counts for specified fields from a Knack object."""
    logging.info(f"Fetching stats from Knack object: {object_key} for {len(fields_to_sum)} fields")
    api_url = f"https://api.knack.com/v1/objects/{object_key}/records"
    # Knack API has a limit on URL length for GET requests, be mindful if many fields
    params = {
        "rows_per_page": 0, 
        "extra_fields_sum": ",".join(fields_to_sum),
        "extra_fields_count": ",".join(fields_to_count)
    }
    response = None # Initialize response here for broader scope in error logging
    try:
        response = requests.get(api_url, headers=get_knack_headers(), params=params)
        response.raise_for_status()  # Raises an exception for HTTP errors
        logging.info(f"Successfully fetched stats from {object_key}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching stats from Knack object {object_key}: {e}")
        if response is not None:
            logging.error(f"Response status: {response.status_code}, Response content: {response.text}")
        else:
            logging.error("No response received from server.")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response from {object_key}: {e}")
        if response is not None:
            logging.error(f"Response content causing decode error: {response.text}")
        raise

def calculate_average(stats_data, sum_field_key, count_field_key):
    """Calculates average from sum and count, handling potential missing data."""
    # Knack stats often return sums/counts as strings, ensure conversion to float/int
    total_sum = float(stats_data.get(sum_field_key, 0) or 0)
    total_count = int(stats_data.get(count_field_key, 0) or 0)
    
    if total_count > 0:
        return total_sum / total_count
    return 0

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

# --- Main Logic ---
def main():
    logging.info("Starting national average calculation task.")

    if not KNACK_APP_ID or not KNACK_API_KEY:
        logging.error("Critical: Knack App ID or API Key not configured. Exiting.")
        return

    try:
        # 1. Fetch all sums and counts from the source object_10
        # Knack API might have limitations on the number of fields in a single stat request.
        # If ALL_SOURCE_FIELDS_FLAT is too long, this might need to be broken down.
        source_stats = fetch_knack_stats(SOURCE_OBJECT_KEY, ALL_SOURCE_FIELDS_FLAT, ALL_SOURCE_FIELDS_FLAT)
        
        if not source_stats:
            logging.error("Failed to retrieve source stats from Knack. Aborting.")
            return
            
        payload_for_target_object = {TARGET_FIELDS["name"]: TARGET_RECORD_NAME}
        
        # 2. Calculate averages for each component in each cycle and prepare payload
        for cycle_key, components in SOURCE_FIELDS.items(): # "cycle1", "cycle2", "cycle3"
            for component_key, source_field_id in components.items(): # "V", "E", "S", "P", "A"
                # Knack prepends 'sum_' or 'count_' to field names in stats results
                sum_key = f"sum_{source_field_id}"
                count_key = f"count_{source_field_id}"
                
                average = calculate_average(source_stats, sum_key, count_key)
                
                target_field_id = TARGET_FIELDS[cycle_key][component_key]
                payload_for_target_object[target_field_id] = average
                logging.info(f"Calculated average for {cycle_key} {component_key} ({source_field_id}): {average:.2f} -> {target_field_id}")

        # 3. Find or Create/Update record in the target object_120
        target_record_id = find_target_record_id(TARGET_OBJECT_KEY, TARGET_FIELDS["name"], TARGET_RECORD_NAME)

        if target_record_id:
            update_knack_record(TARGET_OBJECT_KEY, target_record_id, payload_for_target_object)
        else:
            create_knack_record(TARGET_OBJECT_KEY, payload_for_target_object)
            
        logging.info("National average calculation task completed successfully.")

    except ValueError as ve: # Catch specific error for missing credentials
        logging.error(f"Configuration error: {ve}")
    except requests.exceptions.RequestException as re:
        logging.error(f"A network-related error occurred: {re}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during the task: {e}", exc_info=True)

if __name__ == "__main__":
    main() 