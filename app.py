import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, current_app
from dotenv import load_dotenv
from flask_cors import CORS # Import CORS
import logging # Import Python's standard logging
from functools import wraps
import hashlib
import redis
import pickle
import pandas as pd
from scipy.stats import pearsonr
import gzip  # Add gzip for compression
from threading import Thread
import time
import random  # Add random for sampling comments

# Add PDF generation imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
import base64

# Download NLTK data at startup
import nltk
import ssl

# Configure logging first
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
logger = logging.getLogger(__name__)

# Handle SSL certificate issues
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download required NLTK data with error handling
import os
nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir)

# Set NLTK data path
nltk.data.path.append('/app/nltk_data')

# Download punkt tokenizer if not already present
try:
    nltk.data.find('tokenizers/punkt')
    logger.info("NLTK punkt tokenizer already downloaded")
except LookupError:
    logger.info("Downloading NLTK punkt tokenizer...")
    try:
        nltk.download('punkt', download_dir='/app/nltk_data')
    except Exception as e:
        logger.warning(f"Failed to download punkt: {e}")
        # Try to use existing data if download fails
        pass

# Download stopwords if not already present
try:
    nltk.data.find('corpora/stopwords')
    logger.info("NLTK stopwords already downloaded")
except LookupError:
    logger.info("Downloading NLTK stopwords...")
    try:
        nltk.download('stopwords', download_dir='/app/nltk_data')
    except Exception as e:
        logger.warning(f"Failed to download stopwords: {e}")
        pass

# Download brown corpus if not already present
try:
    nltk.data.find('corpora/brown')
    logger.info("NLTK brown corpus already downloaded")
except LookupError:
    logger.info("Downloading NLTK brown corpus...")
    try:
        nltk.download('brown', download_dir='/app/nltk_data')
    except Exception as e:
        logger.warning(f"Failed to download brown: {e}")
        pass

load_dotenv() # Load environment variables from .env for local development

app = Flask(__name__)

# --- Redis Cache Setup ---
# Check for different Redis URL environment variable names
REDIS_URL = os.getenv('REDIS_URL') or os.getenv('HEROKU_REDIS_COBALT_URL') or os.getenv('HEROKU_REDIS_CRIMSON_URL')
if not REDIS_URL:
    app.logger.warning("Redis URL not found in environment variables (checked REDIS_URL, HEROKU_REDIS_COBALT_URL)")
    REDIS_URL = 'redis://localhost:6379'

try:
    # Handle SSL connections for Heroku Redis
    if REDIS_URL.startswith('rediss://'):
        # For SSL connections, we need to configure SSL settings
        import ssl as ssl_lib
        redis_client = redis.from_url(
            REDIS_URL, 
            decode_responses=False,
            ssl_cert_reqs=None,
            ssl_ca_certs=None,
            ssl_check_hostname=False
        )
    else:
        # For non-SSL connections
        redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    
    # Test the connection
    redis_client.ping()
    CACHE_ENABLED = True
    app.logger.info(f"Redis cache connected successfully to {REDIS_URL.split('@')[1] if '@' in REDIS_URL else REDIS_URL}")
except Exception as e:
    redis_client = None
    CACHE_ENABLED = False
    app.logger.warning(f"Redis cache not available - caching disabled. Error: {str(e)}")

# Cache TTL settings (in seconds)
CACHE_TTL = {
    'vespa_results': 300,  # 5 minutes for VESPA results
    'national_data': 3600,  # 1 hour for national benchmarks
    'filter_options': 600,  # 10 minutes for filter options
    'establishments': 3600,  # 1 hour for establishments
    'question_mappings': 86400,  # 24 hours for static mappings
    'dashboard_data': 600,  # 10 minutes for dashboard batch data
}

# --- Explicit CORS Configuration ---
# Allow requests from your specific Knack domain and potentially localhost for development
# Updated CORS configuration with explicit settings
CORS(app, 
     resources={r"/api/*": {"origins": ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]}},
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Add explicit CORS headers to all responses (belt and suspenders approach)
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    app.logger.info(f"Request Origin: {origin}")
    
    # List of allowed origins
    allowed_origins = ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]  # Added "null" for file:// testing
    
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '3600'
    
    # Log the response headers for debugging
    app.logger.info(f"Response headers: {dict(response.headers)}")
    
    return response

# --- Explicitly configure logging ---
# Remove any default handlers Flask might have added that Gunicorn might ignore
if app.logger.hasHandlers():
    app.logger.handlers.clear()

# Configure the root logger or Flask's logger to be more verbose
# and ensure it outputs to stdout/stderr which Heroku/Gunicorn capture.
gunicorn_logger = logging.getLogger('gunicorn.error') # Gunicorn's error logger often captures app output
app.logger.handlers.extend(gunicorn_logger.handlers)
app.logger.setLevel(logging.INFO)

# If the above doesn't work, try a more direct basicConfig:
# logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
# app.logger = logging.getLogger(__name__) # then use app.logger as before

app.logger.info("Flask logger has been configured explicitly.") # Test message

# --- Configuration ---
KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') # We'll use this later

# Log configuration status (without revealing actual keys)
app.logger.info(f"KNACK_APP_ID configured: {'Yes' if KNACK_APP_ID else 'No'}")
app.logger.info(f"KNACK_API_KEY configured: {'Yes' if KNACK_API_KEY else 'No'}")
app.logger.info(f"OPENAI_API_KEY configured: {'Yes' if OPENAI_API_KEY else 'No'}")

# --- Error Handling ---
class ApiError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code

@app.errorhandler(ApiError)
def handle_api_error(error):
    response = jsonify({'message': error.args[0]})
    response.status_code = error.status_code
    # Ensure CORS headers are added to error responses
    origin = request.headers.get('Origin')
    if origin in ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.errorhandler(Exception)
def handle_generic_error(error):
    app.logger.error(f"An unexpected error occurred: {error}")
    response = jsonify({'message': "An internal server error occurred."})
    response.status_code = 500
    # Ensure CORS headers are added to error responses
    origin = request.headers.get('Origin')
    if origin in ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.errorhandler(503)
def handle_service_unavailable(error):
    app.logger.error(f"Service unavailable (503): {error}")
    response = jsonify({'message': "Request timeout - please try again with a smaller dataset or contact support."})
    response.status_code = 503
    # Ensure CORS headers are added to 503 responses
    origin = request.headers.get('Origin')
    if origin in ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.errorhandler(504)
def handle_gateway_timeout(error):
    app.logger.error(f"Gateway timeout (504): {error}")
    response = jsonify({'message': "Request processing took too long. Please try loading a smaller dataset or contact support."})
    response.status_code = 504
    # Ensure CORS headers are added
    origin = request.headers.get('Origin')
    if origin in ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# --- Knack API Proxy ---
BASE_KNACK_URL = f"https://api.knack.com/v1/objects"

# --- Academic Year Helper ---
def get_academic_year_filters(establishment_id=None, date_field='field_855', australian_field='field_3511'):
    """
    Generate academic year date filters for UK/Australian schools.
    
    Args:
        establishment_id: The establishment record ID to check if Australian
        date_field: The date field to filter on (default: field_855 for Object_10)
        australian_field: The boolean field indicating Australian school (default: field_3511 for Object_10)
    
    Returns:
        list: Filter rules for the academic year
    """
    from datetime import datetime, timedelta
    
    is_australian_school = False
    
    # Check if this is an Australian school
    if establishment_id:
        try:
            # Fetch establishment record to check if Australian
            est_data = make_knack_request('object_2', record_id=establishment_id, fields=[australian_field, f'{australian_field}_raw'])
            is_australian = est_data.get(f'{australian_field}_raw', False)
            if is_australian == 'true' or is_australian == True or is_australian == 'True':
                is_australian_school = True
                app.logger.info(f"Establishment {establishment_id} is an Australian school")
        except Exception as e:
            app.logger.warning(f"Could not check if establishment is Australian: {e}")
    
    # Calculate academic year date boundaries
    today = datetime.now()
    
    if is_australian_school:
        # Australian schools: Calendar year (Jan 1 - Dec 31)
        academic_year_start = datetime(today.year, 1, 1)
        academic_year_end = datetime(today.year, 12, 31)
        app.logger.info(f"Using Australian academic year: {today.year}")
    else:
        # UK schools: Academic year (Aug 1 - Jul 31)
        if today.month >= 8:  # August or later
            academic_year_start = datetime(today.year, 8, 1)
            academic_year_end = datetime(today.year + 1, 7, 31)
            app.logger.info(f"Using UK academic year: {today.year}-{str(today.year + 1)[2:]}")
        else:  # January to July
            academic_year_start = datetime(today.year - 1, 8, 1)
            academic_year_end = datetime(today.year, 7, 31)
            app.logger.info(f"Using UK academic year: {today.year - 1}-{str(today.year)[2:]}")
    
    # Format dates as dd/mm/yyyy for Knack (inclusive boundaries)
    # Subtract 1 day from start to make it inclusive, add 1 day to end
    start_date_inclusive = academic_year_start - timedelta(days=1)
    end_date_inclusive = academic_year_end + timedelta(days=1)
    
    start_date_str = start_date_inclusive.strftime('%d/%m/%Y')
    end_date_str = end_date_inclusive.strftime('%d/%m/%Y')
    
    # Log the filter being applied
    app.logger.info(f"Academic year filter: {start_date_str} to {end_date_str} on field {date_field}")
    
    # Return date range filter
    return {
        'match': 'and',
        'rules': [
            {
                'field': date_field,
                'operator': 'is after',
                'value': start_date_str
            },
            {
                'field': date_field,
                'operator': 'is before',
                'value': end_date_str
            }
        ]
    }

# --- Caching Decorator ---
def cache_key(*args, **kwargs):
    """Generate a cache key from function arguments"""
    key_parts = []
    for arg in args:
        if isinstance(arg, (list, dict)):
            key_parts.append(json.dumps(arg, sort_keys=True))
        else:
            key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (list, dict)):
            key_parts.append(f"{k}:{json.dumps(v, sort_keys=True)}")
        else:
            key_parts.append(f"{k}:{v}")
    
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached(ttl_key='default', ttl_seconds=300):
    """Decorator to cache function results in Redis with compression"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key_str = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            try:
                cached_value = redis_client.get(cache_key_str)
                if cached_value:
                    app.logger.info(f"Cache hit for {cache_key_str}")
                    # Decompress and unpickle
                    return pickle.loads(gzip.decompress(cached_value))
            except Exception as e:
                app.logger.error(f"Cache get error: {e}")
            
            # Call function and cache result
            result = func(*args, **kwargs)
            
            try:
                ttl = CACHE_TTL.get(ttl_key, ttl_seconds)
                # Compress before caching
                compressed_data = gzip.compress(pickle.dumps(result))
                redis_client.setex(cache_key_str, ttl, compressed_data)
                app.logger.info(f"Cached {cache_key_str} for {ttl} seconds (compressed)")
            except Exception as e:
                app.logger.error(f"Cache set error: {e}")
            
            return result
        
        return wrapper
    return decorator

# --- Optimized Knack API Functions ---
@cached(ttl_key='vespa_results')
def make_knack_request(object_key, filters=None, method='GET', data=None, record_id=None, page=1, rows_per_page=1000, sort_field=None, sort_order=None, fields=None):
    # Check if credentials are configured
    if not KNACK_APP_ID or not KNACK_API_KEY:
        raise ApiError("Knack API credentials not configured. Please set KNACK_APP_ID and KNACK_API_KEY environment variables.", 500)
    
    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json'
    }
    url = f"{BASE_KNACK_URL}/{object_key}/records"
    if record_id:
        url = f"{BASE_KNACK_URL}/{object_key}/records/{record_id}"

    params = {'page': page, 'rows_per_page': rows_per_page}
    if filters:
        params['filters'] = json.dumps(filters)
    if sort_field:
        params['sort_field'] = sort_field
    if sort_order:
        params['sort_order'] = sort_order

    # Add field filtering to reduce payload size
    if fields:
        params['fields'] = json.dumps(fields)

    app.logger.info(f"Making Knack API request to URL: {url} with params: {params}")

    try:
        # Add timeout to prevent hanging requests
        timeout = 20  # 20 seconds timeout for individual Knack requests
        
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data, params=params, timeout=timeout)
        else:
            raise ApiError("Unsupported HTTP method for Knack API", 405)
        
        app.logger.info(f"Knack API response status: {response.status_code}") # Log status code
        app.logger.info(f"Knack API response headers: {response.headers}") # Log response headers
        # Log first 500 chars of text response to see what Knack is sending
        app.logger.info(f"Knack API response text (first 500 chars): {response.text[:500]}") 

        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        
        knack_data = response.json() # Try to parse JSON
        app.logger.info(f"Successfully parsed Knack API JSON response.")
        return knack_data

    except requests.exceptions.Timeout:
        app.logger.error(f"Knack API timeout after {timeout} seconds")
        raise ApiError(f"Knack API request timed out after {timeout} seconds", 504)
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Knack API HTTPError: {e.response.status_code} - {e.response.text}")
        raise ApiError(f"Knack API request failed: {e.response.status_code} - {e.response.text}", e.response.status_code)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Knack API RequestException: {e}")
        raise ApiError(f"Knack API request failed: {e}", 500)

@app.route('/api/knack-data', methods=['GET'])
def get_knack_data():
    object_key = request.args.get('objectKey')
    filters_str = request.args.get('filters')
    page = request.args.get('page', 1, type=int)
    rows_per_page = request.args.get('rows_per_page', 1000, type=int)
    sort_field = request.args.get('sort_field')
    sort_order = request.args.get('sort_order')
    fields_str = request.args.get('fields')  # New parameter for field selection

    if not object_key:
        raise ApiError("Missing 'objectKey' parameter")

    filters = []
    if filters_str:
        try:
            filters = json.loads(filters_str)
        except json.JSONDecodeError:
            raise ApiError("Invalid 'filters' JSON format")
    
    fields = []
    if fields_str:
        try:
            fields = json.loads(fields_str)
        except json.JSONDecodeError:
            raise ApiError("Invalid 'fields' JSON format")

    all_records = []
    current_page = page
    
    # Initial fetch
    data = make_knack_request(object_key, filters=filters, page=current_page, rows_per_page=rows_per_page, 
                            sort_field=sort_field, sort_order=sort_order, fields=fields)
    records = data.get('records', [])
    all_records.extend(records)
        
    # Pagination logic: Continue fetching if more pages exist AND we didn't specifically ask for a small number of rows (e.g. 1 with sorting)
    # This avoids unnecessary pagination if the client intended to get only the first page (e.g., rows_per_page=1, sort_field provided).
    if not (rows_per_page == 1 and sort_field):
        while True:
            current_page += 1 # Increment page for the next fetch
            total_pages = data.get('total_pages') 
            
            if total_pages is None or current_page > total_pages or not records: # Check if we should stop
                break
            
            # Allow caller to override the default 5-page safety cap by passing ?max_pages=<N> (0 = unlimited)
            max_pages_param = request.args.get('max_pages', type=int)
            if max_pages_param is None:
                page_cap = 0 if filters else 5  # unlimited pages when client supplied filters (targeted fetch)
            else:
                page_cap = max_pages_param

            if page_cap != 0 and current_page > page_cap:
                app.logger.warning(
                    f"Stopped fetching for {object_key} after {current_page - 1} pages (page cap = {page_cap}).")
                break

            data = make_knack_request(object_key, filters=filters, page=current_page, rows_per_page=rows_per_page, 
                                    sort_field=sort_field, sort_order=sort_order, fields=fields)
            records = data.get('records', []) # Get records from the new fetch
            if not records: # No more records returned, stop.
                break
            all_records.extend(records)
            
    return jsonify({'records': all_records})


# --- New Batch Data Endpoint ---
@app.route('/api/dashboard-initial-data', methods=['POST'])
def get_dashboard_initial_data():
    """
    Batch endpoint to fetch all initial dashboard data in one request.
    This reduces multiple round trips and allows better caching.
    """
    import time
    start_time = time.time()
    MAX_REQUEST_TIME = 25  # Exit before Heroku's 30s timeout
    
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    staff_admin_id = data.get('staffAdminId')
    establishment_id = data.get('establishmentId')
    cycle = data.get('cycle', 1)
    page = data.get('page', 1)  # Support pagination
    rows_per_page = data.get('rowsPerPage', 1000)  # Reduced default from 3000
    
    if not staff_admin_id and not establishment_id:
        raise ApiError("Either staffAdminId or establishmentId must be provided")
    
    # Generate cache key for this specific request
    cache_key = f"dashboard_data:{staff_admin_id or 'none'}:{establishment_id or 'none'}:{cycle}:{page}:{rows_per_page}"
    
    # Try to get from cache first
    if CACHE_ENABLED:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                app.logger.info(f"Returning cached dashboard data for key: {cache_key}")
                # Decompress and unpickle
                return jsonify(pickle.loads(gzip.decompress(cached_data)))
        except Exception as e:
            app.logger.error(f"Cache retrieval error: {e}")
    
    app.logger.info(f"Fetching dashboard initial data for staffAdminId: {staff_admin_id}, establishmentId: {establishment_id}, cycle: {cycle}, page: {page}")
    
    results = {}
    
    # Build base filters
    base_filters = []
    if establishment_id:
        base_filters.append({
            'field': 'field_133',
            'operator': 'is',
            'value': establishment_id
        })
        # Add academic year filter for Object_10
        academic_year_filter = get_academic_year_filters(establishment_id, 'field_855', 'field_3511')
        base_filters.append(academic_year_filter)
        
        # Add filter for cycle completion - check if at least one score field is not blank
        # For cycle 1: field_155, cycle 2: field_161, cycle 3: field_167
        cycle_completion_field = f'field_{155 + (cycle - 1) * 6}'
        base_filters.append({
            'field': cycle_completion_field,
            'operator': 'is not blank'
        })
        app.logger.info(f"Added cycle {cycle} completion filter on field {cycle_completion_field}")
    elif staff_admin_id:
        base_filters.append({
            'field': 'field_439',
            'operator': 'is',
            'value': staff_admin_id
        })
        # For staff admin, we default to UK academic year (can't determine if Australian without specific establishment)
        academic_year_filter = get_academic_year_filters(None, 'field_855', 'field_3511')
        base_filters.append(academic_year_filter)
        
        # Add filter for cycle completion
        cycle_completion_field = f'field_{155 + (cycle - 1) * 6}'
        base_filters.append({
            'field': cycle_completion_field,
            'operator': 'is not blank'
        })
        app.logger.info(f"Added cycle {cycle} completion filter on field {cycle_completion_field}")
    
    # Define minimal field set for VESPA results (object_10)
    cycle_offset = (cycle - 1) * 6
    score_fields = [f'field_{154 + cycle_offset + i}_raw' for i in range(6)]
    
    app.logger.info(f"DEBUG: Looking for cycle {cycle} score fields: {score_fields}")
    
    vespa_fields = [
        'id',
        'field_133',
        'field_133_raw',
        'field_439_raw',
        'field_187_raw',
        'field_223',
        'field_223_raw',
        'field_2299',
        'field_2299_raw',
        'field_144_raw',
        'field_782_raw',
        'field_146',        # Current cycle
        'field_146_raw',    # Current cycle raw value
        *score_fields,
        'field_2302_raw',
        'field_2303_raw',
        'field_2304_raw',
        'field_2499_raw',
        'field_2493_raw',
        'field_2494_raw',
        'field_855',        # Completion date for academic year filtering
        'field_855_raw',
        'field_3511_raw',   # Australian school indicator
    ]
    
    try:
        # Check cache first with exact key
        if CACHE_ENABLED:
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    app.logger.info(f"Returning cached dashboard data for key: {cache_key}")
                    # Decompress and unpickle
                    return jsonify(pickle.loads(gzip.decompress(cached_data)))
            except Exception as e:
                app.logger.error(f"Cache retrieval error: {e}")
        
        # For large establishments, implement a different strategy
        # First, check the size of the dataset
        size_check = make_knack_request(
            'object_10',
            filters=base_filters,
            page=1,
            rows_per_page=1,
            fields=['id']
        )
        
        total_records = size_check.get('total_records', 0)
        total_pages = size_check.get('total_pages', 1)
        
        app.logger.info(f"Total records for establishment: {total_records}, Total pages: {total_pages}")
        app.logger.info(f"DEBUG: Using filters: {base_filters}")
        
        # Check if we have time left
        elapsed_time = time.time() - start_time
        if elapsed_time > MAX_REQUEST_TIME:
            app.logger.warning(f"Request time limit approaching ({elapsed_time}s), returning cached data if available")
            return jsonify({
                'vespaResults': [],
                'nationalBenchmark': {},
                'filterOptions': {'groups': [], 'courses': [], 'yearGroups': [], 'faculties': []},
                'error': 'Request timeout - dataset too large',
                'totalRecords': total_records
            })
        
        # If it's a large dataset, fetch in smarter batches
        if total_records > 1500:
            app.logger.info(f"Large dataset detected ({total_records} records). Fetching initial subset.")
            
            vespa_records = []
            import concurrent.futures
            
            # For initial load, only fetch first 5 pages (5,000 records max)
            # This prevents the 12MB response issue and improves performance
            pages_to_fetch = min(total_pages, 5)  # Increased from 3 to 5 pages for better performance
            app.logger.info(f"Will fetch {pages_to_fetch} pages initially (total available: {total_pages})")
            
            # For very large datasets, try fetching pages sequentially with smaller page size
            if total_records > 2000:
                app.logger.info(f"Very large dataset ({total_records} records). Using sequential fetch with smaller pages.")
                
                # Try smaller page size for large datasets
                smaller_page_size = 500
                # Calculate pages needed based on actual total records, with some buffer
                pages_needed = min(15, ((total_records + smaller_page_size - 1) // smaller_page_size) + 2)  # Add 2 extra pages for buffer
                
                for page_num in range(1, pages_needed + 1):
                    # Check time before each request
                    if time.time() - start_time > MAX_REQUEST_TIME - 5:
                        app.logger.warning(f"Stopping at page {page_num} due to time limit")
                        break
                    
                    try:
                        page_data = make_knack_request(
                            'object_10',
                            filters=base_filters,
                            page=page_num,
                            rows_per_page=smaller_page_size,
                            fields=vespa_fields
                        )
                        page_records = page_data.get('records', [])
                        
                        if page_records:
                            vespa_records.extend(page_records)
                            app.logger.info(f"Fetched page {page_num} - {len(page_records)} records (total so far: {len(vespa_records)})")
                        else:
                            app.logger.warning(f"Page {page_num} returned 0 records, continuing to check next pages...")
                            
                    except Exception as e:
                        app.logger.error(f"Error fetching page {page_num}: {e}")
                        # Try to continue with other pages
                        continue
            else:
                # For smaller datasets, use parallel fetching
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:  # Reduced from 5 to 3
                    futures = []
                    consecutive_empty_pages = 0
                    
                    for page_num in range(1, pages_to_fetch + 1):
                        # Check time before submitting
                        if time.time() - start_time > MAX_REQUEST_TIME - 5:
                            app.logger.warning(f"Stopping page submission at page {page_num} due to time limit")
                            break
                            
                        future = executor.submit(
                            make_knack_request,
                            'object_10',
                            filters=base_filters,
                            page=page_num,
                            rows_per_page=1000,
                            fields=vespa_fields
                        )
                        futures.append((page_num, future))
                
                    # Collect results with progress logging
                    for page_num, future in futures:
                        try:
                            # Check time before processing each page
                            elapsed_time = time.time() - start_time
                            if elapsed_time > MAX_REQUEST_TIME - 3:  # Leave 3s buffer
                                app.logger.warning(f"Approaching timeout after {elapsed_time}s, stopping at page {page_num}")
                                # Cancel remaining futures
                                for _, remaining_future in futures[futures.index((page_num, future)):]:
                                    remaining_future.cancel()
                                break
                            
                            page_data = future.result(timeout=min(5, MAX_REQUEST_TIME - elapsed_time))  # Dynamic timeout
                            page_records = page_data.get('records', [])
                            
                            if page_records:
                                vespa_records.extend(page_records)
                                consecutive_empty_pages = 0  # Reset counter
                            else:
                                consecutive_empty_pages += 1
                                app.logger.warning(f"Page {page_num} returned 0 records")
                                # Only stop if we're sure there's no more data
                                if consecutive_empty_pages >= 3 and page_num >= pages_to_fetch - 2:
                                    app.logger.warning(f"Stopping fetch after {consecutive_empty_pages} consecutive empty pages near end")
                                    break
                            
                            app.logger.info(f"Fetched page {page_num}/{pages_to_fetch} - {len(page_records)} records")
                        except Exception as e:
                            app.logger.error(f"Error fetching page {page_num}: {e}")
                            # Don't fail the entire request for one page error
                            continue
            
            app.logger.info(f"Fetched total of {len(vespa_records)} records")
            
            # Add metadata about the dataset
            results['isLimitedMode'] = len(vespa_records) < total_records
            results['totalRecords'] = total_records
            results['loadedRecords'] = len(vespa_records)
            
            # Check if we had to stop early
            if elapsed_time > MAX_REQUEST_TIME - 3:
                results['partialLoad'] = True
                results['message'] = f'Loaded {len(vespa_records)} of {total_records} records due to time constraints'
                app.logger.warning(f"Partial load: {results['message']}")
        
        else:
            # For smaller datasets, still be careful about response size
            import concurrent.futures
            
            # Limit pages for initial load to prevent large responses
            initial_pages = min(total_pages, 5)  # Max 5 pages (5000 records) for initial load
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                
                # Fetch limited pages initially
                app.logger.info(f"Fetching {initial_pages} of {total_pages} pages initially for {total_records} records")
                
                for page_num in range(1, initial_pages + 1):
                    future = executor.submit(
                        make_knack_request,
                        'object_10',
                        filters=base_filters,
                        page=page_num,
                        rows_per_page=1000,
                        fields=vespa_fields
                    )
                    futures.append(future)
                
                # Also fetch national benchmark in parallel
                national_future = executor.submit(
                    make_knack_request,
                    'object_120',
                    filters=[],
                    rows_per_page=1,
                    sort_field='field_3307',
                    sort_order='desc'
                )
                
                # Collect VESPA results
                vespa_records = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        page_data = future.result(timeout=10)  # 10 second timeout per request
                        vespa_records.extend(page_data.get('records', []))
                    except Exception as e:
                        app.logger.error(f"Error fetching page: {e}")
                
                # Get national benchmark result
                try:
                    national_data = national_future.result(timeout=5)
                    results['nationalBenchmark'] = national_data.get('records', [{}])[0]
                except Exception as e:
                    app.logger.error(f"Error fetching national benchmark: {e}")
                    results['nationalBenchmark'] = {}
            
        
        # For large datasets, fetch national benchmark separately
        if total_records > 1500 and 'nationalBenchmark' not in results:
            try:
                national_data = make_knack_request(
                    'object_120',
                    filters=[],
                    rows_per_page=1,
                    sort_field='field_3307',
                    sort_order='desc'
                )
                results['nationalBenchmark'] = national_data.get('records', [{}])[0]
            except Exception as e:
                app.logger.error(f"Error fetching national benchmark: {e}")
                results['nationalBenchmark'] = {}
        
        results['vespaResults'] = vespa_records
        results['hasMore'] = len(vespa_records) < total_records
        results['totalAvailable'] = total_records
        app.logger.info(f"Fetched {len(vespa_records)} of {total_records} VESPA results")
        
        # Debug: Log first few records to check data structure
        if vespa_records:
            app.logger.info(f"DEBUG: First VESPA record structure: {json.dumps(vespa_records[0], indent=2)[:500]}...")
        else:
            app.logger.warning("DEBUG: No VESPA records found!")
        
        # Build filter options locally (quick)
        filter_sets = {
            'groups': set(),
            'courses': set(),
            'yearGroups': set(),
            'faculties': set()
        }

        # Standard year groups that should always be visible
        STANDARD_YEAR_GROUPS = ['Yr7', 'Yr8', 'Yr9', 'Yr10', 'Yr11', 'Yr12', 'Yr13']
        filter_sets['yearGroups'].update(STANDARD_YEAR_GROUPS)

        for rec in vespa_records:
            grp = rec.get('field_223_raw') or rec.get('field_223')
            if grp:
                if isinstance(grp, list):
                    filter_sets['groups'].update([str(g) for g in grp if g])
                else:
                    filter_sets['groups'].add(str(grp))

            course = rec.get('field_2299_raw') or rec.get('field_2299')
            if course:
                if isinstance(course, list):
                    filter_sets['courses'].update([str(c) for c in course if c])
                else:
                    filter_sets['courses'].add(str(course))

            yg = rec.get('field_144_raw')
            if yg:
                filter_sets['yearGroups'].add(str(yg))

            fac = rec.get('field_782_raw')
            if fac:
                filter_sets['faculties'].add(str(fac))

        results['filterOptions'] = {k: sorted(list(v)) for k, v in filter_sets.items()}
        
        # Calculate counts for each filter option
        filter_counts = {
            'groups': {},
            'courses': {},
            'yearGroups': {},
            'faculties': {}
        }
        
        for rec in vespa_records:
            # Count year groups
            yg = rec.get('field_144_raw')
            if yg:
                yg_str = str(yg)
                filter_counts['yearGroups'][yg_str] = filter_counts['yearGroups'].get(yg_str, 0) + 1
                
            # Count other fields similarly...
            
        results['filterCounts'] = filter_counts

        # Always calculate ERI and psychometric data - no compromises on data accuracy
        # Calculate school ERI
        eri_field_map = {
            1: 'field_2868',
            2: 'field_2869',
            3: 'field_2870'
        }
        # This would need the psychometric data - for now just placeholder
        results['schoolERI'] = None
        results['nationalERI'] = None
        results['psychometricResponses'] = []

        # Cache the results with consistent TTL
        if CACHE_ENABLED:
            try:
                # Cache for 10 minutes for all datasets
                cache_ttl = CACHE_TTL.get('dashboard_data', 600)
                compressed_data = gzip.compress(pickle.dumps(results))
                redis_client.setex(cache_key, cache_ttl, compressed_data)
                app.logger.info(f"Cached dashboard data for key: {cache_key} (compressed, TTL: {cache_ttl}s, {len(vespa_records)} records)")
            except Exception as e:
                app.logger.error(f"Cache storage error: {e}")

        app.logger.info(
            f"Dashboard data prepared: {len(vespa_records)} VESPA rows, Filter opts G{len(results['filterOptions']['groups'])}/C{len(results['filterOptions']['courses'])}"
        )

        return jsonify(results)

    except Exception as e:
        app.logger.error(f"Error fetching dashboard initial data: {e}")
        # Always return CORS headers even on error
        response = jsonify({
            'error': str(e),
            'message': 'Failed to fetch dashboard initial data',
            'vespaResults': [],
            'nationalBenchmark': {},
            'filterOptions': {'groups': [], 'courses': [], 'yearGroups': [], 'faculties': []}
        })
        response.status_code = 500
        # Add CORS headers
        origin = request.headers.get('Origin')
        if origin in ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response


# --- New Progressive Loading Endpoint ---
@app.route('/api/dashboard-data-page', methods=['POST'])
def get_dashboard_data_page():
    """
    Fetch a single page of dashboard data for progressive loading.
    Used for large establishments to avoid timeouts.
    """
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    establishment_id = data.get('establishmentId')
    cycle = data.get('cycle', 1)
    page = data.get('page', 1)
    rows_per_page = data.get('rowsPerPage', 1000)
    
    if not establishment_id:
        raise ApiError("establishmentId must be provided")
    
    app.logger.info(f"Fetching page {page} for establishment {establishment_id}, cycle {cycle}")
    
    try:
        # Build filters
        base_filters = [{
            'field': 'field_133',
            'operator': 'is',
            'value': establishment_id
        }]
        
        # Add academic year filter for Object_10
        academic_year_filter = get_academic_year_filters(establishment_id, 'field_855', 'field_3511')
        base_filters.append(academic_year_filter)
        
        # Add filter for cycle completion
        cycle_completion_field = f'field_{155 + (cycle - 1) * 6}'
        base_filters.append({
            'field': cycle_completion_field,
            'operator': 'is not blank'
        })
        app.logger.info(f"Added cycle {cycle} completion filter on field {cycle_completion_field}")
        
        # Define minimal field set
        cycle_offset = (cycle - 1) * 6
        score_fields = [f'field_{154 + cycle_offset + i}_raw' for i in range(6)]
        
        vespa_fields = [
            'id',
            'field_133',
            'field_133_raw',
            'field_439_raw',
            'field_187_raw',
            'field_223',
            'field_223_raw',
            'field_2299',
            'field_2299_raw',
            'field_144_raw',
            'field_782_raw',
            'field_146',        # Current cycle
            'field_146_raw',    # Current cycle raw value
            *score_fields,
            'field_2302_raw',
            'field_2303_raw',
            'field_2304_raw',
            'field_2499_raw',
            'field_2493_raw',
            'field_2494_raw',
            'field_855',        # Completion date
            'field_855_raw',
            'field_3511_raw',   # Australian school indicator
        ]
        
        # Fetch single page
        page_data = make_knack_request(
            'object_10',
            filters=base_filters,
            page=page,
            rows_per_page=rows_per_page,
            fields=vespa_fields
        )
        
        return jsonify({
            'records': page_data.get('records', []),
            'total_pages': page_data.get('total_pages', 0),
            'total_records': page_data.get('total_records', 0),
            'current_page': page
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching dashboard page: {e}")
        raise ApiError(f"Failed to fetch dashboard page: {str(e)}", 500)

# --- Cache Management Endpoints ---
@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all or specific cache entries"""
    if not CACHE_ENABLED:
        return jsonify({'message': 'Cache not enabled'}), 200
    
    data = request.get_json() or {}
    pattern = data.get('pattern', '*')
    establishment_id = data.get('establishmentId')
    clear_type = data.get('clearType')  # New parameter for specific cache types
    
    try:
        if pattern == '*':
            redis_client.flushdb()
            message = 'All cache cleared'
        elif clear_type == 'data_health':
            # Clear all data health cache entries
            keys = redis_client.keys('check_data_health:*')
            if keys:
                redis_client.delete(*keys)
                message = f'Cleared {len(keys)} data health cache entries'
            else:
                message = 'No data health cache entries found'
        elif establishment_id:
            # Clear all cache entries for a specific establishment
            patterns = [
                f'*:{establishment_id}:*',
                f'*establishment*{establishment_id}*',
                f'dashboard_data:*:{establishment_id}:*',
                f'dataset:{establishment_id}:*',
                f'metadata:{establishment_id}:*',
                f'check_data_health:*'  # Also clear data health cache
            ]
            total_cleared = 0
            for p in patterns:
                keys = redis_client.keys(p)
                if keys:
                    redis_client.delete(*keys)
                    total_cleared += len(keys)
            message = f'Cleared {total_cleared} cache entries for establishment {establishment_id}'
        else:
            keys = redis_client.keys(f'*{pattern}*')
            if keys:
                redis_client.delete(*keys)
                message = f'Cleared {len(keys)} cache entries matching pattern: {pattern}'
            else:
                message = f'No cache entries found matching pattern: {pattern}'
        
        app.logger.info(message)
        return jsonify({'message': message})
    except Exception as e:
        app.logger.error(f"Error clearing cache: {e}")
        raise ApiError(f"Failed to clear cache: {str(e)}", 500)

# --- New Endpoint for Establishments ---

@app.route('/api/establishments/search', methods=['GET'])
def search_establishments():
    """Quick search endpoint for establishments using Knack's search"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({'establishments': []})
        
        # Try to search in the establishment object directly if available
        # This assumes you have an establishments object in Knack
        # If not, we'll fall back to searching in VESPA results
        
        # First, try object_3 (Establishments) if it exists
        try:
            filters = [{
                'field': 'field_8',  # Establishment name field in object_3
                'operator': 'contains',
                'value': query
            }]
            
            establishments = make_knack_request(
                'object_3',  # Establishments object
                filters=filters,
                rows_per_page=20,
                page=1
            )
            
            if establishments:
                results = []
                for est in establishments:
                    results.append({
                        'id': est['id'],
                        'name': est.get('field_8', 'Unknown')
                    })
                return jsonify({'establishments': results})
                
        except Exception as e:
            app.logger.warning(f"Could not search object_3: {str(e)}")
        
        # Fallback to searching in VESPA results
        return get_establishments()
        
    except Exception as e:
        app.logger.error(f"Error searching establishments: {str(e)}")
        return jsonify({'establishments': [], 'error': str(e)}), 500

# --- Serving Static JSON Files ---
def load_json_file(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise ApiError(f"File not found: {file_path}", 404)
    except json.JSONDecodeError:
        raise ApiError(f"Error decoding JSON from file: {file_path}", 500)

@app.route('/api/interrogation-questions', methods=['GET'])
def get_interrogation_questions():
    questions = load_json_file('knowledge_base/data_analysis_questions.json')
    return jsonify(questions)

@app.route('/api/question-mappings', methods=['GET'])
def get_question_mappings():
    # Combine or serve them separately as needed by your frontend
    id_to_text = load_json_file('AIVESPACoach/question_id_to_text_mapping.json')
    psychometric_details = load_json_file('AIVESPACoach/psychometric_question_details.json')
    return jsonify({
        'id_to_text': id_to_text,
        'psychometric_details': psychometric_details
    })

# === QLA DATAFRAME UTILS (new) ===
def _get_psychometric_mapping(cycle=None):
    mapping_path = 'AIVESPACoach/psychometric_question_details.json'
    mapping_json = load_json_file(mapping_path)
    id_map = {}
    
    # Create a comprehensive mapping that handles all variations
    for item in mapping_json:
        qid = item['questionId']
        
        # Determine which field to use based on cycle
        if cycle:
            # Use cycle-specific historical fields
            cycle_field_map = {
                1: 'fieldIdCycle1',
                2: 'fieldIdCycle2', 
                3: 'fieldIdCycle3'
            }
            field_key = cycle_field_map.get(int(cycle))
            if field_key and field_key in item:
                field_id = item[field_key]
            else:
                # Fallback to current cycle field if historical not available
                field_id = item['currentCycleFieldId']
        else:
            # Use current cycle field as default
            field_id = item['currentCycleFieldId']
        
        # Handle outcome questions
        if qid.startswith('outcome_'):
            # Map both uppercase and original case
            id_map[qid.upper()] = field_id
            id_map[qid] = field_id
            # Also map without 'outcome_' prefix for flexibility
            short_id = qid.replace('outcome_', '').upper()
            id_map[f'OUTCOME_{short_id}'] = field_id
        else:
            # Regular questions (q1-q29)
            # Map lowercase version
            id_map[qid] = field_id
            # Map uppercase version
            id_map[qid.upper()] = field_id
            # Map just the number with Q prefix
            if qid.startswith('q'):
                num = qid[1:]
                id_map[f'Q{num}'] = field_id
                id_map[f'q{num}'] = field_id
    
    app.logger.info(f"Psychometric mapping created with {len(id_map)} entries for cycle {cycle}")
    app.logger.info(f"Sample mappings: {list(id_map.items())[:5]}")
    
    return id_map


def _fetch_psychometric_records(question_field_ids, base_filters, cycle=None):
    """Fetch records from object_29 containing the requested fields."""
    # Build field list with _raw so we get numeric value directly
    fields = []
    for fid in question_field_ids:
        fields.append(fid)
        fields.append(fid + '_raw')
    
    # Add cycle-specific completion check fields
    cycle_completion_fields = {
        1: 'field_1953',  # Cycle 1 completion field
        2: 'field_1955',  # Cycle 2 completion field
        3: 'field_1956'   # Cycle 3 completion field
    }
    
    # Add cycle filter if specified
    filters = base_filters.copy()
    if cycle and cycle in cycle_completion_fields:
        # Filter by checking if the cycle-specific field is not blank
        completion_field = cycle_completion_fields[cycle]
        filters.append({
            'field': completion_field,
            'operator': 'is not blank'
        })
        # Also add the field to fetch list to verify
        fields.append(completion_field)
        fields.append(completion_field + '_raw')
        app.logger.info(f"Added cycle filter for cycle {cycle} using field {completion_field}")
    
    # Always include student ID field for reconciliation
    fields.append('field_1819')  # Student connection field in object_29
    fields.append('field_1819_raw')
    
    # Add completion date field for academic year filtering
    fields.append('field_856')  # Completion date
    fields.append('field_856_raw')
    
    # First, determine if this is an Australian school
    # We need to check the establishment record to see if field_3508 is True
    is_australian_school = False
    establishment_id = None
    
    if base_filters:
        # Extract establishment ID from filters
        for f in base_filters:
            if f.get('field') == 'field_1821':  # Establishment field in object_29
                establishment_id = f.get('value')
                break
        
        # If no direct establishment filter, we might have a trust or staff admin filter
        # In these cases, we'll default to UK academic year unless we implement
        # a more complex logic to check all establishments in the trust
        if establishment_id:
            try:
                # Fetch establishment record to check if Australian
                est_data = make_knack_request('object_2', record_id=establishment_id, fields=['field_3508', 'field_3508_raw'])
                is_australian = est_data.get('field_3508_raw', False)
                if is_australian == 'true' or is_australian == True or is_australian == 'True':
                    is_australian_school = True
                    app.logger.info(f"Establishment {establishment_id} is an Australian school")
            except Exception as e:
                app.logger.warning(f"Could not check if establishment is Australian: {e}")
        else:
            # For trust or staff admin filters, we still apply academic year filtering
            # But we use UK academic year as the default when establishment is not specified
            app.logger.info("No establishment ID found in filters, using UK academic year for filtering")
    
    # Calculate academic year date boundaries
    from datetime import datetime
    today = datetime.now()
    
    if is_australian_school:
        # Australian schools: Calendar year (Jan 1 - Dec 31)
        academic_year_start = datetime(today.year, 1, 1)
        academic_year_end = datetime(today.year, 12, 31)
        app.logger.info(f"Using Australian academic year: {today.year}")
    else:
        # UK schools: Academic year (Aug 1 - Jul 31)
        if today.month >= 8:  # August or later
            academic_year_start = datetime(today.year, 8, 1)
            academic_year_end = datetime(today.year + 1, 7, 31)
            app.logger.info(f"Using UK academic year: {today.year}-{str(today.year + 1)[2:]}")
        else:  # January to July
            academic_year_start = datetime(today.year - 1, 8, 1)
            academic_year_end = datetime(today.year, 7, 31)
            app.logger.info(f"Using UK academic year: {today.year - 1}-{str(today.year)[2:]}")
    
    # Add date range filter for academic year
    # Format dates as dd/mm/yyyy for Knack (inclusive boundaries)
    # Subtract 1 day from start to make it inclusive, add 1 day to end
    from datetime import timedelta
    start_date_inclusive = academic_year_start - timedelta(days=1)
    end_date_inclusive = academic_year_end + timedelta(days=1)
    
    start_date_str = start_date_inclusive.strftime('%d/%m/%Y')
    end_date_str = end_date_inclusive.strftime('%d/%m/%Y')
    
    # Add date range filter using Knack's date operators
    # Using 'is after' and 'is before' to create an inclusive range
    filters.append({
        'match': 'and',
        'rules': [
            {
                'field': 'field_856',  # Completion date
                'operator': 'is after',
                'value': start_date_str
            },
            {
                'field': 'field_856',
                'operator': 'is before',
                'value': end_date_str
            }
        ]
    })
    
    app.logger.info(f"Added academic year filter: {start_date_str} to {end_date_str}")
    
    data = make_knack_request('object_29', filters=filters, fields=list(set(fields)))
    records = data.get('records', [])
    
    app.logger.info(f"Fetched {len(records)} psychometric records for cycle {cycle} in current academic year")
    
    return records


def _build_dataframe(question_ids, base_filters, cycle=None):
    """Return pandas dataframe with columns per question id (numeric 1-5)."""
    # Try Redis cache first
    cache_key_df = f"qla_df:{hashlib.md5(json.dumps({'q': question_ids, 'f': base_filters, 'c': cycle}).encode()).hexdigest()}"
    if CACHE_ENABLED:
        cached = redis_client.get(cache_key_df)
        if cached:
            try:
                # Decompress and unpickle
                return pickle.loads(gzip.decompress(cached))
            except Exception:
                pass
    
    mapping = _get_psychometric_mapping(cycle)
    field_ids = []
    
    # Extract establishment context from filters for logging
    establishment_context = "Unknown"
    for f in base_filters:
        if f.get('field') == 'field_1821' and f.get('value'):
            establishment_context = f"EstablishmentID: {f['value']}"
            break
    
    app.logger.info(f"_build_dataframe: Processing {len(question_ids)} question IDs for cycle {cycle} - {establishment_context}")
    app.logger.info(f"_build_dataframe: First 5 question IDs: {question_ids[:5]}")
    
    for qid in question_ids:
        # Try multiple variations of the question ID
        field = None
        for variant in [qid, qid.upper(), qid.lower()]:
            field = mapping.get(variant)
            if field:
                break
        
        if field:
            field_ids.append(field)
        else:
            app.logger.warning(f"_build_dataframe: No mapping found for question ID: {qid}")
    
    app.logger.info(f"_build_dataframe: Mapped to {len(field_ids)} field IDs")
    
    if not field_ids:
        app.logger.warning("_build_dataframe: No field IDs to fetch")
        return pd.DataFrame()
    
    records = _fetch_psychometric_records(field_ids, base_filters, cycle)
    app.logger.info(f"_build_dataframe: Fetched {len(records)} records")
    
    if not records:
        return pd.DataFrame()
    
    data_dict = {}
    for qid in question_ids:
        # Try multiple variations again
        f_id = None
        for variant in [qid, qid.upper(), qid.lower()]:
            f_id = mapping.get(variant)
            if f_id:
                break
        
        if not f_id:
            continue
            
        col_vals = []
        for rec in records:
            val = rec.get(f_id + '_raw')
            try:
                col_vals.append(float(val) if val is not None else None)
            except ValueError:
                col_vals.append(None)
        data_dict[qid] = col_vals
    
    df = pd.DataFrame(data_dict)
    app.logger.info(f"_build_dataframe: Created DataFrame with shape {df.shape}")
    
    # cache with compression
    if CACHE_ENABLED:
        try:
            compressed_df = gzip.compress(pickle.dumps(df))
            redis_client.setex(cache_key_df, 300, compressed_df)
        except Exception:
            pass
    return df

# === Analysis helpers ===

def quick_percent_agree(question_ids, filters, cycle=None):
    df = _build_dataframe(question_ids, filters, cycle)
    if df.empty:
        return {"percent": 0, "n": 0}
    
    # Handle multiple questions - calculate average percentage across all questions
    if len(question_ids) > 1:
        total_agree = 0
        total_responses = 0
        
        for q in question_ids:
            if q in df.columns:
                series = df[q].dropna()
                n = len(series)
                if n > 0:
                    agree_count = (series >= 4).sum()
                    total_agree += agree_count
                    total_responses += n
        
        if total_responses == 0:
            return {"percent": 0, "n": 0}
        
        percent = float(total_agree * 100 / total_responses)
        # For multiple questions, n represents average responses per question
        avg_n = int(total_responses / len(question_ids))
        return {"percent": round(percent, 1), "n": avg_n}
    else:
        # Single question - original logic
        q = question_ids[0]
        series = df[q].dropna()
        n = len(series)
        if n == 0:
            return {"percent": 0, "n": 0}
        percent = float((series >= 4).sum() * 100 / n)
        return {"percent": round(percent, 1), "n": n}


def quick_correlation(question_ids, filters, cycle=None):
    df = _build_dataframe(question_ids[:2], filters, cycle)
    if df.empty or df.shape[1] < 2:
        return {"r": None, "p": None, "n": 0}
    a, b = question_ids[:2]
    sub = df[[a, b]].dropna()
    if len(sub) < 3:
        return {"r": None, "p": None, "n": len(sub)}
    r, p = pearsonr(sub[a], sub[b])
    return {"r": round(r,3), "p": round(p,4), "n": len(sub)}


def quick_top_bottom(question_ids, filters, cycle=None):
    # If questionIds empty => evaluate all from mapping
    mapping = _get_psychometric_mapping(cycle)
    
    # Normalize question IDs to avoid duplicates
    if question_ids:
        qs = question_ids
    else:
        # Get unique questions by normalizing to lowercase base form
        unique_questions = set()
        for qid in mapping.keys():
            # Normalize to base form (e.g., 'Q1', 'q1' -> 'q1')
            normalized = qid.lower()
            # Handle outcome questions
            if normalized.startswith('outcome_'):
                unique_questions.add(normalized)
            # Handle regular questions
            elif normalized.startswith('q') and len(normalized) > 1:
                # Extract just the base question ID
                if '_' in normalized:
                    base = normalized.split('_')[0]
                else:
                    base = normalized
                unique_questions.add(base)
        qs = list(unique_questions)
    
    app.logger.info(f"quick_top_bottom: Processing {len(qs)} unique questions for cycle {cycle}")
    app.logger.info(f"quick_top_bottom: Filters: {filters}")
    app.logger.info(f"quick_top_bottom: Using cycle {cycle} for data fetching")
    
    df = _build_dataframe(qs, filters, cycle)
    
    if df.empty:
        app.logger.warning("quick_top_bottom: DataFrame is empty, no data found")
        return {"top": {}, "bottom": {}}
    
    app.logger.info(f"quick_top_bottom: DataFrame shape: {df.shape}")
    app.logger.info(f"quick_top_bottom: DataFrame columns: {list(df.columns)}")
    
    # Calculate means and counts for columns that have data
    means = df.mean().dropna()
    counts = df.count()
    
    if means.empty:
        app.logger.warning("quick_top_bottom: No valid means calculated")
        return {"top": {}, "bottom": {}}
    
    # Create combined data with means and counts
    combined_data = {}
    for qid in means.index:
        combined_data[qid] = {
            'score': round(means[qid], 2),
            'n': int(counts.get(qid, 0))
        }
    
    # Sort by score
    sorted_questions = sorted(combined_data.items(), key=lambda x: x[1]['score'], reverse=True)
    
    # Get top and bottom 5 (or fewer if less data available)
    top_count = min(5, len(sorted_questions))
    bottom_count = min(5, len(sorted_questions))
    
    top = dict(sorted_questions[:top_count])
    bottom = dict(sorted_questions[-bottom_count:])
    
    app.logger.info(f"quick_top_bottom: Found {len(top)} top questions and {len(bottom)} bottom questions")
    
    return {"top": top, "bottom": bottom}


# Extend qla_analysis

calc_dispatch = {
    "percentAgree": quick_percent_agree,
    "correlation": quick_correlation,
    "topBottom": quick_top_bottom,
    # themeMeans etc can be added later
}

# Modify existing qla_analysis wrapper
@app.route('/api/qla-analysis', methods=['POST'])
def qla_analysis():
    """Perform statistical analysis based on query type"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    analysis_type = data.get('analysisType')
    question_ids = data.get('questionIds', [])
    filters_param = data.get('filters', {})
    options = data.get('options', {})
    cycle = data.get('cycle', 1)  # Default to cycle 1 if not specified
    
    if not analysis_type:
        raise ApiError("Missing analysisType parameter")
    
    # Enhanced logging with establishment context
    establishment_id = filters_param.get('establishmentId', 'Unknown')
    establishment_name = filters_param.get('establishmentName', 'Unknown')
    
    app.logger.info(f"QLA analysis requested: {analysis_type} for questions: {question_ids}, cycle: {cycle}")
    app.logger.info(f"QLA analysis for establishment: {establishment_name} (ID: {establishment_id})")
    
    try:
        # Convert filters_param into proper list for builder
        base_filters = []
        if isinstance(filters_param, dict):
            if 'establishmentId' in filters_param:
                base_filters.append({
                    'field': 'field_1821',
                    'operator': 'is',
                    'value': filters_param['establishmentId']
                })
            if 'staffAdminId' in filters_param:
                base_filters.append({
                    'field': 'field_2069',
                    'operator': 'is',
                    'value': filters_param['staffAdminId']
                })
            if 'trustFieldValue' in filters_param:
                base_filters.append({
                    'field': 'field_3479', # Academy Trust text field in object_29
                    'operator': 'is',
                    'value': filters_param['trustFieldValue']
                })
            
            # Combine base filters with any additional filters from the frontend
            if 'additionalFilters' in filters_param and filters_param['additionalFilters']:
                base_filters.extend(filters_param['additionalFilters'])

        if analysis_type in calc_dispatch:
            result = calc_dispatch[analysis_type](question_ids, base_filters, cycle)
            app.logger.info(f"QLA analysis completed successfully for {establishment_name}")
        else:
            app.logger.error(f"Unknown analysis type '{analysis_type}' requested by {establishment_name}")
            raise ApiError(f"Unknown analysis type: {analysis_type}")
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"QLA analysis error for {establishment_name} (ID: {establishment_id}): {e}")
        app.logger.error(f"QLA analysis failed with filters: {filters_param}")
        raise ApiError(f"Analysis failed: {str(e)}", 500)

@app.route('/api/qla-correlation', methods=['POST'])
def qla_correlation():
    """Calculate correlations between questions"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    # TODO: Implement correlation calculation
    return jsonify({
        'correlations': [],
        'message': 'Correlation analysis will be implemented'
    })

@app.route('/api/qla-trends', methods=['POST'])
def qla_trends():
    """Analyze trends across cycles"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    # TODO: Implement trend analysis
    return jsonify({
        'trends': [],
        'message': 'Trend analysis will be implemented'
    })

# --- New Batch QLA Analysis Endpoint ---
@app.route('/api/qla-batch-analysis', methods=['POST'])
def qla_batch_analysis():
    """Perform multiple QLA analyses in a single request to improve performance"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    analyses = data.get('analyses', [])
    filters_param = data.get('filters', {})
    cycle = data.get('cycle', 1)  # Default to cycle 1 if not specified
    
    if not analyses:
        raise ApiError("Missing analyses parameter")
    
    app.logger.info(f"QLA batch analysis requested for {len(analyses)} insights, cycle: {cycle}")
    
    try:
        # Convert filters
        base_filters = []
        if isinstance(filters_param, dict):
            if 'establishmentId' in filters_param:
                base_filters.append({
                    'field': 'field_1821',
                    'operator': 'is',
                    'value': filters_param['establishmentId']
                })
            if 'staffAdminId' in filters_param:
                base_filters.append({
                    'field': 'field_2069',
                    'operator': 'is',
                    'value': filters_param['staffAdminId']
                })
            if 'trustFieldValue' in filters_param:
                base_filters.append({
                    'field': 'field_3479', # Academy Trust text field in object_29
                    'operator': 'is',
                    'value': filters_param['trustFieldValue']
                })
            
            # Combine base filters with any additional filters from the frontend
            if 'additionalFilters' in filters_param and filters_param['additionalFilters']:
                base_filters.extend(filters_param['additionalFilters'])
        
        # Collect all unique question IDs
        all_question_ids = set()
        for analysis in analyses:
            all_question_ids.update(analysis.get('questionIds', []))
        
        # Fetch data once for all questions
        df = _build_dataframe(list(all_question_ids), base_filters, cycle)
        
        # Process each analysis using the same dataframe
        results = {}
        for analysis in analyses:
            insight_id = analysis.get('id')
            analysis_type = analysis.get('type', 'percentAgree')
            question_ids = analysis.get('questionIds', [])
            
            if analysis_type == 'percentAgree':
                # Calculate directly from the dataframe
                if df.empty:
                    results[insight_id] = {"percent": 0, "n": 0}
                elif len(question_ids) > 1:
                    # Multiple questions
                    total_agree = 0
                    total_responses = 0
                    
                    for q in question_ids:
                        if q in df.columns:
                            series = df[q].dropna()
                            n = len(series)
                            if n > 0:
                                agree_count = (series >= 4).sum()
                                total_agree += agree_count
                                total_responses += n
                    
                    if total_responses == 0:
                        results[insight_id] = {"percent": 0, "n": 0}
                    else:
                        percent = float(total_agree * 100 / total_responses)
                        avg_n = int(total_responses / len(question_ids))
                        results[insight_id] = {"percent": round(percent, 1), "n": avg_n}
                else:
                    # Single question
                    q = question_ids[0]
                    if q in df.columns:
                        series = df[q].dropna()
                        n = len(series)
                        if n == 0:
                            results[insight_id] = {"percent": 0, "n": 0}
                        else:
                            percent = float((series >= 4).sum() * 100 / n)
                            results[insight_id] = {"percent": round(percent, 1), "n": n}
                    else:
                        results[insight_id] = {"percent": 0, "n": 0}
            else:
                # Other analysis types can be added here
                results[insight_id] = {"error": f"Unsupported analysis type: {analysis_type}"}
        
        return jsonify(results)
        
    except Exception as e:
        app.logger.error(f"QLA batch analysis error: {e}")
        raise ApiError(f"Batch analysis failed: {str(e)}", 500)

# --- QLA AI Chat (Enhanced) ---
@app.route('/api/qla-chat', methods=['POST'])
def qla_chat():
    data = request.get_json()
    if not data or 'query' not in data:
        raise ApiError("Missing 'query' in request body")
    
    user_query = data['query']
    question_data = data.get('questionData', [])

    # Check if OpenAI API key is configured
    if not OPENAI_API_KEY:
        app.logger.warning("OpenAI API key not configured - returning placeholder response")
        return jsonify({'answer': f"AI analysis for '{user_query}' - OpenAI integration pending configuration."})

    app.logger.info(f"Received QLA chat query: {user_query}")
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        # Prepare context from question data
        context = prepare_question_context(question_data)
        
        # Construct prompt
        prompt = f"""You are an educational data analyst helping to interpret questionnaire response data.
        
Context: {context}

User Question: {user_query}

Provide a clear, actionable analysis that helps improve student outcomes. Include specific recommendations where appropriate."""

        # Call OpenAI API with new syntax
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert educational data analyst specializing in student questionnaire analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        answer = response.choices[0].message['content']
        
        return jsonify({'answer': answer})
        
    except Exception as e:
        app.logger.error(f"OpenAI API error: {e}")
        return jsonify({'answer': f"AI analysis temporarily unavailable. Error: {str(e)}"})

def prepare_question_context(question_data):
    """Prepare context from question data for AI analysis"""
    if not question_data or len(question_data) == 0:
        return "Limited question data available."
    
    # Summarize the data (this is a simplified version)
    total_responses = len(question_data)
    context = f"Analysis based on {total_responses} responses. "
    
    # Add more context as needed
    return context

# --- Comment Analysis Endpoints ---
@app.route('/api/comment-wordcloud', methods=['POST'])
def generate_wordcloud():
    """Generate word cloud data from student comments"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    comment_fields = data.get('commentFields', [])
    filters = data.get('filters', {})
    cycle = data.get('cycle')  # Get cycle from request
    
    app.logger.info(f"Generating word cloud for fields: {comment_fields}, cycle: {cycle}")
    
    try:
        # Import required libraries
        import nltk
        from textblob import TextBlob
        from collections import Counter
        import re
        
        # Download required NLTK data (do this once in production)
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        # Ensure essential corpora for tokenisation & sentiment exist
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')
        # TextBlob additional corpora
        try:
            from textblob import download_corpora as _tb_dl
            _tb_dl.download_all()
        except Exception:
            pass
        
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
        
        # Add custom stop words for educational context
        custom_stop_words = {
            'need', 'needs', 'would', 'could', 'should', 'think', 'feel', 'feels',
            'really', 'much', 'many', 'also', 'well', 'good', 'better', 'best',
            'help', 'helps', 'make', 'makes', 'get', 'gets', 'know', 'knows',
            'want', 'wants', 'like', 'likes', 'time', 'year', 'work', 'works'
        }
        stop_words.update(custom_stop_words)
        
        # Build filters for fetching VESPA results
        knack_filters = []
        establishment_id = None
        
        if filters.get('establishmentId'):
            establishment_id = filters['establishmentId']
            knack_filters.append({
                'field': 'field_133',
                'operator': 'is',
                'value': establishment_id
            })
        elif filters.get('staffAdminId'):
            knack_filters.append({
                'field': 'field_439',
                'operator': 'is',
                'value': filters['staffAdminId']
            })
        elif filters.get('trustFieldValue'):
            knack_filters.append({
                'field': 'field_3478',
                'operator': 'is',
                'value': filters['trustFieldValue']
            })
        
        # Add academic year filter for current academic year comments
        academic_year_filter = get_academic_year_filters(establishment_id, 'field_855', 'field_3511')
        knack_filters.append(academic_year_filter)
        
        # Add cycle filter if provided
        if cycle:
            knack_filters.append({
                'field': 'field_146',
                'operator': 'is',
                'value': str(cycle)
            })
            app.logger.info(f"Added cycle filter for cycle {cycle}")
        
        # Combine base filters with any additional filters from the frontend
        if 'additionalFilters' in filters and filters['additionalFilters']:
            knack_filters.extend(filters['additionalFilters'])
        
        # Fetch VESPA results with comment fields
        fields_to_fetch = ['id', 'field_855', 'field_855_raw', 'field_3511_raw'] + [f + '_raw' for f in comment_fields]
        
        all_comments = []
        page = 1
        max_pages = 10  # Increased to handle larger datasets
        
        while page <= max_pages:
            vespa_data = make_knack_request(
                'object_10',
                filters=knack_filters,
                page=page,
                rows_per_page=500,
                fields=fields_to_fetch
            )
            
            records = vespa_data.get('records', [])
            if not records:
                break
            
            # Extract comments from records
            for record in records:
                for field in comment_fields:
                    comment = record.get(field + '_raw')
                    if comment and isinstance(comment, str) and len(comment.strip()) > 0:
                        all_comments.append(comment.strip())
            
            if len(records) < 500:
                # Don't break - there might be more data on subsequent pages
                pass
            page += 1
        
        app.logger.info(f"Collected {len(all_comments)} comments")
        
        # If no comments found, return empty result
        if not all_comments:
            return jsonify({
                'wordCloudData': [],
                'totalComments': 0,
                'uniqueWords': 0,
                'topWord': None,
                'message': 'No comments found for the selected filters'
            })
        
        # Process comments
        word_freq = Counter()
        
        for comment in all_comments:
            # Clean and tokenize
            # Remove URLs, email addresses, and special characters
            comment = re.sub(r'http\S+|www.\S+|@\S+', '', comment)
            comment = re.sub(r'[^\w\s]', ' ', comment)
            
            blob = TextBlob(comment.lower())
            words = blob.words
            
            # Filter out stop words, short words, and numbers
            filtered_words = [
                word for word in words 
                if word not in stop_words 
                and len(word) > 3 
                and not word.isdigit()
                and word.isalpha()
            ]
            word_freq.update(filtered_words)
        
        # Get top 100 words
        top_words = word_freq.most_common(100)
        
        # Calculate sentiment for top words (simplified)
        word_sentiments = {}
        for word, _ in top_words[:50]:  # Analyze top 50 for performance
            try:
                blob = TextBlob(word)
                sentiment = blob.sentiment.polarity
                word_sentiments[word] = sentiment
            except:
                word_sentiments[word] = 0
        
        # Format for word cloud with relative sizing
        max_count = top_words[0][1] if top_words else 1
        word_cloud_data = []
        
        for word, count in top_words:
            # Scale size between 10 and 100 based on frequency
            size = int(10 + (count / max_count) * 90)
            sentiment = word_sentiments.get(word, 0)
            
            word_cloud_data.append({
                'text': word,
                'size': size,
                'count': count,
                'sentiment': round(sentiment, 2)
            })
        
        return jsonify({
            'wordCloudData': word_cloud_data,
            'totalComments': len(all_comments),
            'uniqueWords': len(word_freq),
            'topWord': top_words[0] if top_words else None
        })
        
    except Exception as e:
        app.logger.error(f"Word cloud generation error: {e}")
        raise ApiError(f"Failed to generate word cloud: {str(e)}", 500)

@app.route('/api/comment-themes', methods=['POST'])
def analyze_themes():
    """Extract themes from student comments using AI"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    comment_fields = data.get('commentFields', [])
    filters = data.get('filters', {})
    
    app.logger.info(f"Analyzing themes for fields: {comment_fields}")
    
    try:
        # Build filters for fetching VESPA results
        knack_filters = []
        establishment_id = None
        
        if filters.get('establishmentId'):
            establishment_id = filters['establishmentId']
            knack_filters.append({
                'field': 'field_133',
                'operator': 'is',
                'value': establishment_id
            })
        elif filters.get('staffAdminId'):
            knack_filters.append({
                'field': 'field_439',
                'operator': 'is',
                'value': filters['staffAdminId']
            })
        elif filters.get('trustFieldValue'):
            knack_filters.append({
                'field': 'field_3478',
                'operator': 'is',
                'value': filters['trustFieldValue']
            })
        
        # Add academic year filter for current academic year comments
        academic_year_filter = get_academic_year_filters(establishment_id, 'field_855', 'field_3511')
        knack_filters.append(academic_year_filter)
        
        # Add cycle filter if provided
        if cycle:
            knack_filters.append({
                'field': 'field_146',
                'operator': 'is',
                'value': str(cycle)
            })
            app.logger.info(f"Added cycle filter for cycle {cycle}")
        
        # Combine base filters with any additional filters from the frontend
        if 'additionalFilters' in filters and filters['additionalFilters']:
            knack_filters.extend(filters['additionalFilters'])
        
        # Fetch VESPA results with comment fields
        fields_to_fetch = ['id', 'field_855', 'field_855_raw', 'field_3511_raw'] + [f + '_raw' for f in comment_fields]
        
        all_comments = []
        page = 1
        max_pages = 10  # Increased to handle larger datasets
        
        while page <= max_pages:
            vespa_data = make_knack_request(
                'object_10',
                filters=knack_filters,
                page=page,
                rows_per_page=500,
                fields=fields_to_fetch
            )
            
            records = vespa_data.get('records', [])
            if not records:
                break
            
            # Extract comments from records
            for record in records:
                for field in comment_fields:
                    comment = record.get(field + '_raw')
                    if comment and isinstance(comment, str) and len(comment.strip()) > 0:
                        all_comments.append(comment.strip())
            
            if len(records) < 500:
                # Don't break - there might be more data on subsequent pages
                pass
            page += 1
        
        app.logger.info(f"Collected {len(all_comments)} comments for theme analysis")
        
        # If no comments found, return empty result
        if not all_comments:
            return jsonify({
                'themes': [],
                'totalThemes': 0,
                'totalComments': 0,
                'message': 'No comments found for theme analysis'
            })
        
        # Use OpenAI to analyze themes
        if OPENAI_API_KEY:
            try:
                import openai
                openai.api_key = OPENAI_API_KEY
                
                # Sample comments if too many (to avoid token limits and timeouts)
                comments_to_analyze = all_comments
                if len(all_comments) > 50:
                    # Take a smaller representative sample to avoid timeouts
                    import random
                    comments_to_analyze = random.sample(all_comments, 50)
                    app.logger.info(f"Sampled 50 comments from {len(all_comments)} for analysis")
                elif len(all_comments) > 30:
                    # For medium datasets, sample a bit
                    import random
                    comments_to_analyze = random.sample(all_comments, 30)
                    app.logger.info(f"Sampled 30 comments from {len(all_comments)} for analysis")
                
                # Prepare the prompt
                comments_text = '\n'.join([f"- {comment}" for comment in comments_to_analyze])
                
                prompt = f"""Analyze these student comments and identify the main themes. For each theme:
1. Give it a clear, descriptive name
2. Count how many comments relate to it
3. Determine the overall sentiment (positive, negative, or mixed)
4. Select 2-3 representative example quotes

Return the results as a JSON array with this structure:
[
  {{
    "theme": "Theme Name",
    "count": number,
    "sentiment": "positive|negative|mixed",
    "examples": ["quote 1", "quote 2"]
  }}
]

Focus on themes related to learning, support, challenges, goals, and academic experience.

Student Comments:
{comments_text}

Important: Return ONLY the JSON array, no additional text."""

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-16k" if len(prompt) > 3000 else "gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an educational data analyst specializing in identifying themes from student feedback. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                themes_text = response.choices[0].message['content'].strip()
                
                # Parse the JSON response
                try:
                    # Clean up the response if needed
                    if themes_text.startswith('```json'):
                        themes_text = themes_text[7:]
                    if themes_text.endswith('```'):
                        themes_text = themes_text[:-3]
                    
                    themes = json.loads(themes_text)
                    
                    # Sort themes by count
                    themes.sort(key=lambda x: x.get('count', 0), reverse=True)
                    
                    # Take top 6 themes
                    themes = themes[:6]
                    
                    return jsonify({
                        'themes': themes,
                        'totalThemes': len(themes),
                        'totalComments': len(all_comments),
                        'sampledComments': len(comments_to_analyze) if len(comments_to_analyze) < len(all_comments) else None
                    })
                    
                except json.JSONDecodeError as e:
                    app.logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                    app.logger.error(f"Response was: {themes_text}")
                    
                    # Fallback to simple theme extraction
                    return jsonify({
                        'themes': [],
                        'totalThemes': 0,
                        'totalComments': len(all_comments),
                        'message': 'Theme extraction completed but failed to parse results',
                        'error': 'JSON parsing failed'
                    })
                    
            except Exception as e:
                app.logger.error(f"OpenAI theme analysis error: {e}")
                return jsonify({
                    'themes': [],
                    'totalThemes': 0,
                    'totalComments': len(all_comments),
                    'message': f'Theme analysis error: {str(e)}'
                })
        else:
            # No OpenAI key configured
            return jsonify({
                'themes': [],
                'totalThemes': 0,
                'totalComments': len(all_comments),
                'message': 'Theme analysis requires OpenAI API configuration'
            })
        
    except Exception as e:
        app.logger.error(f"Theme analysis error: {e}")
        raise ApiError(f"Failed to analyze themes: {str(e)}", 500)

@app.route('/api/comment-themes-fast', methods=['POST'])
def analyze_themes_from_wordcloud():
    """Extract themes from word cloud data using AI - much faster than analyzing raw comments"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    app.logger.info("Analyzing themes from word cloud data (fast method)")
    
    try:
        # First get the word cloud data
        comment_fields = data.get('commentFields', [])
        filters = data.get('filters', {})
        
        # Call the word cloud generation internally
        from flask import current_app
        with current_app.test_request_context(json=data):
            wordcloud_response = generate_wordcloud()
            wordcloud_data = wordcloud_response.get_json()
        
        if not wordcloud_data or not wordcloud_data.get('wordCloudData'):
            return jsonify({
                'themes': [],
                'totalThemes': 0,
                'totalComments': wordcloud_data.get('totalComments', 0),
                'message': 'No word cloud data available for theme analysis'
            })
        
        # Use OpenAI to analyze themes from word patterns
        if OPENAI_API_KEY:
            try:
                import openai
                openai.api_key = OPENAI_API_KEY
                
                # Get top words with their frequencies
                top_words = wordcloud_data['wordCloudData'][:50]  # Top 50 words
                total_comments = wordcloud_data.get('totalComments', 0)
                
                # Create a text representation of word patterns
                word_patterns = []
                for word_data in top_words:
                    word = word_data['text']
                    count = word_data['count']
                    sentiment = word_data.get('sentiment', 0)
                    
                    # Include sentiment indicator
                    sentiment_label = 'positive' if sentiment > 0.1 else 'negative' if sentiment < -0.1 else 'neutral'
                    word_patterns.append(f"{word} (mentioned {count} times, {sentiment_label})")
                
                patterns_text = '\n'.join(word_patterns)
                
                prompt = f"""Based on these frequently mentioned words from {total_comments} student comments, identify the main themes.

Word patterns (word, frequency, sentiment):
{patterns_text}

Analyze these patterns and identify 4-6 main themes. For each theme:
1. Give it a clear, descriptive name based on the related words
2. Estimate how many comments might relate to it (based on word frequencies)
3. Determine the overall sentiment (positive, negative, or mixed) based on word sentiments
4. List the key words that support this theme

Return the results as a JSON array with this structure:
[
  {{
    "theme": "Theme Name",
    "count": estimated_number,
    "sentiment": "positive|negative|mixed",
    "examples": ["key word 1", "key word 2", "key word 3"]
  }}
]

Focus on themes related to learning, support, challenges, goals, and academic experience.

Important: Return ONLY the JSON array, no additional text."""

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an educational data analyst specializing in identifying themes from word patterns. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1500
                )
                
                themes_text = response.choices[0].message['content'].strip()
                
                # Parse the JSON response
                try:
                    # Clean up the response if needed
                    if themes_text.startswith('```json'):
                        themes_text = themes_text[7:]
                    if themes_text.endswith('```'):
                        themes_text = themes_text[:-3]
                    
                    themes = json.loads(themes_text)
                    
                    # Sort themes by count
                    themes.sort(key=lambda x: x.get('count', 0), reverse=True)
                    
                    # Take top 6 themes
                    themes = themes[:6]
                    
                    return jsonify({
                        'themes': themes,
                        'totalThemes': len(themes),
                        'totalComments': total_comments,
                        'method': 'word_patterns',
                        'processingTime': 'fast'
                    })
                    
                except json.JSONDecodeError as e:
                    app.logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                    app.logger.error(f"Response was: {themes_text}")
                    
                    return jsonify({
                        'themes': [],
                        'totalThemes': 0,
                        'totalComments': total_comments,
                        'message': 'Theme extraction completed but failed to parse results'
                    })
                    
            except Exception as e:
                app.logger.error(f"OpenAI theme analysis error: {e}")
                return jsonify({
                    'themes': [],
                    'totalThemes': 0,
                    'totalComments': total_comments,
                    'message': f'Theme analysis error: {str(e)}'
                })
        else:
            # No OpenAI key configured
            return jsonify({
                'themes': [],
                'totalThemes': 0,
                'totalComments': total_comments,
                'message': 'Theme analysis requires OpenAI API configuration'
            })
        
    except Exception as e:
        app.logger.error(f"Fast theme analysis error: {e}")
        raise ApiError(f"Failed to analyze themes: {str(e)}", 500)

@app.route('/api/comment-sentiment', methods=['POST'])
def analyze_sentiment():
    """Analyze sentiment of student comments"""
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    try:
        from textblob import TextBlob
        
        comments = data.get('comments', [])
        
        sentiment_results = {
            'positive': 0,
            'neutral': 0,
            'negative': 0,
            'overall_polarity': 0
        }
        
        polarities = []
        
        for comment in comments:
            if comment and isinstance(comment, str):
                blob = TextBlob(comment)
                polarity = blob.sentiment.polarity
                polarities.append(polarity)
                
                if polarity > 0.1:
                    sentiment_results['positive'] += 1
                elif polarity < -0.1:
                    sentiment_results['negative'] += 1
                else:
                    sentiment_results['neutral'] += 1
        
        if polarities:
            sentiment_results['overall_polarity'] = sum(polarities) / len(polarities)
        
        return jsonify(sentiment_results)
        
    except Exception as e:
        app.logger.error(f"Sentiment analysis error: {e}")
        raise ApiError(f"Failed to analyze sentiment: {str(e)}", 500)

# --- Test Endpoint for CORS and Connection Verification ---
@app.route('/api/test', methods=['GET', 'OPTIONS'])
def test_endpoint():
    """Test endpoint to verify CORS and backend connectivity"""
    return jsonify({
        'status': 'ok',
        'message': 'VESPA Dashboard Backend is accessible',
        'cors_configured': True,
        'knack_configured': bool(KNACK_APP_ID and KNACK_API_KEY),
        'timestamp': str(datetime.now())
    })

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    health_status = {
        'status': 'healthy',
        'timestamp': str(datetime.now()),
        'services': {
            'knack_api': bool(KNACK_APP_ID and KNACK_API_KEY),
            'openai_api': bool(OPENAI_API_KEY),
            'redis_cache': CACHE_ENABLED
        }
    }
    
    # Test Redis connection if enabled
    if CACHE_ENABLED:
        try:
            redis_client.ping()
            health_status['services']['redis_status'] = 'connected'
        except:
            health_status['services']['redis_status'] = 'disconnected'
            health_status['status'] = 'degraded'
    
    return jsonify(health_status)

@app.route('/api/filter-options', methods=['GET'])
def get_filter_options():
    """Fetch unique values for filter dropdowns based on object and establishment."""
    object_key = request.args.get('objectKey')
    establishment_id = request.args.get('establishmentId')
    filter_fields_str = request.args.get('fields') # Comma-separated list of field keys

    if not object_key or not establishment_id or not filter_fields_str:
        raise ApiError("Missing required parameters: objectKey, establishmentId, and fields")

    filter_fields = [field.strip() for field in filter_fields_str.split(',')] # Split comma-separated fields

    try:
        app.logger.info(f"Fetching filter options for object {object_key}, establishment {establishment_id}, fields: {filter_fields}")

        base_filters = [
            {
                'field': 'field_133', # Assuming field_133 is the link to establishment in object_10
                'operator': 'is',
                'value': establishment_id
            }
        ]

        # Fetch ALL records for the given object and establishment.
        # This is necessary to get all potential filter values within that subset.
        # The performance bottleneck is fetching all records, but filtering *before*\
        # extracting unique values on the backend is still more efficient than doing it client-side.
        all_records = []
        page = 1
        # Using a larger rows_per_page here to minimize API calls
        rows_per_page = 1000
        while True:
            data = make_knack_request(object_key, filters=base_filters, page=page, rows_per_page=rows_per_page) # Corrected rows_per_per_page to rows_per_page
            records = data.get('records', [])

            if not records:
                break

            all_records.extend(records)

            if len(records) < rows_per_page or page > 100: # Safety limit for very large schools
                break

            page += 1

        app.logger.info(f"Fetched {len(all_records)} records for filter option extraction.")

        # Extract unique values for the requested fields
        unique_values = {}
        for field in filter_fields:
            unique_values[field] = set()

        for record in all_records:
            for field in filter_fields:
                field_value = record.get(f'{field}_raw') or record.get(field)
                if field_value is not None and field_value != '':
                    # Handle potential array of linked values or single values
                    if isinstance(field_value, list):
                        for item in field_value:
                            if isinstance(item, dict) and item.get('id'):
                                display_value = item.get('identifier') or item.get('value') or item.get('id')
                                unique_values[field].add(json.dumps({'id': item['id'], 'name': display_value}))
                            elif isinstance(item, str) and item.strip():
                                unique_values[field].add(item.strip())
                    elif isinstance(field_value, dict) and field_value.get('id'):
                         unique_values[field].add(json.dumps({
                            'id': field_value['id'],
                            'name': field_value.get('identifier') or field_value.get('value') or field_value.get('id')
                        }))
                    elif isinstance(field_value, str) and field_value.strip():
                        value = field_value.strip()
                        if value and value != 'null' and value != 'undefined':
                            unique_values[field].add(value)

        # Convert sets to lists and parse JSON strings back to objects for object values
        processed_unique_values = {}
        for field, values in unique_values.items():
            processed_values = []
            for val in values:
                try:
                    # Try to parse as JSON (for linked objects)
                    parsed_val = json.loads(val)
                    processed_values.append(parsed_val)
                except json.JSONDecodeError:
                    # If not JSON, it's a plain string
                    processed_values.append(val)
            # Sort the values alphabetically by name or string value
            processed_values.sort(key=lambda x: x.get('name', x) if isinstance(x, dict) else x)
            processed_unique_values[field] = processed_values

        return jsonify({
            'filter_options': processed_unique_values
        })

    except Exception as e:
        app.logger.error(f"Failed to fetch filter options: {e}")
        raise ApiError(f"Failed to fetch filter options: {str(e)}", 500)

# --- ERI (Exam Readiness Index) Endpoint ---
@app.route('/api/calculate-eri', methods=['GET'])
def calculate_eri():
    """Calculate Exam Readiness Index for a school/establishment."""
    try:
        # Get parameters
        staff_admin_id = request.args.get('staffAdminId')
        establishment_id = request.args.get('establishmentId')
        cycle = request.args.get('cycle', '1')
        
        # Validate cycle
        if cycle not in ['1', '2', '3']:
            raise ApiError("Invalid cycle. Must be 1, 2, or 3.")
        
        # Build filters for psychometric responses (object_29)
        filters = []
        
        if establishment_id:
            filters.append({
                'field': 'field_1821',  # VESPA Customer field in object_29
                'operator': 'is',
                'value': establishment_id
            })
        elif staff_admin_id:
            filters.append({
                'field': 'field_2069',  # Staff Admin field in object_29
                'operator': 'is',
                'value': staff_admin_id
            })
        else:
            raise ApiError("Either staffAdminId or establishmentId must be provided")
        
        # Map cycle to ERI field
        eri_field_map = {
            '1': 'field_2868',
            '2': 'field_2869',
            '3': 'field_2870'
        }
        
        eri_field = eri_field_map[cycle]
        
        # Fetch psychometric responses
        app.logger.info(f"Fetching psychometric responses for ERI calculation with filters: {filters}")
        
        all_responses = []
        page = 1
        max_pages = request.args.get('max_pages', 3, type=int)
        while True:
            data = make_knack_request('object_29', filters=filters, page=page, rows_per_page=1000)
            records = data.get('records', [])
            
            if not records:
                break
                
            all_responses.extend(records)
            
            if len(records) < 1000 or page > max_pages:  # Stop after max_pages to avoid timeout
                break
                
            page += 1
        
        app.logger.info(f"Found {len(all_responses)} psychometric responses")
        
        # Calculate average ERI
        total_eri = 0
        valid_responses = 0
        
        for response in all_responses:
            eri_value = response.get(f'{eri_field}_raw')
            if eri_value is not None:
                try:
                    eri_float = float(eri_value)
                    if 1 <= eri_float <= 5:  # Valid range for psychometric scale
                        total_eri += eri_float
                        valid_responses += 1
                except (ValueError, TypeError):
                    continue
        
        if valid_responses == 0:
            return jsonify({
                'school_eri': None,
                'response_count': 0,
                'message': 'No valid ERI responses found'
            })
        
        average_eri = total_eri / valid_responses
        
        app.logger.info(f"Calculated ERI: {average_eri:.2f} from {valid_responses} responses")
        
        return jsonify({
            'school_eri': round(average_eri, 2),
            'response_count': valid_responses,
            'cycle': cycle
        })
        
    except ApiError as e:
        raise e
    except Exception as e:
        app.logger.error(f"Failed to calculate ERI: {e}")
        raise ApiError(f"Failed to calculate ERI: {str(e)}", 500)

# --- National ERI Endpoint ---
@app.route('/api/national-eri', methods=['GET'])
def get_national_eri():
    """Get national ERI benchmark for a specific cycle."""
    try:
        cycle = request.args.get('cycle', '1')
        
        # Validate cycle
        if cycle not in ['1', '2', '3']:
            raise ApiError("Invalid cycle. Must be 1, 2, or 3.")
        
        # Map cycle to actual field IDs in object_120
        national_eri_field_map = {
            '1': 'field_3432',  # ERI_cycle1
            '2': 'field_3433',  # ERI_cycle2
            '3': 'field_3434'   # ERI_cycle3
        }
        
        eri_field = national_eri_field_map[cycle]
        
        # Fetch latest national benchmark record
        app.logger.info(f"Fetching national ERI for cycle {cycle} from object_120")
        
        data = make_knack_request(
            'object_120',
            filters=[],
            page=1,
            rows_per_page=1,
            sort_field='field_3307',  # Date Time field
            sort_order='desc'
        )
        
        records = data.get('records', [])
        if not records:
            app.logger.warning("No national benchmark data found in object_120")
            # Return placeholder if no data exists yet
            return jsonify({
                'national_eri': 3.5,
                'cycle': cycle,
                'source': 'placeholder',
                'message': 'No national benchmark data found'
            })
        
        national_record = records[0]
        national_eri_raw = national_record.get(f'{eri_field}_raw')
        
        if national_eri_raw is None:
            app.logger.warning(f"National ERI field {eri_field} is empty for cycle {cycle}")
            # Return placeholder if field is empty
            return jsonify({
                'national_eri': 3.5,
                'cycle': cycle,
                'source': 'placeholder',
                'message': f'National ERI not yet calculated for cycle {cycle}'
            })
        
        try:
            national_eri = float(national_eri_raw)
            app.logger.info(f"Found national ERI: {national_eri} for cycle {cycle}")
            
            return jsonify({
                'national_eri': round(national_eri, 2),
                'cycle': cycle,
                'source': 'object_120',
                'record_date': national_record.get('field_3307', 'Unknown')  # Include the date of the benchmark
            })
            
        except (ValueError, TypeError) as e:
            app.logger.error(f"Invalid national ERI value: {national_eri_raw}")
            return jsonify({
                'national_eri': 3.5,
                'cycle': cycle,
                'source': 'placeholder',
                'message': 'Invalid national ERI value in database'
            })
        
    except ApiError as e:
        raise e
    except Exception as e:
        app.logger.error(f"Failed to get national ERI: {e}")
        raise ApiError(f"Failed to get national ERI: {str(e)}", 500)

@app.route('/api/establishments/popular', methods=['GET'])
@cached(ttl_key='popular_establishments', ttl_seconds=3600)  # Cache for 1 hour
def get_popular_establishments():
    """Get most active establishments based on recent VESPA results"""
    try:
        # Get establishments with most recent activity
        # Sort by most recent submission date
        records = make_knack_request(
            'object_10',  # VESPA Results
            rows_per_page=500,
            page=1,
            sort_field='field_132',  # Date submitted
            sort_order='desc',
            fields=['field_133', 'field_133_raw', 'field_132']  # Establishment and date
        )
        
        if not records:
            return jsonify({'establishments': []})
        
        # Count establishment occurrences
        establishment_counts = {}
        establishment_names = {}
        
        for record in records:
            est_display = record.get('field_133')
            est_raw = record.get('field_133_raw')
            
            if est_raw and est_display:
                if isinstance(est_raw, list):
                    for i, est_id in enumerate(est_raw):
                        if est_id:
                            est_name = est_display[i] if isinstance(est_display, list) and i < len(est_display) else est_display
                            establishment_counts[est_id] = establishment_counts.get(est_id, 0) + 1
                            establishment_names[est_id] = est_name
                else:
                    establishment_counts[est_raw] = establishment_counts.get(est_raw, 0) + 1
                    establishment_names[est_raw] = est_display
        
        # Sort by count and get top 10
        sorted_establishments = sorted(
            establishment_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # Format results
        popular = []
        for est_id, count in sorted_establishments:
            popular.append({
                'id': est_id,
                'name': establishment_names.get(est_id, 'Unknown'),
                'activity_count': count
            })
        
        return jsonify({'establishments': popular})
        
    except Exception as e:
        app.logger.error(f"Error fetching popular establishments: {str(e)}")
        return jsonify({'establishments': []}), 500

# --- Background Pre-caching System ---
def precache_establishment_data(establishment_id, establishment_name=None):
    """Pre-cache all data for an establishment in the background"""
    try:
        app.logger.info(f"Starting background pre-cache for establishment {establishment_id}")
        
        # Pre-cache for all 3 cycles
        for cycle in [1, 2, 3]:
            cache_key = f"dashboard_data:none:{establishment_id}:{cycle}:1:1000"
            
            # Check if already cached
            if CACHE_ENABLED:
                try:
                    existing = redis_client.get(cache_key)
                    if existing:
                        app.logger.info(f"Establishment {establishment_id} cycle {cycle} already cached")
                        continue
                except:
                    pass
            
            # Fetch and cache the data
            try:
                # Build filters
                base_filters = [{
                    'field': 'field_133',
                    'operator': 'is',
                    'value': establishment_id
                }]
                
                # Fetch VESPA results with minimal fields for speed
                vespa_records = []
                page = 1
                while page <= 2:  # Limit to 2 pages for pre-cache
                    data = make_knack_request(
                        'object_10',
                        filters=base_filters,
                        page=page,
                        rows_per_page=1000,
                        fields=['id', 'field_133', 'field_133_raw', 'field_439_raw', 
                               f'field_{155 + (cycle-1)*6}_raw',  # Vision score for cycle
                               f'field_{160 + (cycle-1)*6}_raw']  # Overall score for cycle
                    )
                    records = data.get('records', [])
                    if not records:
                        break
                    vespa_records.extend(records)
                    if len(records) < 1000:
                        break
                    page += 1
                
                # Create minimal cache entry
                cache_data = {
                    'vespaResults': vespa_records,
                    'nationalBenchmark': {},  # Will be fetched separately
                    'filterOptions': {'groups': [], 'courses': [], 'yearGroups': [], 'faculties': []},
                    'cycle': cycle,
                    'staffAdminId': None,
                    'establishmentId': establishment_id,
                    'precached': True,
                    'timestamp': time.time()
                }
                
                # Store in cache with longer TTL for pre-cached data
                if CACHE_ENABLED:
                    try:
                        compressed_data = gzip.compress(pickle.dumps(cache_data))
                        redis_client.setex(cache_key, 1800, compressed_data)  # 30 minutes
                        app.logger.info(f"Pre-cached establishment {establishment_id} cycle {cycle}")
                    except Exception as e:
                        app.logger.error(f"Failed to cache: {e}")
                        
            except Exception as e:
                app.logger.error(f"Error pre-caching establishment {establishment_id} cycle {cycle}: {e}")
                
        app.logger.info(f"Completed pre-cache for establishment {establishment_id}")
        
    except Exception as e:
        app.logger.error(f"Pre-cache failed for establishment {establishment_id}: {e}")

@app.route('/api/academy-trusts', methods=['GET'])
@cached(ttl_key='academy_trusts', ttl_seconds=3600)
def get_academy_trusts():
    """Get all Academy Trusts with their associated schools"""
    try:
        app.logger.info("Fetching Academy Trusts from object_2")
        
        # Fetch all VESPA Customers from object_2
        filters = [
            {
                'field': 'field_2209',
                'operator': 'is not',
                'value': 'Cancelled'
            }
        ]
        
        all_establishments = []
        page = 1
        
        while True:
            data = make_knack_request('object_2', filters=filters, page=page, rows_per_page=1000)
            records = data.get('records', [])
            
            if not records:
                break
                
            all_establishments.extend(records)
            
            if len(records) < 1000 or page > 5:  # Safety limit
                break
                
            page += 1
        
        app.logger.info(f"Processing {len(all_establishments)} establishments for Academy Trust grouping")
        
        # Group by Academy Trust (field_3480)
        trust_map = {}
        
        for record in all_establishments:
            est_id = record.get('id')
            est_name = record.get('field_44') or record.get('field_44_raw') or f"Customer {est_id}"
            
            # Get Academy Trust field (field_3480)
            trust_name = record.get('field_3480') or record.get('field_3480_raw')
            
            if trust_name and trust_name.strip():
                trust_name = trust_name.strip()
                
                if trust_name not in trust_map:
                    trust_map[trust_name] = {
                        'id': trust_name.lower().replace(' ', '-').replace('&', 'and'),
                        'name': trust_name,
                        'schools': []
                    }
                
                trust_map[trust_name]['schools'].append({
                    'id': est_id,
                    'name': est_name,
                    'status': record.get('field_2209') or 'Active'
                })
        
        # Convert to list and sort by name
        trusts = list(trust_map.values())
        trusts.sort(key=lambda x: x['name'].lower())
        
        # If no trusts found, create a sample trust for testing
        if not trusts and all_establishments:
            sample_trust = {
                'id': 'sample-academy-trust',
                'name': 'Sample Academy Trust',
                'schools': all_establishments[:3]  # First 3 schools for testing
            }
            trusts.append(sample_trust)
        
        app.logger.info(f"Found {len(trusts)} Academy Trusts")
        
        return jsonify({
            'trusts': trusts,
            'total': len(trusts)
        })
        
    except Exception as e:
        app.logger.error(f"Failed to fetch Academy Trusts: {e}")
        raise ApiError(f"Failed to fetch Academy Trusts: {str(e)}", 500)

@app.route('/api/dashboard-trust-data', methods=['POST'])
def get_dashboard_trust_data():
    """
    Fetch aggregated dashboard data for an Academy Trust.
    This searches across multiple schools in the trust.
    """
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")

    trust_name = data.get('trustName')
    trust_field_value = data.get('trustFieldValue')
    school_ids = data.get('schoolIds', [])
    cycle = data.get('cycle', 1)

    if not trust_name or not trust_field_value:
        raise ApiError("trustName and trustFieldValue must be provided")

    app.logger.info(f"Fetching trust data for: {trust_name} using value: {trust_field_value}")

    try:
        # Build filter to get all records for the given trust
        trust_filters = [{
            'field': 'field_3478',  # Academy Trust field in Object_10
            'operator': 'is',
            'value': trust_field_value
        }]
        
        # Add academic year filter (default to UK as trust could have mixed schools)
        academic_year_filter = get_academic_year_filters(None, 'field_855', 'field_3511')
        trust_filters.append(academic_year_filter)
        
        # Add filter for cycle completion
        cycle_completion_field = f'field_{155 + (cycle - 1) * 6}'
        trust_filters.append({
            'field': cycle_completion_field,
            'operator': 'is not blank'
        })
        app.logger.info(f"Added cycle {cycle} completion filter on field {cycle_completion_field}")

        app.logger.info(f"Using trust filter: {trust_filters}")

        # Define fields to fetch
        cycle_offset = (cycle - 1) * 6
        score_fields = [f'field_{154 + cycle_offset + i}_raw' for i in range(6)]
        
        vespa_fields = [
            'id',
            'field_133',        # VESPA Customer (establishment)
            'field_133_raw',
            'field_3478',       # Academy Trust field in Object_10
            'field_3478_raw',
            'field_439_raw',    # Staff Admin
            'field_187_raw',    # Student name
            'field_223',        # Group
            'field_223_raw',
            'field_2299',
            'field_2299_raw',
            'field_144_raw',
            'field_782_raw',
            'field_146',        # Current cycle
            'field_146_raw',    # Current cycle raw value
            *score_fields,
            'field_2302_raw',
            'field_2303_raw',
            'field_2304_raw',
            'field_2499_raw',
            'field_2493_raw',
            'field_2494_raw',
            'field_855',        # Completion date
            'field_855_raw',
            'field_3511_raw',   # Australian school indicator
        ]

        # Fetch all records for the trust
        vespa_data = make_knack_request('object_10', filters=trust_filters, fields=vespa_fields)
        vespa_records = vespa_data.get('records', [])
        
        app.logger.info(f"Found {len(vespa_records)} records for trust '{trust_name}'")

        if not vespa_records:
            return jsonify({
                'vespaResults': [],
                'nationalBenchmark': {},
                'filterOptions': {},
                'trustSchools': [],
                'trustName': trust_name,
                'schoolCount': 0,
                'totalRecords': 0,
                'cycle': cycle
            })

        # Build filter options from all trust data
        filter_sets = {
            'groups': set(),
            'courses': set(),
            'yearGroups': set(),
            'faculties': set(),
            'schools': set()  # To collect school IDs for filtering
        }

        for rec in vespa_records:
            grp = rec.get('field_223_raw') or rec.get('field_223')
            if grp:
                if isinstance(grp, list):
                    filter_sets['groups'].update([str(g) for g in grp if g])
                else:
                    filter_sets['groups'].add(str(grp))

            course = rec.get('field_2299_raw') or rec.get('field_2299')
            if course:
                if isinstance(course, list):
                    filter_sets['courses'].update([str(c) for c in course if c])
                else:
                    filter_sets['courses'].add(str(course))

            yg = rec.get('field_144_raw')
            if yg:
                filter_sets['yearGroups'].add(str(yg))

            fac = rec.get('field_782_raw')
            if fac:
                filter_sets['faculties'].add(str(fac))
                
            # Collect school IDs from the records
            school_conn = rec.get('field_133_raw')
            if school_conn and isinstance(school_conn, list) and len(school_conn) > 0:
                filter_sets['schools'].add(school_conn[0]['id'])

        # Get national benchmark
        national_data = make_knack_request(
            'object_120',
            filters=[],
            rows_per_page=1,
            sort_field='field_3307',
            sort_order='desc'
        )
        
        # Get school information for the trust filter
        school_info = []
        if filter_sets['schools']:
            school_filters = [{'match': 'or', 'rules': [{'field': 'id', 'operator': 'is', 'value': sid} for sid in filter_sets['schools']]}]
            school_records_data = make_knack_request('object_2', filters=school_filters, fields=['id', 'field_44'])
            school_records = school_records_data.get('records', [])
            school_info = [{'id': s['id'], 'name': s.get('field_44', 'Unknown School')} for s in school_records]

        results = {
            'vespaResults': vespa_records,
            'nationalBenchmark': national_data.get('records', [{}])[0],
            'filterOptions': {k: sorted(list(v)) for k, v in filter_sets.items() if k != 'schools'},
            'trustSchools': sorted(school_info, key=lambda x: x['name']),
            'trustName': trust_name,
            'schoolCount': len(filter_sets['schools']),
            'totalRecords': len(vespa_records),
            'cycle': cycle
        }
        
        return jsonify(results)

    except Exception as e:
        app.logger.error(f"Error fetching trust data: {e}", exc_info=True)
        raise ApiError(f"Failed to fetch trust dashboard data: {e}", 500)

@app.route('/api/establishments', methods=['GET'])
@cached(ttl_key='establishments')
def get_establishments():
    """Fetch VESPA Customer establishments from object_2"""
    try:
        app.logger.info("Fetching VESPA Customer establishments from object_2")
        
        # Check if we should trigger pre-caching
        should_precache = request.args.get('precache', 'false').lower() == 'true'
        
        # Fetch all VESPA Customers from object_2, excluding cancelled ones
        filters = [
            {
                'field': 'field_2209',
                'operator': 'is not',
                'value': 'Cancelled'
            }
        ]
        
        all_establishments = []
        page = 1
        
        while True:
            data = make_knack_request('object_2', filters=filters, page=page, rows_per_page=1000)
            records = data.get('records', [])
            
            if not records:
                break
                
            all_establishments.extend(records)
            
            # Since there are only ~200 records, we should get them all in one page
            if len(records) < 1000 or page > 5:  # Safety limit
                break
                
            page += 1
        
        app.logger.info(f"Found {len(all_establishments)} active VESPA Customers")
        
        # Format establishments using field_44 for the name
        establishments = []
        for record in all_establishments:
            est_id = record.get('id')
            # field_44 contains the VESPA Customer name
            est_name = record.get('field_44') or record.get('field_44_raw') or f"Customer {est_id}"
            
            # Also check if there's a formatted/display version
            if not est_name and record.get('identifier'):
                est_name = record.get('identifier')
            
            establishments.append({
                'id': est_id,
                'name': est_name,
                # Include additional useful fields if needed
                'status': record.get('field_2209') or 'Active'
            })
        
        # Sort by name
        establishments.sort(key=lambda x: x['name'].lower() if x['name'] else '')
        
        # If pre-caching requested, start background jobs for top establishments
        if should_precache and CACHE_ENABLED:
            # Pre-cache top 10 most likely establishments
            for est in establishments[:10]:
                Thread(target=precache_establishment_data, args=(est['id'], est['name'])).start()
        
        return jsonify({
            'establishments': establishments,
            'source_object': 'object_2',
            'total': len(establishments)
        })
        
    except Exception as e:
        app.logger.error(f"Failed to fetch establishments from object_2: {e}")
        raise ApiError(f"Failed to fetch establishments: {str(e)}", 500)

# --- Generate PDF Report Endpoint ---
@app.route('/api/generate-report', methods=['POST'])
def generate_pdf_report():
    """Generate a comprehensive PDF report with AI-generated insights"""
    try:
        data = request.get_json()
        if not data:
            raise ApiError("Missing request body")
        
        establishment_id = data.get('establishmentId')
        establishment_name = data.get('establishmentName', 'Unknown Establishment')
        staff_admin_id = data.get('staffAdminId')
        cycle = data.get('cycle', 1)
        vespa_scores = data.get('vespaScores', {})
        qla_insights = data.get('qlaInsights', [])
        filters = data.get('filters', {})
        
        app.logger.info(f"Generating PDF report for establishment: {establishment_name}, cycle: {cycle}")
        app.logger.info(f"Received VESPA scores: {vespa_scores}")
        app.logger.info(f"Received QLA insights count: {len(qla_insights)}")
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0f0f23'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#3b82f6'),
            spaceAfter=12,
            spaceBefore=20
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            textColor=colors.HexColor('#1a1a2e'),
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )
        
        # Title Page
        elements.append(Paragraph("VESPA Performance Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(f"<b>{establishment_name}</b>", styles['Heading3']))
        elements.append(Paragraph(f"Cycle {cycle} Analysis", styles['Normal']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(PageBreak())
        
        # Section 1: Executive Summary
        elements.append(Paragraph("1. Executive Summary", heading_style))
        
        # Generate AI summary if OpenAI is configured
        executive_summary = "This report provides a comprehensive analysis of student performance and engagement metrics."
        
        if OPENAI_API_KEY:
            try:
                import openai
                
                # Set the API key directly
                openai.api_key = OPENAI_API_KEY
                
                # Prepare context for AI
                context = f"""
                Establishment: {establishment_name}
                Cycle: {cycle}
                VESPA Scores: Vision={vespa_scores.get('vision', 'N/A')}, Effort={vespa_scores.get('effort', 'N/A')}, 
                Systems={vespa_scores.get('systems', 'N/A')}, Practice={vespa_scores.get('practice', 'N/A')}, 
                Attitude={vespa_scores.get('attitude', 'N/A')}, Overall={vespa_scores.get('overall', 'N/A')}
                
                Top performing areas based on QLA insights: {', '.join([i.get('title', '') for i in qla_insights[:3]])}
                """
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an educational data analyst creating executive summaries for school performance reports. Be concise, professional, and focus on actionable insights."},
                        {"role": "user", "content": f"Write a 2-3 paragraph executive summary for this school's performance report:\n{context}"}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                executive_summary = response.choices[0].message['content']
                
            except Exception as e:
                # Surface the OpenAI failure to the caller so the front-end knows something went wrong
                app.logger.error(f"Failed to generate AI summary: {e}")
                raise ApiError(f"OpenAI error while generating executive summary: {str(e)}", 500)
        
        elements.append(Paragraph(executive_summary, body_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Section 2: VESPA Scores Analysis
        elements.append(Paragraph("2. VESPA Performance Metrics", heading_style))
        
        # Helper function to format difference
        def format_difference(school_score, national_score):
            if school_score is None or national_score is None:
                return 'N/A'
            diff = school_score - national_score
            sign = '+' if diff > 0 else ''
            return f"{sign}{diff:.1f}"
        
        # Create VESPA scores table
        vespa_data = [
            ['Metric', 'School Score', 'National Average', 'Difference']
        ]
        
        # Add rows for each metric
        for metric in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
            school_score = vespa_scores.get(metric)
            national_score = vespa_scores.get(f'{metric}National')
            
            # Format scores for display
            school_display = f"{school_score:.1f}" if isinstance(school_score, (int, float)) else 'N/A'
            national_display = f"{national_score:.1f}" if isinstance(national_score, (int, float)) else 'N/A'
            
            # Calculate difference
            if isinstance(school_score, (int, float)) and isinstance(national_score, (int, float)):
                diff_display = format_difference(school_score, national_score)
            else:
                diff_display = 'N/A'
            
            vespa_data.append([
                metric.capitalize(),
                school_display,
                national_display,
                diff_display
            ])
        
        vespa_table = Table(vespa_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        vespa_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(vespa_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # AI Commentary on VESPA scores
        if OPENAI_API_KEY:
            try:
                vespa_analysis = "Based on the VESPA scores, the following observations can be made..."
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are analyzing VESPA educational metrics. Provide specific, actionable insights based on the scores."},
                        {"role": "user", "content": f"Analyze these VESPA scores and provide 2-3 key insights:\n{vespa_data}"}
                    ],
                    temperature=0.7,
                    max_tokens=250
                )
                
                vespa_analysis = response.choices[0].message['content']
                elements.append(Paragraph(vespa_analysis, body_style))
                
            except Exception as e:
                app.logger.error(f"Failed to generate VESPA analysis: {e}")
                raise ApiError(f"OpenAI error while generating VESPA analysis: {str(e)}", 500)
        
        elements.append(PageBreak())
        
        # Section 3: Question Level Analysis
        elements.append(Paragraph("3. Question Level Analysis - Key Insights", heading_style))
        
        if qla_insights:
            # Create insights table
            insights_data = [['Insight', 'Score', 'Status']]
            
            for insight in qla_insights[:8]:  # Top 8 insights
                status = 'Excellent' if insight.get('percentage', 0) >= 80 else 'Good' if insight.get('percentage', 0) >= 60 else 'Needs Attention'
                insights_data.append([
                    insight.get('title', 'Unknown'),
                    f"{insight.get('percentage', 0):.1f}%",
                    status
                ])
            
            insights_table = Table(insights_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            insights_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(insights_table)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Section 4: Intervention Strategies
        elements.append(Paragraph("4. Recommended Intervention Strategies", heading_style))
        
        # Generate AI recommendations
        if OPENAI_API_KEY and qla_insights:
            try:
                low_performing = [i for i in qla_insights if i.get('percentage', 100) < 60]
                
                context = f"Low performing areas: {', '.join([i.get('title', '') for i in low_performing[:3]])}"
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an educational consultant providing specific intervention strategies. Be practical and actionable."},
                        {"role": "user", "content": f"Suggest 3-4 specific intervention strategies for these areas:\n{context}"}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                interventions = response.choices[0].message['content']
                elements.append(Paragraph(interventions, body_style))
                
            except Exception as e:
                app.logger.error(f"Failed to generate interventions: {e}")
                raise ApiError(f"OpenAI error while generating intervention strategies: {str(e)}", 500)
        else:
            elements.append(Paragraph("Contact VESPA support for customized intervention strategies.", body_style))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Section 5: Conclusion
        elements.append(Paragraph("5. Conclusion and Next Steps", heading_style))
        
        conclusion = "This report highlights key areas of strength and opportunities for improvement. Regular monitoring and targeted interventions will help achieve better student outcomes."
        
        if OPENAI_API_KEY:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Write a brief, actionable conclusion for an educational performance report."},
                        {"role": "user", "content": f"Summarize key findings and suggest 2-3 next steps for {establishment_name}"}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                
                conclusion = response.choices[0].message['content']
                
            except Exception as e:
                app.logger.error(f"Failed to generate conclusion: {e}")
                raise ApiError(f"OpenAI error while generating conclusion: {str(e)}", 500)
        
        elements.append(Paragraph(conclusion, body_style))
        
        # Build PDF
        doc.build(elements)
        
        # Return PDF
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'VESPA_Report_{establishment_name.replace(" ", "_")}_Cycle{cycle}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Failed to generate PDF report: {e}")
        raise ApiError(f"Failed to generate report: {str(e)}", 500)

@app.route('/api/dashboard-data-optimized', methods=['POST'])
def get_dashboard_data_optimized():
    """
    Optimized endpoint for large datasets that uses Redis more efficiently.
    Stores data in chunks and allows progressive loading.
    """
    import time
    import hashlib
    
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    establishment_id = data.get('establishmentId')
    cycle = data.get('cycle', 1)
    chunk_size = data.get('chunkSize', 500)  # Smaller chunks for better caching
    chunk_index = data.get('chunkIndex', 0)  # Which chunk to return
    
    if not establishment_id:
        raise ApiError("establishmentId must be provided")
    
    # Create a stable cache key for the entire dataset
    dataset_key = f"dataset:{establishment_id}:{cycle}"
    metadata_key = f"metadata:{establishment_id}:{cycle}"
    chunk_key = f"{dataset_key}:chunk:{chunk_index}"
    
    # Try to get metadata from cache first
    metadata = None
    if CACHE_ENABLED:
        try:
            cached_metadata = redis_client.get(metadata_key)
            if cached_metadata:
                metadata = json.loads(cached_metadata)
                app.logger.info(f"Found cached metadata: {metadata}")
        except Exception as e:
            app.logger.error(f"Error reading metadata from cache: {e}")
    
    # If no metadata, we need to fetch initial data to understand the dataset
    if not metadata:
        app.logger.info(f"No metadata found, fetching dataset info for establishment {establishment_id}")
        
        # Build filters
        base_filters = [{
            'field': 'field_133',
            'operator': 'is',
            'value': establishment_id
        }]
        
        # Get dataset size with minimal fields
        size_check = make_knack_request(
            'object_10',
            filters=base_filters,
            page=1,
            rows_per_page=1,
            fields=['id']
        )
        
        total_records = size_check.get('total_records', 0)
        total_pages = size_check.get('total_pages', 1)
        total_chunks = (total_records + chunk_size - 1) // chunk_size
        
        metadata = {
            'total_records': total_records,
            'total_pages': total_pages,
            'total_chunks': total_chunks,
            'chunk_size': chunk_size,
            'created_at': time.time()
        }
        
        # Cache metadata for 30 minutes
        if CACHE_ENABLED:
            try:
                redis_client.setex(metadata_key, 1800, json.dumps(metadata))
            except Exception as e:
                app.logger.error(f"Error caching metadata: {e}")
    
    # Check if requested chunk is in cache
    chunk_data = None
    if CACHE_ENABLED:
        try:
            cached_chunk = redis_client.get(chunk_key)
            if cached_chunk:
                chunk_data = pickle.loads(gzip.decompress(cached_chunk))
                app.logger.info(f"Returning cached chunk {chunk_index}")
                return jsonify({
                    'chunk': chunk_data,
                    'metadata': metadata,
                    'cached': True
                })
        except Exception as e:
            app.logger.error(f"Error reading chunk from cache: {e}")
    
    # If not in cache, fetch the specific chunk
    app.logger.info(f"Fetching chunk {chunk_index} (records {chunk_index * chunk_size} to {(chunk_index + 1) * chunk_size})")
    
    # Calculate which Knack page contains this chunk
    records_per_knack_page = 1000
    start_record = chunk_index * chunk_size
    knack_page = (start_record // records_per_knack_page) + 1
    offset_in_page = start_record % records_per_knack_page
    
    # Define fields to fetch
    cycle_offset = (cycle - 1) * 6
    score_fields = [f'field_{154 + cycle_offset + i}_raw' for i in range(6)]
    
    vespa_fields = [
        'id',
        'field_133_raw',
        'field_187_raw',
        'field_223_raw',
        'field_2299_raw',
        'field_144_raw',
        'field_782_raw',
        *score_fields
    ]
    
    # Build filters
    base_filters = [{
        'field': 'field_133',
        'operator': 'is',
        'value': establishment_id
    }]
    
    try:
        # Fetch the page(s) needed for this chunk
        chunk_records = []
        records_needed = chunk_size
        current_page = knack_page
        
        while records_needed > 0 and current_page <= metadata['total_pages']:
            page_data = make_knack_request(
                'object_10',
                filters=base_filters,
                page=current_page,
                rows_per_page=records_per_knack_page,
                fields=vespa_fields
            )
            
            page_records = page_data.get('records', [])
            
            if current_page == knack_page:
                # First page - skip to offset
                page_records = page_records[offset_in_page:]
            
            # Take only what we need
            records_to_take = min(records_needed, len(page_records))
            chunk_records.extend(page_records[:records_to_take])
            records_needed -= records_to_take
            
            if records_to_take < len(page_records):
                break  # We have enough
                
            current_page += 1
        
        # Cache this chunk for 30 minutes
        if CACHE_ENABLED and chunk_records:
            try:
                compressed_chunk = gzip.compress(pickle.dumps(chunk_records))
                redis_client.setex(chunk_key, 1800, compressed_chunk)
                app.logger.info(f"Cached chunk {chunk_index} ({len(chunk_records)} records, {len(compressed_chunk)} bytes)")
            except Exception as e:
                app.logger.error(f"Error caching chunk: {e}")
        
        return jsonify({
            'chunk': chunk_records,
            'metadata': metadata,
            'cached': False
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching chunk: {e}")
        raise ApiError(f"Failed to fetch data chunk: {str(e)}", 500)

@app.route('/api/cache/prewarm', methods=['POST'])
def prewarm_cache():
    """
    Pre-warm cache for an establishment to improve subsequent load times.
    This can be called after selecting an establishment but before loading the dashboard.
    """
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    establishment_id = data.get('establishmentId')
    cycles = data.get('cycles', [1, 2, 3])  # Pre-warm all cycles by default
    
    if not establishment_id:
        raise ApiError("establishmentId must be provided")
    
    if not CACHE_ENABLED:
        return jsonify({'message': 'Cache not enabled', 'success': False})
    
    try:
        warmed_keys = []
        
        for cycle in cycles:
            # Get metadata first
            metadata_key = f"metadata:{establishment_id}:{cycle}"
            dataset_key = f"dataset:{establishment_id}:{cycle}"
            
            # Check dataset size
            base_filters = [{
                'field': 'field_133',
                'operator': 'is',
                'value': establishment_id
            }]
            
            size_check = make_knack_request(
                'object_10',
                filters=base_filters,
                page=1,
                rows_per_page=1,
                fields=['id']
            )
            
            total_records = size_check.get('total_records', 0)
            
            # Only pre-warm first few chunks for large datasets
            chunk_size = 500
            chunks_to_warm = min(6, (total_records + chunk_size - 1) // chunk_size)  # Max 6 chunks (3000 records)
            
            app.logger.info(f"Pre-warming {chunks_to_warm} chunks for establishment {establishment_id}, cycle {cycle}")
            
            # Store metadata
            metadata = {
                'total_records': total_records,
                'total_pages': size_check.get('total_pages', 1),
                'total_chunks': (total_records + chunk_size - 1) // chunk_size,
                'chunk_size': chunk_size,
                'created_at': time.time()
            }
            redis_client.setex(metadata_key, 1800, json.dumps(metadata))
            warmed_keys.append(metadata_key)
            
            # Pre-fetch first few chunks
            for chunk_index in range(chunks_to_warm):
                # Use the optimized endpoint internally
                with current_app.test_request_context(json={
                    'establishmentId': establishment_id,
                    'cycle': cycle,
                    'chunkSize': chunk_size,
                    'chunkIndex': chunk_index
                }):
                    response = get_dashboard_data_optimized()
                    if response.status_code == 200:
                        warmed_keys.append(f"{dataset_key}:chunk:{chunk_index}")
        
        return jsonify({
            'success': True,
            'warmed_keys': len(warmed_keys),
            'message': f'Pre-warmed cache for establishment {establishment_id}'
        })
        
    except Exception as e:
        app.logger.error(f"Error pre-warming cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to pre-warm cache'
        })

@app.route('/api/debug/recent-logs', methods=['GET'])
def get_recent_logs():
    """
    Get recent application logs for debugging purposes.
    This is a temporary endpoint to help diagnose issues when Heroku logs are not accessible.
    """
    try:
        # Check if authorized (you should add proper authentication here)
        auth_token = request.headers.get('Authorization')
        if auth_token != os.getenv('DEBUG_AUTH_TOKEN', 'debug-token-2025'):
            raise ApiError("Unauthorized", 401)
        
        # In a real implementation, you would store logs in Redis or a database
        # For now, return a message about how to access logs
        return jsonify({
            'message': 'To view Heroku logs, use the following commands:',
            'commands': [
                'heroku logs --tail -a vespa-dashboard-9a1f84ee5341',
                'heroku logs -n 1500 -a vespa-dashboard-9a1f84ee5341 | grep -i "qla"',
                'heroku logs -n 1500 -a vespa-dashboard-9a1f84ee5341 | grep -i "ashlyns"'
            ],
            'note': 'Heroku only retains the last 1,500 lines. For persistent logging, configure a log drain service.',
            'recommendation': 'Set up Papertrail or similar service for log retention'
        })
    except Exception as e:
        app.logger.error(f"Debug logs endpoint error: {e}")
        raise ApiError(f"Failed to retrieve logs: {str(e)}", 500)

@app.route('/api/data-health-check', methods=['POST'])
@cached(ttl_key='data_health', ttl_seconds=60)  # Cache for 1 minute (reduced for faster updates)
def check_data_health():
    """
    Compare Object_10 (VESPA scores) and Object_29 (Psychometric responses) to identify data discrepancies.
    Returns health status (green/amber/red) and detailed mismatch information.
    """
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    establishment_id = data.get('establishmentId')
    staff_admin_id = data.get('staffAdminId')
    cycle = data.get('cycle', 1)
    trust_field_value = data.get('trustFieldValue')
    
    # Must have at least one identifier
    if not establishment_id and not staff_admin_id and not trust_field_value:
        raise ApiError("Either establishmentId, staffAdminId, or trustFieldValue must be provided")
    
    try:
        # Build filters for Object_10 (VESPA Results)
        vespa_filters = []
        if establishment_id:
            vespa_filters.append({
                'field': 'field_133',
                'operator': 'is',
                'value': establishment_id
            })
        elif staff_admin_id:
            vespa_filters.append({
                'field': 'field_439',
                'operator': 'is',
                'value': staff_admin_id
            })
        elif trust_field_value:
            # For trust, we need to get all establishments in the trust first
            est_filters = [{
                'field': 'field_3480',  # Academy Trust field in Object_2
                'operator': 'is',
                'value': trust_field_value
            }]
            trust_establishments = make_knack_request('object_2', filters=est_filters, fields=['id'])
            trust_est_ids = [e['id'] for e in trust_establishments.get('records', [])]
            
            if trust_est_ids:
                vespa_filters.append({
                    'field': 'field_133',
                    'operator': 'is one of',
                    'value': trust_est_ids
                })
        
        # Add academic year filters
        academic_year_filter = get_academic_year_filters(establishment_id)
        if academic_year_filter:
            vespa_filters.append(academic_year_filter)
        
        # Build filters for Object_29 (Psychometric responses)
        psycho_filters = []
        if establishment_id:
            psycho_filters.append({
                'field': 'field_1821',  # Establishment connection in Object_29
                'operator': 'is',
                'value': establishment_id
            })
        elif staff_admin_id:
            # For staff admin, we need to find their establishment first
            staff_record = make_knack_request(
                'object_5',
                filters=[{'field': 'id', 'operator': 'is', 'value': staff_admin_id}],
                fields=['field_35_raw']  # Establishment connection
            )
            if staff_record['records']:
                est_id = staff_record['records'][0].get('field_35_raw', [{}])[0].get('id')
                if est_id:
                    psycho_filters.append({
                        'field': 'field_1821',
                        'operator': 'is',
                        'value': est_id
                    })
        elif trust_field_value and trust_est_ids:
            psycho_filters.append({
                'field': 'field_1821',
                'operator': 'is one of',
                'value': trust_est_ids
            })
        
        # Add academic year filters for Object_29
        psycho_academic_filter = get_academic_year_filters(establishment_id, 'field_856', 'field_3508')
        if psycho_academic_filter:
            psycho_filters.append(psycho_academic_filter)
        
        # Add cycle filter for Object_29
        cycle_field_map = {
            1: 'field_1953',  # Cycle 1 response field
            2: 'field_1955',  # Cycle 2 response field
            3: 'field_1956'   # Cycle 3 response field
        }
        
        if cycle in cycle_field_map:
            psycho_filters.append({
                'field': cycle_field_map[cycle],
                'operator': 'is not blank'
            })
        
        # Fetch all records from both objects with pagination
        app.logger.info(f"Fetching VESPA records with filters: {vespa_filters}")
        
        # Determine which score fields to check based on cycle
        cycle_offset = (int(cycle) - 1) * 6
        score_fields = [f'field_{154 + cycle_offset + i}' for i in range(6)]  # Score fields for this cycle
        
        # Include score fields in the fetch to check if they have values
        vespa_fields = ['id', 'field_187_raw', 'field_133_raw'] + [f + '_raw' for f in score_fields]
        
        # Fetch all VESPA records with pagination
        all_vespa_records = []
        page = 1
        max_pages = 10  # Safety limit
        
        while page <= max_pages:
            vespa_response = make_knack_request(
                'object_10',
                filters=vespa_filters,
                page=page,
                rows_per_page=1000,
                fields=vespa_fields
            )
            
            records = vespa_response.get('records', [])
            if not records:
                break
                
            all_vespa_records.extend(records)
            app.logger.info(f"Fetched page {page} of VESPA records: {len(records)} records (total so far: {len(all_vespa_records)})")
            
            if len(records) < 1000:  # Last page
                break
                
            page += 1
        
        # Filter to only include records that have at least one score for this cycle
        vespa_records = []
        for record in all_vespa_records:
            has_score = False
            for field in score_fields:
                if record.get(f'{field}_raw'):
                    has_score = True
                    break
            if has_score:
                vespa_records.append(record)
        
        app.logger.info(f"Total VESPA records fetched: {len(all_vespa_records)}, with Cycle {cycle} scores: {len(vespa_records)}")
        
        # Fetch all Psychometric records with pagination
        app.logger.info(f"Fetching Psychometric records with filters: {psycho_filters}")
        
        psycho_records = []
        page = 1
        
        while page <= max_pages:
            psycho_response = make_knack_request(
                'object_29',
                filters=psycho_filters,
                page=page,
                rows_per_page=1000,
                fields=['id', 'field_1819_raw', 'field_1821_raw']  # ID, Student connection, Establishment
            )
            
            records = psycho_response.get('records', [])
            if not records:
                break
                
            psycho_records.extend(records)
            app.logger.info(f"Fetched page {page} of Psychometric records: {len(records)} records (total so far: {len(psycho_records)})")
            
            if len(records) < 1000:  # Last page
                break
                
            page += 1
        
        app.logger.info(f"Total Psychometric records fetched: {len(psycho_records)}")
        
        # Create maps for comparison
        # For Object_10: map by student name
        vespa_students = {}
        for record in vespa_records:
            student_name = record.get('field_187_raw', {})
            if student_name:
                full_name = f"{student_name.get('first', '')} {student_name.get('last', '')}".strip()
                if full_name:
                    vespa_students[full_name.lower()] = {
                        'id': record['id'],
                        'name': full_name,
                        'establishment': record.get('field_133_raw', [{}])[0].get('identifier', 'Unknown')
                    }
        
        # For Object_29: map by student connection
        psycho_students = {}
        for record in psycho_records:
            student_conn = record.get('field_1819_raw', [])
            if student_conn and len(student_conn) > 0:
                student_name = student_conn[0].get('identifier', '').strip()
                if student_name:
                    psycho_students[student_name.lower()] = {
                        'id': record['id'],
                        'name': student_name,
                        'student_id': student_conn[0].get('id'),
                        'establishment': record.get('field_1821_raw', [{}])[0].get('identifier', 'Unknown')
                    }
        
        # Find discrepancies
        vespa_names = set(vespa_students.keys())
        psycho_names = set(psycho_students.keys())
        
        # Students with VESPA scores but no questionnaire
        missing_questionnaires = []
        for name in (vespa_names - psycho_names):
            student = vespa_students[name]
            missing_questionnaires.append({
                'student_id': student['id'],
                'student_name': student['name'],
                'has_vespa_score': True,
                'has_questionnaire': False,
                'establishment': student['establishment']
            })
        
        # Students with questionnaire but no VESPA scores
        missing_scores = []
        for name in (psycho_names - vespa_names):
            student = psycho_students[name]
            missing_scores.append({
                'student_id': student['student_id'],
                'student_name': student['name'],
                'has_vespa_score': False,
                'has_questionnaire': True,
                'questionnaire_id': student['id'],
                'establishment': student['establishment']
            })
        
        # Calculate health status
        total_students = len(vespa_students)
        total_issues = len(missing_questionnaires) + len(missing_scores)
        
        if total_students == 0:
            status = 'gray'  # No data
            discrepancy_rate = 0
        else:
            discrepancy_rate = (total_issues / total_students) * 100
            
            if discrepancy_rate == 0:
                status = 'green'
            elif discrepancy_rate <= 5:
                status = 'amber'
            else:
                status = 'red'
        
        # Build response
        response_data = {
            'status': status,
            'summary': {
                'object10_count': len(vespa_students),
                'object29_count': len(psycho_students),
                'matched_count': len(vespa_names & psycho_names),
                'discrepancy_rate': round(discrepancy_rate, 1)
            },
            'issues': {
                'missing_questionnaires': missing_questionnaires[:50],  # Limit to first 50
                'missing_scores': missing_scores[:50],  # Limit to first 50
                'total_missing_questionnaires': len(missing_questionnaires),
                'total_missing_scores': len(missing_scores)
            },
            'recommendations': []
        }
        
        # Add recommendations based on findings
        if len(missing_questionnaires) > 0:
            response_data['recommendations'].append(
                f"{len(missing_questionnaires)} students need to complete psychometric questionnaires"
            )
        
        if len(missing_scores) > 0:
            response_data['recommendations'].append(
                f"{len(missing_scores)} students have questionnaire data but no VESPA scores recorded"
            )
        
        if discrepancy_rate > 10:
            response_data['recommendations'].append(
                "High discrepancy rate - urgent data reconciliation needed"
            )
        elif discrepancy_rate > 5:
            response_data['recommendations'].append(
                "Moderate discrepancy rate - review data entry processes"
            )
        
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"Data health check error: {e}")
        raise ApiError(f"Failed to check data health: {str(e)}", 500)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv('PORT', 5001)) # Use port 5001 for local dev if 5000 is common 