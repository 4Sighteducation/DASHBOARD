import os
import json
import traceback
import requests
from datetime import datetime, timedelta
from types import SimpleNamespace
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
from reportlab.platypus import HRFlowable
from io import BytesIO
import base64
from supabase import create_client, Client
import numpy as np

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

# Academic year normalization for global benchmarks
def normalize_academic_year_for_benchmark(academic_year):
    """Normalize academic year for benchmark comparisons
    
    Australian schools: 2025/2025 -> 2025/2026 (treated as same period as UK)
    UK schools: 2025/2026 -> 2025/2026 (unchanged)
    
    This allows all schools to be compared in the same benchmark period.
    """
    if not academic_year or '/' not in academic_year:
        return academic_year
    
    parts = academic_year.split('/')
    if len(parts) != 2:
        return academic_year
    
    # If it's Australian format (same year repeated), convert to UK format
    if parts[0] == parts[1]:
        year = int(parts[0])
        return f"{year}/{year + 1}"
    
    return academic_year

# Cache TTL settings (in seconds)
CACHE_TTL = {
    'vespa_results': 300,  # 5 minutes for VESPA results
    'national_data': 3600,  # 1 hour for global benchmarks (was national)
    'filter_options': 600,  # 10 minutes for filter options
    'establishments': 3600,  # 1 hour for establishments
    'question_mappings': 86400,  # 24 hours for static mappings
    'dashboard_data': 600,  # 10 minutes for dashboard batch data
}

# --- Supabase Setup ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase_client = None
SUPABASE_ENABLED = False

if SUPABASE_URL and SUPABASE_KEY:
    try:
        # Create client with basic options only - avoid proxy issues on Heroku
        import os
        # Clear any proxy settings that might interfere
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
        
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        SUPABASE_ENABLED = True
        app.logger.info(f"Supabase client initialized for {SUPABASE_URL}")
    except Exception as e:
        supabase_client = None
        SUPABASE_ENABLED = False
        app.logger.warning(f"Supabase client initialization failed: {str(e)}")
else:
    app.logger.warning("Supabase credentials not found in environment variables")

# --- Explicit CORS Configuration ---
# Allow requests from your specific Knack domain and potentially localhost for development
# Updated CORS configuration with explicit settings
CORS(app, 
     resources={r"/api/*": {"origins": ["https://vespaacademy.knack.com", "http://localhost:8000", "http://127.0.0.1:8000", "null"]}},
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'X-Knack-Application-Id', 'X-Knack-REST-API-Key', 'x-knack-application-id', 'x-knack-rest-api-key'],
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
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-Knack-Application-Id, X-Knack-REST-API-Key, x-knack-application-id, x-knack-rest-api-key'
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

# --- ID Conversion Helper ---
def convert_knack_id_to_uuid(establishment_id):
    """Convert Knack ID to Supabase UUID if needed"""
    if not establishment_id:
        return None
        
    # Check if it's already a valid UUID format
    import uuid
    try:
        uuid.UUID(establishment_id)
        # It's already a UUID, use as is
        return establishment_id
    except ValueError:
        # It's a Knack ID, need to convert
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
            
        est_result = supabase_client.table('establishments').select('id').eq('knack_id', establishment_id).execute()
        if not est_result.data:
            raise ApiError(f"Establishment not found with ID: {establishment_id}", 404)
        return est_result.data[0]['id']

# --- Academic Year Helper ---
def get_current_academic_year():
    """Get the current academic year string (e.g., '2024/2025')"""
    today = datetime.now()
    # August to December: Current year / Next year (e.g., 2024/2025)
    if today.month >= 8:
        return f"{today.year}/{today.year + 1}"
    # January to July: Previous year / Current year (e.g., 2023/2024)
    else:
        return f"{today.year - 1}/{today.year}"

def convert_academic_year_format(year_str, to_database=True):
    """
    Convert academic year between frontend format (2025-26) and database format (2025/2026)
    
    Args:
        year_str: The academic year string to convert
        to_database: If True, convert from frontend to database format. If False, convert from database to frontend.
    
    Returns:
        Converted academic year string, or original if no conversion needed
    """
    if not year_str or year_str == 'all':
        return year_str
    
    if to_database:
        # Convert from 2025-26 to 2025/2026
        if '-' in year_str:
            parts = year_str.split('-')
            if len(parts) == 2:
                start_year = parts[0]
                short_end = parts[1]
                # Reconstruct full end year
                if len(short_end) == 2:
                    end_year = start_year[:2] + short_end
                else:
                    end_year = short_end
                return f"{start_year}/{end_year}"
    else:
        # Convert from 2025/2026 to 2025-26
        if '/' in year_str:
            parts = year_str.split('/')
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1][-2:]}"
    
    return year_str

def strip_html_tags(text):
    """
    Remove HTML tags from text while preserving the content.
    Handles both simple tags like <p> and self-closing tags.
    
    Args:
        text: String that may contain HTML tags
    
    Returns:
        String with HTML tags removed
    """
    if not text or not isinstance(text, str):
        return text
    
    import re
    # Remove HTML tags but keep the content
    # Pattern matches: <tag>, </tag>, <tag/>, <tag attr="value">
    clean_text = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    clean_text = ' '.join(clean_text.split())
    return clean_text.strip()

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
            is_australian = est_data.get(f'{australian_field}_raw', '')
            # For field_3573, only exactly "True" counts
            if australian_field == 'field_3573':
                is_australian_school = (is_australian == 'True')
            else:
                # For backward compatibility with other fields
                is_australian_school = (is_australian == 'true' or is_australian == True or is_australian == 'True')
            
            if is_australian_school:
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
    force_refresh = data.get('forceRefresh', False)  # Allow cache bypass
    
    if not staff_admin_id and not establishment_id:
        raise ApiError("Either staffAdminId or establishmentId must be provided")
    
    # Generate cache key for this specific request
    cache_key = f"dashboard_data:{staff_admin_id or 'none'}:{establishment_id or 'none'}:{cycle}:{page}:{rows_per_page}"
    
    # Try to get from cache first (unless force refresh is requested)
    if CACHE_ENABLED and not force_refresh:
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
        
        # Add filter for cycle completion - check if Vision score exists for the cycle
        # Cycle 1: field_155 (V1), Cycle 2: field_161 (V2), Cycle 3: field_167 (V3)
        cycle_vision_fields = {
            1: 'field_155',  # Vision Cycle 1
            2: 'field_161',  # Vision Cycle 2
            3: 'field_167'   # Vision Cycle 3
        }
        
        if cycle in cycle_vision_fields:
            cycle_filter_field = cycle_vision_fields[cycle]
            base_filters.append({
                'field': cycle_filter_field,
                'operator': 'is not blank'
            })
            app.logger.info(f"Added cycle {cycle} filter: checking if {cycle_filter_field} (Vision score) exists")
    elif staff_admin_id:
        base_filters.append({
            'field': 'field_439',
            'operator': 'is',
            'value': staff_admin_id
        })
        # For staff admin, we default to UK academic year (can't determine if Australian without specific establishment)
        academic_year_filter = get_academic_year_filters(None, 'field_855', 'field_3511')
        base_filters.append(academic_year_filter)
        
        # Add filter for cycle completion - check if Vision score exists for the cycle
        # Cycle 1: field_155 (V1), Cycle 2: field_161 (V2), Cycle 3: field_167 (V3)
        cycle_vision_fields = {
            1: 'field_155',  # Vision Cycle 1
            2: 'field_161',  # Vision Cycle 2
            3: 'field_167'   # Vision Cycle 3
        }
        
        if cycle in cycle_vision_fields:
            cycle_filter_field = cycle_vision_fields[cycle]
            base_filters.append({
                'field': cycle_filter_field,
                'operator': 'is not blank'
            })
            app.logger.info(f"Added cycle {cycle} filter: checking if {cycle_filter_field} (Vision score) exists")
    
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
                # Determine academic year (using current year as we're fetching current data)
                current_academic_year = get_current_academic_year()
                # Convert to Object_120 format (2024-2025 instead of 2024/2025)
                object120_year = current_academic_year.replace('/', '-')
                
                national_future = executor.submit(
                    make_knack_request,
                    'object_120',
                    filters=[{
                        'field': 'field_3308',  # Academic Year field in Object_120
                        'operator': 'is',
                        'value': object120_year
                    }],
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
                # Determine academic year (using current year as we're fetching current data)
                current_academic_year = get_current_academic_year()
                # Convert to Object_120 format (2024-2025 instead of 2024/2025)
                object120_year = current_academic_year.replace('/', '-')
                
                national_data = make_knack_request(
                    'object_120',
                    filters=[{
                        'field': 'field_3308',  # Academic Year field in Object_120
                        'operator': 'is',
                        'value': object120_year
                    }],
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
        
        # Add filter for cycle completion - check if Vision score exists for the cycle
        # Cycle 1: field_155 (V1), Cycle 2: field_161 (V2), Cycle 3: field_167 (V3)
        cycle_vision_fields = {
            1: 'field_155',  # Vision Cycle 1
            2: 'field_161',  # Vision Cycle 2
            3: 'field_167'   # Vision Cycle 3
        }
        
        if cycle in cycle_vision_fields:
            cycle_filter_field = cycle_vision_fields[cycle]
            base_filters.append({
                'field': cycle_filter_field,
                'operator': 'is not blank'
            })
            app.logger.info(f"Added cycle {cycle} filter: checking if {cycle_filter_field} (Vision score) exists")
        
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

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Get all questions from the database with optional filtering"""
    try:
        # Get query parameters
        vespa_category = request.args.get('category')
        is_active = request.args.get('active', 'true').lower() == 'true'
        
        # Build query
        query = supabase_client.table('questions').select('*')
        
        if vespa_category:
            query = query.eq('vespa_category', vespa_category)
        
        if is_active:
            query = query.eq('is_active', True)
            
        # Order by question_order
        query = query.order('question_order')
        
        result = query.execute()
        
        return jsonify({
            'questions': result.data,
            'count': len(result.data)
        })
    except Exception as e:
        app.logger.error(f"Error fetching questions: {str(e)}")
        return jsonify({'error': 'Failed to fetch questions'}), 500

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
            # Also map the exact format used by frontend: OUTCOME_Q_CONFIDENT
            if '_q_' in qid:
                uppercase_with_underscore = qid.upper()
                id_map[uppercase_with_underscore] = field_id
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


def map_object10_to_object29_filters(filters):
    """
    Map Object_10 filters to their Object_29 equivalents.
    Some fields exist directly in Object_29, others need special handling.
    """
    # Direct field mappings from Object_10 to Object_29
    direct_mapping = {
        'field_144': 'field_1826',   # Year Group
        'field_223': 'field_1824',   # Groups
        'field_187': 'field_1823'    # Student Name
    }
    
    # Fields that don't exist in Object_29
    unsupported_fields = {
        'field_2299': 'Course',
        'field_782': 'Faculty'
    }
    
    mapped_filters = []
    unsupported_filter_names = []
    
    for filter_item in filters:
        field = filter_item.get('field')
        
        if field in direct_mapping:
            # Direct mapping exists - use Object_29 field
            mapped_filter = filter_item.copy()
            mapped_filter['field'] = direct_mapping[field]
            mapped_filters.append(mapped_filter)
            app.logger.info(f"Mapped Object_10 field {field} to Object_29 field {direct_mapping[field]}")
        elif field in unsupported_fields:
            # Track unsupported filters for warning message
            unsupported_filter_names.append(unsupported_fields[field])
            app.logger.warning(f"Filter '{unsupported_fields[field]}' (field {field}) is not supported in QLA")
            # Don't add to mapped_filters - these will be ignored
        else:
            # Unknown field, pass through as-is (might be a valid Object_29 field)
            mapped_filters.append(filter_item)
    
    # Return filters and any warning message
    result = {
        'filters': mapped_filters,
        'warnings': []
    }
    
    if unsupported_filter_names:
        warning_msg = f"{', '.join(unsupported_filter_names)} filters cannot be applied at Question Level Analysis"
        result['warnings'].append(warning_msg)
        app.logger.warning(f"QLA Analysis: {warning_msg}")
    
    return result


def _fetch_psychometric_records(question_field_ids, base_filters, cycle=None):
    """Fetch records from object_29 containing the requested fields."""
    # Build field list with _raw so we get numeric value directly
    fields = []
    for fid in question_field_ids:
        fields.append(fid)
        fields.append(fid + '_raw')
    
    # Add cycle filter if specified
    filters = base_filters.copy()
    
    # Check cycle-specific fields that are actually populated
    cycle_field_map = {
        1: 'field_1953',  # Cycle 1 data field
        2: 'field_1955',  # Cycle 2 data field (note: was incorrectly documented as field_1954)
        3: 'field_1956'   # Cycle 3 data field
    }
    
    if cycle and cycle in cycle_field_map:
        # Filter by checking if the cycle-specific field is not blank
        filters.append({
            'field': cycle_field_map[cycle],
            'operator': 'is not blank'
        })
        # Also add the field to fetch list to verify
        fields.append(cycle_field_map[cycle])
        fields.append(cycle_field_map[cycle] + '_raw')
        app.logger.info(f"Added cycle filter for cycle {cycle} using field {cycle_field_map[cycle]}")
    
    # Always include the current cycle field to see what's stored
    fields.append('field_863')
    fields.append('field_863_raw')
    
    # Always include student ID field for reconciliation
    fields.append('field_1819')  # Student connection field in object_29
    fields.append('field_1819_raw')
    
    # Add completion date field for academic year filtering
    fields.append('field_856')  # Completion date
    fields.append('field_856_raw')
    
    # First, determine if this is an Australian school
    # We need to check the establishment record to see if field_3573 is True
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
                est_data = make_knack_request('object_2', record_id=establishment_id, fields=['field_3573', 'field_3573_raw'])
                is_australian = est_data.get('field_3573_raw', '')
                if is_australian == 'True':  # Only exactly "True" counts
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
                app.logger.info(f"Mapped question {qid} (variant: {variant}) to field {f_id}")
                break
        
        if not f_id:
            app.logger.warning(f"No mapping found for question {qid} in cycle {cycle}")
            continue
            
        col_vals = []
        for rec in records:
            val = rec.get(f_id + '_raw')
            try:
                # Treat zeros as null/missing values
                if val is not None:
                    # Handle string "0" as well as numeric 0
                    if str(val) == "0" or val == 0:
                        col_vals.append(None)
                    else:
                        float_val = float(val)
                        # If the value is 0, treat it as null (don't include in calculations)
                        col_vals.append(None if float_val == 0 else float_val)
                else:
                    col_vals.append(None)
            except ValueError:
                col_vals.append(None)
        data_dict[qid] = col_vals
    
    df = pd.DataFrame(data_dict)
    app.logger.info(f"_build_dataframe: Created DataFrame with shape {df.shape}")
    
    # Log information about null values (including zeros treated as nulls)
    null_counts = df.isnull().sum()
    if not null_counts.empty:
        app.logger.info(f"_build_dataframe: Null counts per question (includes zeros): {null_counts.to_dict()}")
    
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
    app.logger.info(f"quick_percent_agree called with questions: {question_ids}, cycle: {cycle}")
    df = _build_dataframe(question_ids, filters, cycle)
    if df.empty:
        app.logger.warning(f"DataFrame is empty for questions: {question_ids}")
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
                    app.logger.info(f"Question {q}: {n} responses, {agree_count} agree")
                else:
                    app.logger.warning(f"Question {q}: No valid responses after dropna")
            else:
                app.logger.warning(f"Question {q} not found in dataframe columns: {list(df.columns)}")
        
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
                # Map Object_10 filters to Object_29 filters
                mapping_result = map_object10_to_object29_filters(filters_param['additionalFilters'])
                base_filters.extend(mapping_result['filters'])

        if analysis_type in calc_dispatch:
            result = calc_dispatch[analysis_type](question_ids, base_filters, cycle)
            # Add any filter warnings to the result
            if 'additionalFilters' in filters_param and filters_param['additionalFilters']:
                if mapping_result.get('warnings'):
                    if 'warnings' not in result:
                        result['warnings'] = []
                    result['warnings'].extend(mapping_result['warnings'])
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
            filter_warnings = []
            if 'additionalFilters' in filters_param and filters_param['additionalFilters']:
                # Map Object_10 filters to Object_29 filters
                mapping_result = map_object10_to_object29_filters(filters_param['additionalFilters'])
                base_filters.extend(mapping_result['filters'])
                filter_warnings = mapping_result.get('warnings', [])
        
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
        
        # Add filter warnings if any
        if filter_warnings:
            results['_warnings'] = filter_warnings
        
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
        cycle = filters.get('cycle')
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

# --- Supabase Comment Analysis Endpoints ---
@app.route('/api/comments/word-cloud', methods=['GET'])
def get_comments_word_cloud():
    """Generate word cloud data from student comments in Supabase"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Get filters from query params - BE CAREFUL WITH FIELD NAMES!
        establishment_id = request.args.get('establishment_id')
        cycle = request.args.get('cycle', type=int)
        academic_year = request.args.get('academic_year')
        # Convert academic year from frontend format (2025-26) to database format (2025/2026)
        if academic_year:
            academic_year = convert_academic_year_format(academic_year, to_database=True)
        year_group = request.args.get('year_group')
        group = request.args.get('group')
        faculty = request.args.get('faculty')
        student_id = request.args.get('student_id')  # NOT student_ID!
        
        app.logger.info(f"Word cloud request - establishment: {establishment_id}, cycle: {cycle}, academic_year: {academic_year}")
        
        # Convert establishment_id if it's a Knack ID
        if establishment_id:
            establishment_id = convert_knack_id_to_uuid(establishment_id)
        
        # Convert student_id if provided
        if student_id:
            student_id = convert_knack_id_to_uuid(student_id)
        
        # If no academic year specified, use current
        if not academic_year:
            academic_year = get_current_academic_year()
        
        # Build query for comments
        comments = []
        
        # First, get relevant student IDs based on filters
        students_query = supabase_client.table('students').select('id')
        
        if establishment_id:
            students_query = students_query.eq('establishment_id', establishment_id)
        if academic_year:
            students_query = students_query.eq('academic_year', academic_year)
        if year_group:
            students_query = students_query.eq('year_group', year_group)
        if group:
            students_query = students_query.eq('group', group)
        if faculty:
            students_query = students_query.eq('faculty', faculty)
        if student_id:
            students_query = students_query.eq('id', student_id)
        
        # Fetch all students with pagination
        all_students = []
        page = 0
        PAGE_SIZE = 1000
        
        while True:
            students_result = students_query.range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1).execute()
            if not students_result.data:
                break
            all_students.extend(students_result.data)
            if len(students_result.data) < PAGE_SIZE:
                break
            page += 1
        
        if not all_students:
            return jsonify({
                'wordCloudData': [],
                'totalComments': 0,
                'uniqueWords': 0,
                'topWord': None,
                'message': 'No students found for the selected filters'
            })
        
        student_ids = [s['id'] for s in all_students]
        app.logger.info(f"Found {len(student_ids)} students matching filters")
        
        # Now fetch comments for these students
        # Use batching to avoid URL length issues
        BATCH_SIZE = 50
        all_comments = []
        
        for i in range(0, len(student_ids), BATCH_SIZE):
            batch_ids = student_ids[i:i + BATCH_SIZE]
            
            # Query student_comments table - CAREFUL WITH FIELD NAMES!
            comments_query = supabase_client.table('student_comments')\
                .select('comment_text, comment_type, cycle')\
                .in_('student_id', batch_ids)  # student_id NOT student_ID!
            
            # Apply cycle filter if specified, otherwise get all cycles
            if cycle:
                comments_query = comments_query.eq('cycle', cycle)
            
            batch_result = comments_query.execute()
            
            if batch_result.data:
                for comment in batch_result.data:
                    if comment.get('comment_text'):
                        # Clean HTML tags from comment text
                        clean_text = strip_html_tags(comment['comment_text'])
                        if clean_text:  # Only add if there's content after cleaning
                            all_comments.append(clean_text)
        
        app.logger.info(f"Collected {len(all_comments)} comments")
        
        if not all_comments:
            return jsonify({
                'wordCloudData': [],
                'totalComments': 0,
                'uniqueWords': 0,
                'topWord': None,
                'message': 'No comments found for the selected filters'
            })
        
        # Process comments for word cloud
        import nltk
        from textblob import TextBlob
        from collections import Counter
        import re
        
        # Download required NLTK data if needed
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
        
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
        
        # Add educational context stop words
        custom_stop_words = {
            'need', 'needs', 'would', 'could', 'should', 'think', 'feel', 'feels',
            'really', 'much', 'many', 'also', 'well', 'good', 'better', 'best',
            'help', 'helps', 'make', 'makes', 'get', 'gets', 'know', 'knows',
            'want', 'wants', 'like', 'likes', 'time', 'year', 'work', 'works',
            'will', 'can', 'able', 'try', 'trying', 'going', 'way', 'thing', 'things'
        }
        stop_words.update(custom_stop_words)
        
        word_freq = Counter()
        
        for comment in all_comments:
            # Clean and process comment text
            comment = re.sub(r'http\S+|www.\S+|@\S+', '', comment)
            comment = re.sub(r'[^\w\s]', ' ', comment)
            
            # Tokenize and filter
            blob = TextBlob(comment.lower())
            words = blob.words
            
            for word in words:
                if (len(word) > 2 and 
                    word not in stop_words and 
                    not word.isdigit()):
                    word_freq[word] += 1
        
        # Get top words for word cloud
        top_words = word_freq.most_common(100)
        
        if not top_words:
            return jsonify({
                'wordCloudData': [],
                'totalComments': len(all_comments),
                'uniqueWords': 0,
                'topWord': None,
                'message': 'No meaningful words found in comments'
            })
        
        # Calculate relative sizes for word cloud
        max_count = top_words[0][1] if top_words else 1
        min_size = 10
        max_size = 60
        
        word_cloud_data = []
        for word, count in top_words:
            # Scale size between min_size and max_size
            relative_size = min_size + ((count / max_count) * (max_size - min_size))
            word_cloud_data.append({
                'text': word,
                'size': int(relative_size),
                'count': count
            })
        
        return jsonify({
            'wordCloudData': word_cloud_data,
            'totalComments': len(all_comments),
            'uniqueWords': len(word_freq),
            'topWord': top_words[0] if top_words else None,
            'academicYear': academic_year,
            'cycle': cycle if cycle else 'All Cycles'
        })
        
    except Exception as e:
        app.logger.error(f"Word cloud generation error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        raise ApiError(f"Failed to generate word cloud: {str(e)}", 500)

@app.route('/api/comments/themes', methods=['GET'])
def get_comments_themes():
    """Get themes and sample comments from student comments"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Get filters - CAREFUL WITH FIELD NAMES!
        establishment_id = request.args.get('establishment_id')
        cycle = request.args.get('cycle', type=int)
        academic_year = request.args.get('academic_year')
        year_group = request.args.get('year_group')
        group = request.args.get('group')
        faculty = request.args.get('faculty')
        student_id = request.args.get('student_id')
        
        # Convert IDs if needed
        if establishment_id:
            establishment_id = convert_knack_id_to_uuid(establishment_id)
        if student_id:
            student_id = convert_knack_id_to_uuid(student_id)
        
        # Convert academic year from frontend format (2025-26) to database format (2025/2026)
        if academic_year:
            academic_year = convert_academic_year_format(academic_year, to_database=True)
        else:
            academic_year = get_current_academic_year()
        
        # Get students matching filters
        students_query = supabase_client.table('students').select('id, year_group')
        
        if establishment_id:
            students_query = students_query.eq('establishment_id', establishment_id)
        if academic_year:
            students_query = students_query.eq('academic_year', academic_year)
        if year_group:
            students_query = students_query.eq('year_group', year_group)
        if group:
            students_query = students_query.eq('group', group)
        if faculty:
            students_query = students_query.eq('faculty', faculty)
        if student_id:
            students_query = students_query.eq('id', student_id)
        
        # Fetch students
        all_students = []
        page = 0
        PAGE_SIZE = 1000
        
        while True:
            students_result = students_query.range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1).execute()
            if not students_result.data:
                break
            all_students.extend(students_result.data)
            if len(students_result.data) < PAGE_SIZE:
                break
            page += 1
        
        if not all_students:
            return jsonify({
                'themes': {
                    'positive': [],
                    'improvement': []
                },
                'sampleComments': [],
                'totalComments': 0,
                'message': 'No students found for the selected filters'
            })
        
        # Create student ID to year group mapping
        student_year_map = {s['id']: s.get('year_group', 'Unknown') for s in all_students}
        student_ids = list(student_year_map.keys())
        
        # Fetch comments with batching
        BATCH_SIZE = 50
        all_comments_with_meta = []
        
        for i in range(0, len(student_ids), BATCH_SIZE):
            batch_ids = student_ids[i:i + BATCH_SIZE]
            
            comments_query = supabase_client.table('student_comments')\
                .select('comment_text, comment_type, cycle, student_id, created_at, academic_year')\
                .in_('student_id', batch_ids)
            
            if cycle:
                comments_query = comments_query.eq('cycle', cycle)
            if academic_year:
                comments_query = comments_query.eq('academic_year', academic_year)
            
            batch_result = comments_query.execute()
            
            if batch_result.data:
                for comment in batch_result.data:
                    if comment.get('comment_text'):
                        # Clean HTML tags from comment text
                        clean_text = strip_html_tags(comment['comment_text'])
                        if clean_text:  # Only add if there's content after cleaning
                            all_comments_with_meta.append({
                                'text': clean_text,
                                'type': comment.get('comment_type', 'general'),
                                'cycle': comment.get('cycle'),
                                'yearGroup': student_year_map.get(comment['student_id'], 'Unknown'),
                                'date': comment.get('created_at', '')[:10] if comment.get('created_at') else ''
                            })
        
        app.logger.info(f"Found {len(all_comments_with_meta)} comments for theme analysis")
        
        if not all_comments_with_meta:
            return jsonify({
                'themes': {
                    'positive': [],
                    'improvement': []
                },
                'sampleComments': [],
                'totalComments': 0,
                'message': 'No comments found for the selected filters'
            })
        
        # Import Counter for theme counting
        from collections import Counter
        
        # Analyze comments for themes using simple keyword matching
        # (In production, you might want to use AI here)
        positive_keywords = {
            'excellent': 'Excellence in Learning',
            'amazing': 'Exceptional Performance',
            'confident': 'Strong Confidence',
            'improved': 'Significant Improvement',
            'understanding': 'Deep Understanding',
            'focused': 'Strong Focus',
            'motivated': 'High Motivation',
            'organized': 'Good Organization',
            'progress': 'Good Progress',
            'achieved': 'Achievement'
        }
        
        improvement_keywords = {
            'struggle': 'Academic Challenges',
            'difficult': 'Finding Topics Difficult',
            'help': 'Needs Support',
            'practice': 'More Practice Needed',
            'revision': 'Revision Strategies',
            'time management': 'Time Management',
            'focus': 'Focus and Concentration',
            'confidence': 'Building Confidence',
            'homework': 'Homework Completion',
            'attendance': 'Attendance Issues'
        }
        
        positive_counts = Counter()
        improvement_counts = Counter()
        
        for comment in all_comments_with_meta:
            text_lower = comment['text'].lower()
            
            # Check for positive themes
            for keyword, theme in positive_keywords.items():
                if keyword in text_lower:
                    positive_counts[theme] += 1
            
            # Check for improvement themes
            for keyword, theme in improvement_keywords.items():
                if keyword in text_lower:
                    improvement_counts[theme] += 1
        
        # Format themes
        positive_themes = [
            {'name': theme, 'count': count, 'id': f'pos_{i}'}
            for i, (theme, count) in enumerate(positive_counts.most_common(5))
        ]
        
        improvement_themes = [
            {'name': theme, 'count': count, 'id': f'imp_{i}'}
            for i, (theme, count) in enumerate(improvement_counts.most_common(5))
        ]
        
        # Get sample comments (latest 5)
        sample_comments = sorted(
            all_comments_with_meta,
            key=lambda x: x['date'],
            reverse=True
        )[:5]
        
        return jsonify({
            'themes': {
                'positive': positive_themes,
                'improvement': improvement_themes
            },
            'sampleComments': sample_comments,
            'totalComments': len(all_comments_with_meta),
            'academicYear': academic_year,
            'cycle': cycle if cycle else 'All Cycles'
        })
        
    except Exception as e:
        app.logger.error(f"Theme analysis error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        raise ApiError(f"Failed to analyze themes: {str(e)}", 500)

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
            'redis_cache': CACHE_ENABLED,
            'supabase': SUPABASE_ENABLED
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
    
    # Test Supabase connection if enabled
    if SUPABASE_ENABLED:
        try:
            # Test with a simple RPC call or basic connectivity
            # Since tables might not exist yet, just check if client is initialized
            if supabase_client:
                health_status['services']['supabase_status'] = 'initialized'
            else:
                health_status['services']['supabase_status'] = 'not_initialized'
        except Exception as e:
            health_status['services']['supabase_status'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
    
    return jsonify(health_status)

@app.route('/api/sync/test', methods=['POST'])
def test_sync():
    """Test endpoint to verify sync setup"""
    if not SUPABASE_ENABLED:
        raise ApiError("Supabase not enabled", 503)
    
    try:
        # Test Supabase tables
        tables_status = {}
        tables = ['establishments', 'students', 'vespa_scores', 'question_responses', 'school_statistics']
        
        for table in tables:
            try:
                result = supabase_client.table(table).select('count', count='exact').limit(1).execute()
                tables_status[table] = {
                    'accessible': True,
                    'count': result.count
                }
            except Exception as e:
                tables_status[table] = {
                    'accessible': False,
                    'error': str(e)
                }
        
        # Test Knack connection
        knack_status = {
            'configured': bool(KNACK_APP_ID and KNACK_API_KEY)
        }
        
        if knack_status['configured']:
            try:
                # Test with a simple request
                test_data = make_knack_request('object_2', rows_per_page=1)
                knack_status['connected'] = True
                knack_status['total_establishments'] = test_data.get('total_records', 0)
            except Exception as e:
                knack_status['connected'] = False
                knack_status['error'] = str(e)
        
        return jsonify({
            'supabase_tables': tables_status,
            'knack': knack_status,
            'ready_to_sync': all(t['accessible'] for t in tables_status.values()) and knack_status.get('connected', False)
        })
        
    except Exception as e:
        app.logger.error(f"Sync test error: {e}")
        raise ApiError(f"Sync test failed: {str(e)}", 500)

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
        academic_year = request.args.get('academic_year')
        
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
        
        # Determine academic year to use
        if academic_year:
            # Convert from frontend format (2025-26) to database format (2025/2026) if needed
            academic_year = convert_academic_year_format(academic_year, to_database=True)
        else:
            academic_year = get_current_academic_year()
        
        # Convert to Object_120 format (2024-2025 instead of 2024/2025)
        object120_year = academic_year.replace('/', '-')
        
        # Fetch national benchmark record for specific academic year
        app.logger.info(f"Fetching national ERI for cycle {cycle}, academic year {object120_year} from object_120")
        
        data = make_knack_request(
            'object_120',
            filters=[{
                'field': 'field_3308',  # Academic Year field in Object_120
                'operator': 'is',
                'value': object120_year
            }],
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
        
        # Add filter for cycle completion - check if Vision score exists for the cycle
        # Cycle 1: field_155 (V1), Cycle 2: field_161 (V2), Cycle 3: field_167 (V3)
        cycle_vision_fields = {
            1: 'field_155',  # Vision Cycle 1
            2: 'field_161',  # Vision Cycle 2
            3: 'field_167'   # Vision Cycle 3
        }
        
        if cycle in cycle_vision_fields:
            cycle_filter_field = cycle_vision_fields[cycle]
            trust_filters.append({
                'field': cycle_filter_field,
                'operator': 'is not blank'
            })
            app.logger.info(f"Added cycle {cycle} filter: checking if {cycle_filter_field} (Vision score) exists")

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
        # Determine academic year (using current year as default)
        current_academic_year = get_current_academic_year()
        # Convert to Object_120 format (2024-2025 instead of 2024/2025)
        object120_year = current_academic_year.replace('/', '-')
        
        national_data = make_knack_request(
            'object_120',
            filters=[{
                'field': 'field_3308',  # Academic Year field in Object_120
                'operator': 'is',
                'value': object120_year
            }],
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

@app.route('/api/data-health-check', methods=['POST', 'OPTIONS'])
def check_data_health():
    """
    Compare Object_10 (VESPA scores) and Object_29 (Psychometric responses) to identify data discrepancies.
    Returns health status (green/amber/red) and detailed mismatch information.
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    establishment_id = data.get('establishmentId')
    staff_admin_id = data.get('staffAdminId')
    cycle = data.get('cycle', 1)
    trust_field_value = data.get('trustFieldValue')
    force_refresh = data.get('forceRefresh', False)
    
    # Must have at least one identifier
    if not establishment_id and not staff_admin_id and not trust_field_value:
        raise ApiError("Either establishmentId, staffAdminId, or trustFieldValue must be provided")
    
    # Generate cache key
    cache_key = f"data_health:{establishment_id or 'none'}:{staff_admin_id or 'none'}:{trust_field_value or 'none'}:{cycle}"
    
    # Try cache first unless force refresh
    if CACHE_ENABLED and not force_refresh:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                app.logger.info(f"Returning cached data health check for key: {cache_key}")
                return jsonify(pickle.loads(gzip.decompress(cached_result)))
        except Exception as e:
            app.logger.error(f"Cache retrieval error in data health check: {e}")
    
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
        
        # Add cycle filter for Object_10 - check if Vision score exists for the cycle
        cycle_vision_fields = {
            1: 'field_155',  # Vision Cycle 1
            2: 'field_161',  # Vision Cycle 2
            3: 'field_167'   # Vision Cycle 3
        }
        
        if cycle in cycle_vision_fields:
            cycle_filter_field = cycle_vision_fields[cycle]
            vespa_filters.append({
                'field': cycle_filter_field,
                'operator': 'is not blank'
            })
            app.logger.info(f"Added Object_10 cycle {cycle} filter: checking if {cycle_filter_field} (Vision score) exists")
        
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
        
        # Add academic year filter for Object_29
        psycho_academic_filter = get_academic_year_filters(establishment_id, 'field_856', 'field_3573')
        if psycho_academic_filter:
            psycho_filters.append(psycho_academic_filter)
            app.logger.info("Added academic year filter for Object_29")
        
        # Add cycle filter for Object_29 using cycle-specific fields
        cycle_field_map = {
            1: 'field_1953',  # Cycle 1 Q1 response
            2: 'field_1955',  # Cycle 2 Q1 response  
            3: 'field_1956'   # Cycle 3 Q1 response
        }
        
        if cycle in cycle_field_map:
            # Filter by checking if the Q1 response for this cycle is not blank
            psycho_filters.append({
                'field': cycle_field_map[cycle],
                'operator': 'is not blank'
            })
            app.logger.info(f"Added Object_29 cycle {cycle} filter: checking if {cycle_field_map[cycle]} exists")
        
        # Fetch all records from both objects with pagination
        app.logger.info(f"Fetching VESPA records with filters: {vespa_filters}")
        
        # Determine which score fields to check based on cycle
        cycle_offset = (int(cycle) - 1) * 6
        score_fields = [f'field_{154 + cycle_offset + i}' for i in range(6)]  # Score fields for this cycle
        
        # Include score fields in the fetch to check if they have values
        vespa_fields = ['id', 'field_187_raw', 'field_133_raw'] + [f + '_raw' for f in score_fields]
        
        # Add email field for proper matching
        vespa_fields.append('field_197')  # Email field in Object_10
        vespa_fields.append('field_197_raw')
        
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
                score_value = record.get(f'{field}_raw')
                # Check if score exists and is not empty string (but allow 0)
                if score_value is not None and score_value != '':
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
                fields=['id', 'field_1819_raw', 'field_1821_raw', 'field_2732', 'field_2732_raw', 'field_792_raw', 'field_863', 'field_863_raw']
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
        # For Object_10: map by email AND record ID
        vespa_students = {}
        vespa_by_id = {}
        
        for record in vespa_records:
            # Map by email if available
            email_data = record.get('field_197_raw') or record.get('field_197', {})
            if isinstance(email_data, dict) and email_data.get('email'):
                email = email_data['email'].lower().strip()
                vespa_students[email] = {
                    'id': record['id'],
                    'email': email,
                    'name': f"{record.get('field_187_raw', {}).get('first', '')} {record.get('field_187_raw', {}).get('last', '')}".strip(),
                    'establishment': record.get('field_133_raw', [{}])[0].get('identifier', 'Unknown')
                }
            
            # Also map by record ID for Object_29 connection checking
            vespa_by_id[record['id']] = record
        
        # For Object_29: map by email AND check Object_10 connections
        psycho_students = {}
        psycho_by_object10_connection = {}
        
        for record in psycho_records:
            # First check if it has Object_10 connection
            object10_connection = record.get('field_792_raw', [])
            if object10_connection and len(object10_connection) > 0:
                object10_id = object10_connection[0].get('id', object10_connection[0])
                psycho_by_object10_connection[object10_id] = record
            
            # Also map by email
            email_data = record.get('field_2732_raw') or record.get('field_2732', {})
            if isinstance(email_data, dict) and email_data.get('email'):
                email = email_data['email'].lower().strip()
                psycho_students[email] = {
                    'id': record['id'],
                    'email': email,
                    'cycle': record.get('field_863', record.get('field_863_raw', '')),
                    'establishment': record.get('field_1821_raw', [{}])[0].get('identifier', 'Unknown')
                }
        
        # Find discrepancies using multiple matching methods
        missing_questionnaires = []
        missing_scores = []
        matched_count = 0
        
        # Check each VESPA record
        for vespa_id, vespa_record in vespa_by_id.items():
            # Check if there's a corresponding Object_29 record
            has_object29 = False
            
            # Method 1: Check by Object_10 connection
            if vespa_id in psycho_by_object10_connection:
                has_object29 = True
                matched_count += 1
            else:
                # Method 2: Check by email as fallback
                email_data = vespa_record.get('field_197_raw') or vespa_record.get('field_197', {})
                if isinstance(email_data, dict) and email_data.get('email'):
                    email = email_data['email'].lower().strip()
                    if email in psycho_students:
                        has_object29 = True
                        matched_count += 1
            
            if not has_object29:
                student_name = f"{vespa_record.get('field_187_raw', {}).get('first', '')} {vespa_record.get('field_187_raw', {}).get('last', '')}".strip()
                missing_questionnaires.append({
                    'student_id': vespa_id,
                    'student_name': student_name,
                    'has_vespa_score': True,
                    'has_questionnaire': False,
                    'establishment': vespa_record.get('field_133_raw', [{}])[0].get('identifier', 'Unknown'),
                    'email': (vespa_record.get('field_197_raw') or vespa_record.get('field_197', {})).get('email', 'No email')
                })
                # Log missing questionnaire for debugging
                app.logger.info(f"Missing questionnaire for student: {student_name} (ID: {vespa_id}, Email: {(vespa_record.get('field_197_raw') or vespa_record.get('field_197', {})).get('email', 'No email')})")
        
        # Check for Object_29 records without corresponding Object_10 records
        for object29_record in psycho_records:
            object10_connection = object29_record.get('field_792_raw', [])
            if object10_connection and len(object10_connection) > 0:
                object10_id = object10_connection[0].get('id', object10_connection[0])
                if object10_id not in vespa_by_id:
                    # This Object_29 record points to an Object_10 record we didn't fetch (possibly no scores for this cycle)
                    missing_scores.append({
                        'student_id': object10_id,
                        'student_name': 'Unknown (Object_10 record not in current cycle)',
                        'has_vespa_score': False,
                        'has_questionnaire': True,
                        'questionnaire_id': object29_record['id'],
                        'establishment': object29_record.get('field_1821_raw', [{}])[0].get('identifier', 'Unknown')
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
                'matched_count': matched_count,
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
        
        # Cache the result for 30 seconds (reduced from 60)
        if CACHE_ENABLED:
            try:
                compressed_data = gzip.compress(pickle.dumps(response_data))
                redis_client.setex(cache_key, 30, compressed_data)
                app.logger.info(f"Cached data health check result for key: {cache_key}")
            except Exception as e:
                app.logger.error(f"Cache storage error in data health check: {e}")
        
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"Data health check error: {e}")
        raise ApiError(f"Failed to check data health: {str(e)}", 500)

# ============================================
# SUPABASE-BACKED ENDPOINTS
# ============================================

@app.route('/api/schools', methods=['GET'])
@cached(ttl_key='establishments', ttl_seconds=3600)
def get_schools():
    """Get all schools from Supabase"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Get all establishments
        result = supabase_client.table('establishments').select('*').order('name').execute()
        
        # Format response
        schools = [{
            'id': school['id'],
            'knack_id': school['knack_id'],
            'name': school['name'],
            'is_australian': school.get('is_australian', False),
            'trust_id': school.get('trust_id')
        } for school in result.data]
        
        return jsonify(schools)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch schools: {e}")
        raise ApiError(f"Failed to fetch schools: {str(e)}", 500)

@app.route('/api/statistics/<school_id>', methods=['GET'])
@cached(ttl_key='school_statistics', ttl_seconds=600)
def get_school_statistics(school_id):
    """Get statistics for a specific school"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Convert Knack ID to Supabase UUID if needed
        # Check if it's a valid UUID format
        import uuid
        try:
            uuid.UUID(school_id)
            # It's already a UUID, use as is
            school_uuid = school_id
        except ValueError:
            # It's a Knack ID, need to convert
            est_result = supabase_client.table('establishments').select('id').eq('knack_id', school_id).execute()
            if not est_result.data:
                raise ApiError(f"Establishment not found with ID: {school_id}", 404)
            school_uuid = est_result.data[0]['id']
        
        cycle = request.args.get('cycle', type=int)
        academic_year = request.args.get('academic_year')
        # Convert academic year from frontend format (2025-26) to database format (2025/2026)
        if academic_year:
            academic_year = convert_academic_year_format(academic_year, to_database=True)
        
        # Build query
        query = supabase_client.table('school_statistics').select('*').eq('establishment_id', school_uuid)
        
        if cycle:
            query = query.eq('cycle', cycle)
        if academic_year:
            query = query.eq('academic_year', academic_year)
        
        result = query.execute()
        
        return jsonify(result.data)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch school statistics: {e}")
        raise ApiError(f"Failed to fetch school statistics: {str(e)}", 500)

@app.route('/api/national-statistics', methods=['GET'])
@cached(ttl_key='national_statistics', ttl_seconds=3600)
def get_national_statistics():
    """Get national statistics from Supabase"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        cycle = request.args.get('cycle', type=int)
        academic_year = request.args.get('academic_year')
        
        # Build query
        query = supabase_client.table('national_statistics').select('*')
        
        if cycle:
            query = query.eq('cycle', cycle)
        if academic_year:
            query = query.eq('academic_year', academic_year)
        
        result = query.execute()
        
        return jsonify(result.data)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch national statistics: {e}")
        raise ApiError(f"Failed to fetch national statistics: {str(e)}", 500)

@app.route('/api/national-eri/<int:cycle>', methods=['GET'])
@cached(ttl_key='national_eri', ttl_seconds=3600)
def get_national_eri_by_cycle(cycle):
    """Get national ERI for a specific cycle"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        academic_year = request.args.get('academic_year')
        
        # Query benchmark statistics for ERI (still called national_statistics for backward compatibility)
        # Normalize the academic year for benchmark comparisons
        normalized_year = normalize_academic_year_for_benchmark(academic_year) if academic_year else None
        query = supabase_client.table('national_statistics')\
            .select('eri_score, count, std_dev, percentile_25, percentile_50, percentile_75')\
            .eq('cycle', cycle)\
            .eq('element', 'ERI')
        
        if normalized_year:
            query = query.eq('academic_year', normalized_year)
            
        result = query.execute()
        
        if result.data and result.data[0]:
            eri_data = result.data[0]
            return jsonify({
                'cycle': cycle,
                'academic_year': academic_year,
                'national_eri': float(eri_data.get('eri_score', 0)),
                'student_count': eri_data.get('count', 0),
                'std_dev': float(eri_data.get('std_dev', 0)) if eri_data.get('std_dev') else 0,
                'percentile_25': float(eri_data.get('percentile_25', 0)) if eri_data.get('percentile_25') else 0,
                'percentile_50': float(eri_data.get('percentile_50', 0)) if eri_data.get('percentile_50') else 0,
                'percentile_75': float(eri_data.get('percentile_75', 0)) if eri_data.get('percentile_75') else 0
            })
        else:
            # No data found - return default
            return jsonify({
                'cycle': cycle,
                'academic_year': academic_year,
                'national_eri': 0,
                'student_count': 0,
                'message': 'No national ERI data available for this cycle'
            })
        
    except Exception as e:
        app.logger.error(f"Failed to fetch national ERI: {e}")
        raise ApiError(f"Failed to fetch national ERI: {str(e)}", 500)

@app.route('/api/qla-data', methods=['POST'])
def get_qla_data():
    """Get Question Level Analysis data from Supabase"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        data = request.get_json() or {}
        establishment_id = data.get('establishment_id')
        cycle = data.get('cycle')
        question_ids = data.get('question_ids', [])
        
        # Convert Knack ID to Supabase UUID if needed
        establishment_uuid = None
        if establishment_id:
            # Check if it's a valid UUID format
            import uuid
            try:
                uuid.UUID(establishment_id)
                # It's already a UUID, use as is
                establishment_uuid = establishment_id
            except ValueError:
                # It's a Knack ID, need to convert
                est_result = supabase_client.table('establishments').select('id').eq('knack_id', establishment_id).execute()
                if not est_result.data:
                    raise ApiError(f"Establishment not found with ID: {establishment_id}", 404)
                establishment_uuid = est_result.data[0]['id']
        
        # Query question_statistics directly instead of using RPC
        query = supabase_client.table('question_statistics').select('*')
        
        if establishment_uuid:
            query = query.eq('establishment_id', establishment_uuid)
        if cycle:
            query = query.eq('cycle', cycle)
        
        result = query.execute()
        
        # Filter by question IDs if provided
        qla_data = result.data
        if question_ids:
            qla_data = [q for q in qla_data if q['question_id'] in question_ids]
        
        return jsonify(qla_data)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch QLA data: {e}")
        raise ApiError(f"Failed to fetch QLA data: {str(e)}", 500)

@app.route('/api/current-averages', methods=['GET'])
@cached(ttl_key='current_averages', ttl_seconds=600)
def get_current_averages():
    """Get current school averages from Supabase view"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        establishment_id = request.args.get('establishment_id')
        
        # Convert Knack ID to Supabase UUID if needed
        establishment_uuid = None
        if establishment_id:
            # Check if it's a valid UUID format
            import uuid
            try:
                uuid.UUID(establishment_id)
                # It's already a UUID, use as is
                establishment_uuid = establishment_id
            except ValueError:
                # It's a Knack ID, need to convert
                est_result = supabase_client.table('establishments').select('id').eq('knack_id', establishment_id).execute()
                if not est_result.data:
                    raise ApiError(f"Establishment not found with ID: {establishment_id}", 404)
                establishment_uuid = est_result.data[0]['id']
        
        # Query the current_school_averages view
        query = supabase_client.table('current_school_averages').select('*')
        
        if establishment_uuid:
            query = query.eq('establishment_id', establishment_uuid)
        
        result = query.execute()
        
        return jsonify(result.data)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch current averages: {e}")
        raise ApiError(f"Failed to fetch current averages: {str(e)}", 500)

@app.route('/api/trust/<trust_id>/statistics', methods=['GET'])
@cached(ttl_key='trust_statistics', ttl_seconds=600)
def get_trust_statistics(trust_id):
    """Get aggregated statistics for all schools in a trust"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        cycle = request.args.get('cycle', type=int)
        
        # Get all establishments in the trust
        est_result = supabase_client.table('establishments').select('id').eq('trust_id', trust_id).execute()
        establishment_ids = [e['id'] for e in est_result.data]
        
        if not establishment_ids:
            return jsonify([])
        
        # Get statistics for all establishments
        query = supabase_client.table('school_statistics').select('*').in_('establishment_id', establishment_ids)
        
        if cycle:
            query = query.eq('cycle', cycle)
        
        result = query.execute()
        
        # Aggregate statistics by element
        aggregated = {}
        for stat in result.data:
            key = f"{stat['cycle']}_{stat['element']}"
            if key not in aggregated:
                aggregated[key] = {
                    'cycle': stat['cycle'],
                    'element': stat['element'],
                    'academic_year': stat['academic_year'],
                    'schools': [],
                    'total_count': 0,
                    'weighted_sum': 0
                }
            
            aggregated[key]['schools'].append(stat)
            aggregated[key]['total_count'] += stat['count']
            aggregated[key]['weighted_sum'] += stat['mean'] * stat['count']
        
        # Calculate trust-wide means
        trust_stats = []
        for key, data in aggregated.items():
            if data['total_count'] > 0:
                trust_stats.append({
                    'trust_id': trust_id,
                    'cycle': data['cycle'],
                    'element': data['element'],
                    'academic_year': data['academic_year'],
                    'mean': round(data['weighted_sum'] / data['total_count'], 2),
                    'count': data['total_count'],
                    'school_count': len(data['schools'])
                })
        
        return jsonify(trust_stats)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch trust statistics: {e}")
        raise ApiError(f"Failed to fetch trust statistics: {str(e)}", 500)

@app.route('/api/academic-years', methods=['GET'])
def get_academic_years():
    """Get distinct academic years, optionally filtered by establishment"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        establishment_id = request.args.get('establishment_id')
        
        if establishment_id:
            # Convert Knack ID to UUID if needed
            establishment_uuid = convert_knack_id_to_uuid(establishment_id)
            
            # Get students for this establishment
            students_result = supabase_client.table('students')\
                .select('id')\
                .eq('establishment_id', establishment_uuid)\
                .execute()
            
            if students_result.data:
                student_ids = [s['id'] for s in students_result.data]
                
                # Get distinct academic years from vespa_scores for these students in batches
                BATCH_SIZE = 100  # Can use larger batch for simpler query
                all_years = set()
                
                for i in range(0, len(student_ids), BATCH_SIZE):
                    batch_ids = student_ids[i:i + BATCH_SIZE]
                    batch_result = supabase_client.table('vespa_scores')\
                        .select('academic_year')\
                        .in_('student_id', batch_ids)\
                        .execute()
                    
                    if batch_result.data:
                        for record in batch_result.data:
                            if record['academic_year']:
                                all_years.add(record['academic_year'])
                
                # Convert set to sorted list (most recent first)
                years = sorted(list(all_years), reverse=True)
                
                # FIXED: Return database format (YYYY/YYYY) without conversion
                # This ensures consistency between API, frontend, and database
                if years:
                    return jsonify(years)
        
        # Fall back to national statistics
        result = supabase_client.table('national_statistics')\
            .select('academic_year')\
            .execute()
        
        # Extract unique years
        years = list(set([r['academic_year'] for r in result.data if r.get('academic_year')]))
        years.sort(reverse=True)  # Most recent first
        
        # FIXED: Return database format (YYYY/YYYY) without conversion
        # This ensures consistency between API, frontend, and database
        return jsonify(years)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch academic years: {e}")
        raise ApiError(f"Failed to fetch academic years: {str(e)}", 500)

@app.route('/api/key-stages', methods=['GET'])
def get_key_stages():
    """Return available key stages, optionally filtered by establishment"""
    try:
        establishment_id = request.args.get('establishment_id')
        
        if establishment_id and SUPABASE_ENABLED:
            # Convert Knack ID to UUID if needed
            establishment_uuid = convert_knack_id_to_uuid(establishment_id)
            
            # Get distinct year groups for this establishment
            result = supabase_client.table('students')\
                .select('year_group')\
                .eq('establishment_id', establishment_uuid)\
                .execute()
            
            if result.data:
                # Map year groups to key stages
                key_stages = set()
                for r in result.data:
                    year_group = r.get('year_group')
                    if year_group:
                        if year_group in ['7', '8', '9']:
                            key_stages.add('KS3')
                        elif year_group in ['10', '11']:
                            key_stages.add('KS4')
                        elif year_group in ['12', '13']:
                            key_stages.add('KS5')
                
                # Sort key stages
                sorted_stages = sorted(list(key_stages))
                if sorted_stages:
                    return jsonify(sorted_stages)
        
        # Default key stages if no establishment specified or no data
        return jsonify(['KS3', 'KS4', 'KS5'])
        
    except Exception as e:
        app.logger.error(f"Failed to fetch key stages: {e}")
        # Return default on error
        return jsonify(['KS3', 'KS4', 'KS5'])

@app.route('/api/year-groups', methods=['GET'])
def get_year_groups():
    """Return available year groups, optionally filtered by establishment"""
    try:
        establishment_id = request.args.get('establishment_id')
        
        if establishment_id and SUPABASE_ENABLED:
            # Convert Knack ID to UUID if needed
            establishment_uuid = convert_knack_id_to_uuid(establishment_id)
            
            # Get distinct year groups for this establishment
            result = supabase_client.table('students')\
                .select('year_group')\
                .eq('establishment_id', establishment_uuid)\
                .execute()
            
            if result.data:
                # Extract unique year groups and sort them
                year_groups = list(set(r['year_group'] for r in result.data if r.get('year_group')))
                # Sort numerically
                year_groups.sort(key=lambda x: int(x) if x.isdigit() else 99)
                return jsonify(year_groups)
        
        # Default year groups if no establishment specified or no data
        return jsonify(['7', '8', '9', '10', '11', '12', '13'])
        
    except Exception as e:
        app.logger.error(f"Failed to fetch year groups: {e}")
        # Return default on error
        return jsonify(['7', '8', '9', '10', '11', '12', '13'])

@app.route('/api/groups', methods=['GET'])
def get_groups():
    """Return available groups, optionally filtered by establishment"""
    try:
        establishment_id = request.args.get('establishment_id')
        
        if not establishment_id or not SUPABASE_ENABLED:
            return jsonify([])
        
        # Convert Knack ID to UUID if needed
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        
        # Get distinct groups for this establishment
        result = supabase_client.table('students')\
            .select('group')\
            .eq('establishment_id', establishment_uuid)\
            .execute()
        
        if result.data:
            # Extract unique groups and sort them
            groups = list(set(r['group'] for r in result.data if r.get('group')))
            groups.sort()
            return jsonify(groups)
        
        return jsonify([])
        
    except Exception as e:
        app.logger.error(f"Failed to fetch groups: {e}")
        return jsonify([])

@app.route('/api/faculties', methods=['GET'])
def get_faculties():
    """Return available faculties, optionally filtered by establishment"""
    try:
        establishment_id = request.args.get('establishment_id')
        
        if not establishment_id or not SUPABASE_ENABLED:
            return jsonify([])
        
        # Convert Knack ID to UUID if needed
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        
        # Get distinct faculties for this establishment
        result = supabase_client.table('students')\
            .select('faculty')\
            .eq('establishment_id', establishment_uuid)\
            .execute()
        
        if result.data:
            # Extract unique faculties and sort them
            faculties = list(set(r['faculty'] for r in result.data if r.get('faculty')))
            faculties.sort()
            return jsonify(faculties)
        
        return jsonify([])
        
    except Exception as e:
        app.logger.error(f"Failed to fetch faculties: {e}")
        return jsonify([])

@app.route('/api/students/search', methods=['GET'])
def search_students():
    """Search for students by name or email"""
    try:
        establishment_id = request.args.get('establishment_id')
        search_term = request.args.get('q', '').strip()
        
        if not establishment_id or not search_term or not SUPABASE_ENABLED:
            return jsonify([])
        
        # Convert Knack ID to UUID if needed
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        
        # Search for students by name or email (case-insensitive)
        # Using ilike for case-insensitive partial matching
        # Search by name first
        name_result = supabase_client.table('students')\
            .select('id, name, email, year_group, group, faculty')\
            .eq('establishment_id', establishment_uuid)\
            .ilike('name', f'%{search_term}%')\
            .limit(20)\
            .execute()
        
        # Search by email
        email_result = supabase_client.table('students')\
            .select('id, name, email, year_group, group, faculty')\
            .eq('establishment_id', establishment_uuid)\
            .ilike('email', f'%{search_term}%')\
            .limit(20)\
            .execute()
        
        # Combine results and remove duplicates
        all_students = []
        seen_ids = set()
        
        for student in (name_result.data or []) + (email_result.data or []):
            if student['id'] not in seen_ids:
                seen_ids.add(student['id'])
                all_students.append(student)
        
        # Limit to 20 results
        result = SimpleNamespace(data=all_students[:20])
        
        if result.data:
            # Format results for frontend
            students = []
            for student in result.data:
                students.append({
                    'id': student['id'],
                    'name': student['name'],
                    'email': student['email'],
                    'yearGroup': student.get('year_group', ''),
                    'group': student.get('group', ''),
                    'faculty': student.get('faculty', ''),
                    'displayText': f"{student['name']} ({student.get('year_group', 'N/A')})"
                })
            return jsonify(students)
        
        return jsonify([])
        
    except Exception as e:
        app.logger.error(f"Failed to search students: {e}")
        return jsonify([])

@app.route('/api/establishment/<establishment_id>', methods=['GET'])
@cached(ttl_key='establishment', ttl_seconds=3600)
def get_establishment(establishment_id):
    """Get establishment details"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        result = supabase_client.table('establishments')\
            .select('id, name, knack_id, is_australian, trust_id')\
            .eq('id', establishment_id)\
            .execute()
        
        if not result.data:
            raise ApiError("Establishment not found", 404)
        
        return jsonify(result.data[0])
        
    except Exception as e:
        app.logger.error(f"Failed to fetch establishment: {e}")
        raise ApiError(f"Failed to fetch establishment: {str(e)}", 500)

@app.route('/api/check-super-user', methods=['GET', 'OPTIONS'])
def check_super_user():
    """Check if a user is a super user by email"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        email = request.args.get('email')
        app.logger.info(f"[CHECK-SUPER-USER] Checking super user status for email: {email}")
        
        if not email:
            app.logger.warning("[CHECK-SUPER-USER] No email parameter provided")
            return jsonify({'error': 'Email parameter required'}), 400
        
        if not SUPABASE_ENABLED:
            app.logger.warning("[CHECK-SUPER-USER] Supabase not enabled")
            return jsonify({'error': 'Supabase not configured'}), 503
        
        app.logger.info(f"[CHECK-SUPER-USER] Supabase enabled: {SUPABASE_ENABLED}, client exists: {supabase_client is not None}")
        
        # Check super_users table
        result = supabase_client.table('super_users').select('*').eq('email', email).execute()
        
        app.logger.info(f"[CHECK-SUPER-USER] Super user query result: {result.data}")
        
        if result.data and len(result.data) > 0:
            user = result.data[0]
            return jsonify({
                'is_super_user': True,
                'user': {
                    'id': user['id'],
                    'knack_id': user.get('knack_id'),
                    'name': user.get('name'),
                    'email': user['email']
                }
            })
        else:
            return jsonify({
                'is_super_user': False,
                'user': None
            })
        
    except Exception as e:
        app.logger.error(f"[CHECK-SUPER-USER] Failed to check super user status: {type(e).__name__}: {str(e)}")
        app.logger.error(f"[CHECK-SUPER-USER] Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# ===== FIXED SUPABASE ENDPOINTS FOR DASHBOARD4A.JS =====

@app.route('/api/statistics', methods=['GET'])
def get_school_statistics_query():
    """Get statistics for a specific school (query parameter version)"""
    try:
        establishment_id = request.args.get('establishment_id')
        if not establishment_id:
            raise ApiError("establishment_id is required", 400)
            
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Convert Knack ID to Supabase UUID if needed
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        
        cycle = request.args.get('cycle', type=int, default=1)
        academic_year = request.args.get('academic_year')
        # Convert academic year from frontend format (2025-26) to database format (2025/2026)
        if academic_year:
            academic_year = convert_academic_year_format(academic_year, to_database=True)
        year_group = request.args.get('yearGroup')
        group = request.args.get('group')
        faculty = request.args.get('faculty')
        student_id = request.args.get('studentId')
        
        # Check if we have any filters other than cycle
        has_other_filters = (year_group and year_group != 'all') or \
                           (group and group != 'all') or \
                           (faculty and faculty != 'all') or \
                           student_id
        
        # Get filtered students for queries
        all_students = []
        offset = 0
        limit = 1000
        
        while True:
            # Build query with filters
            query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)
            
            # DON'T filter by academic_year on students table - we'll check VESPA data instead
            # if academic_year:
            #     query = query.eq('academic_year', academic_year)  # REMOVED - this was the bug
            
            # Apply other filters
            if student_id:
                query = query.eq('id', student_id)
            else:
                if year_group and year_group != 'all':
                    query = query.eq('year_group', year_group)
                if group and group != 'all':
                    query = query.eq('group', group)
                if faculty and faculty != 'all':
                    query = query.eq('faculty', faculty)
            
            students_batch = query.limit(limit).offset(offset).execute()
            
            batch_count = len(students_batch.data) if students_batch.data else 0
            app.logger.info(f"Student fetch batch: offset={offset}, got {batch_count} students")
            
            if not students_batch.data:
                break
                
            all_students.extend(students_batch.data)
            
            # If we got less than the limit, we've reached the end
            if batch_count < limit:
                break
                
            offset += limit
        
        student_ids = [s['id'] for s in all_students]
        
        # NEW: Filter by who has VESPA data for the selected academic year
        if academic_year:
            students_with_vespa = []
            
            # Check in batches who has VESPA data for this year
            for i in range(0, len(student_ids), 50):
                batch_ids = student_ids[i:i+50]
                
                # Check which students have VESPA data for the selected year
                vespa_check = supabase_client.table('vespa_scores')\
                    .select('student_id')\
                    .in_('student_id', batch_ids)\
                    .eq('academic_year', academic_year)\
                    .eq('cycle', cycle)\
                    .limit(1000)\
                    .execute()
                
                students_with_vespa_ids = set(v['student_id'] for v in vespa_check.data)
                
                # Keep only students who have VESPA data
                students_with_vespa.extend([sid for sid in batch_ids if sid in students_with_vespa_ids])
            
            student_ids = students_with_vespa
            app.logger.info(f"After academic year filter: {len(student_ids)} students have data for {academic_year} cycle {cycle}")
        
        app.logger.info(f"Found {len(student_ids)} students for establishment {establishment_id}")
        
        # Get total enrolled students - but we'll calculate the actual total based on who has VESPA scores for this cycle
        total_enrolled_students = len(student_ids)  # Default to filtered count
        
        # If academic_year is specified, count students in that academic year
        if academic_year and not has_other_filters:
            # NEW: Count students directly from their academic_year field
            # This gives us the EXACT enrollment count for that academic year
            total_query = supabase_client.table('students')\
                .select('id', count='exact')\
                .eq('establishment_id', establishment_uuid)\
                .eq('academic_year', academic_year)
            
            total_result = total_query.execute()
            
            if hasattr(total_result, 'count') and total_result.count is not None:
                total_enrolled_students = total_result.count
                app.logger.info(f"Total students enrolled for academic year {academic_year}: {total_enrolled_students}")
            else:
                # Fallback: count manually
                all_year_students = []
                offset = 0
                limit = 1000
                
                while True:
                    batch_query = supabase_client.table('students')\
                        .select('id')\
                        .eq('establishment_id', establishment_uuid)\
                        .eq('academic_year', academic_year)\
                        .limit(limit).offset(offset)
                    batch_result = batch_query.execute()
                    
                    if not batch_result.data:
                        break
                    
                    all_year_students.extend(batch_result.data)
                    
                    if len(batch_result.data) < limit:
                        break
                    offset += limit
                
                total_enrolled_students = len(all_year_students)
                app.logger.info(f"Total students enrolled for academic year {academic_year} (counted): {total_enrolled_students}")
        elif not has_other_filters:
            # No academic year filter - count all students in establishment (old behavior)
            # When no filters except cycle, we want to show total students who could have responses for this cycle
            # This will be recalculated later based on actual VESPA scores
            total_query = supabase_client.table('students').select('id', count='exact').eq('establishment_id', establishment_uuid)
            total_result = total_query.execute()
            if hasattr(total_result, 'count') and total_result.count is not None:
                total_enrolled_students = total_result.count
                app.logger.info(f"Total enrolled students in establishment: {total_enrolled_students}")
            else:
                # Fallback: count all students manually
                all_enrolled = []
                offset = 0
                while True:
                    batch = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid).limit(1000).offset(offset).execute()
                    if not batch.data:
                        break
                    all_enrolled.extend(batch.data)
                    if len(batch.data) < 1000:
                        break
                    offset += 1000
                total_enrolled_students = len(all_enrolled)
                app.logger.info(f"Total enrolled students in establishment (counted): {total_enrolled_students}")
        
        if not student_ids:
            # No students, return empty data
            return jsonify({
                'totalStudents': 0,
                'averageERI': 0,
                'eriChange': 0,
                'completionRate': 0,
                'averageScore': 0,
                'scoreChange': 0,
                'nationalERI': 0,
                'eriTrend': 'stable',
                'vespaScores': {
                    'vision': 0,
                    'effort': 0,
                    'systems': 0,
                    'practice': 0,
                    'attitude': 0,
                    'nationalVision': 0,
                    'nationalEffort': 0,
                    'nationalSystems': 0,
                    'nationalPractice': 0,
                    'nationalAttitude': 0
                },
                'comparison': {
                    'school': [0, 0, 0, 0, 0],
                    'national': [0, 0, 0, 0, 0]
                },
                'yearGroupPerformance': {
                    'labels': [],
                    'scores': []
                },
                'establishment_id': establishment_id,
                'cycle': cycle,
                'academic_year': academic_year
            })
        
        # Get VESPA scores for these students in batches to avoid URL length limits
        BATCH_SIZE = 50  # Process 50 students at a time to stay well under URL limits
        all_vespa_scores = []
        seen_student_ids = set()  # Track unique students to avoid duplicates
            
        # Also filter by academic_year if provided
        for i in range(0, len(student_ids), BATCH_SIZE):
            batch_ids = student_ids[i:i + BATCH_SIZE]
            vespa_query = supabase_client.table('vespa_scores')\
                .select('*')\
                .in_('student_id', batch_ids)\
                .eq('cycle', cycle)
            
            if academic_year:
                vespa_query = vespa_query.eq('academic_year', academic_year)
                
            batch_result = vespa_query.execute()
            if batch_result.data:
                # Deduplicate by student_id - only keep one record per student per cycle
                # Also filter out records with all NULL scores
                for score in batch_result.data:
                    if score['student_id'] not in seen_student_ids:
                        # Check if the student has at least one non-NULL VESPA score
                        has_scores = any([
                            score.get('vision'),
                            score.get('effort'),
                            score.get('systems'),
                            score.get('practice'),
                            score.get('attitude'),
                            score.get('overall')
                        ])
                        if has_scores:
                            seen_student_ids.add(score['student_id'])
                            all_vespa_scores.append(score)
            
        app.logger.info(f"VESPA scores: Found {len(all_vespa_scores)} scores for {len(student_ids)} students")
        
        # Create a simple object to hold the data
        vespa_result = SimpleNamespace(data=all_vespa_scores)
        
        # Initialize distributions variable
        vespa_distributions = None
        nat_stats_by_element = {}
        comparison_national = []
        
        # Initialize variables for all paths
        vespa_scores = {}
        comparison_school = []
        comparison_national = []
        vespa_distributions = None
        nat_stats_by_element = {}
        overall_avg = 0
        
        # Flag to track which data source we're using
        using_school_stats = False
        
        if not vespa_result.data:
            # Try to get data from school_statistics as fallback
            stats_result = supabase_client.table('school_statistics').select('*').eq('establishment_id', establishment_uuid).eq('cycle', cycle).execute()
            
            if stats_result.data:
                using_school_stats = True
                # Use school_statistics data
                stats_by_element = {}
                for stat in stats_result.data:
                    element = stat['element'].lower()
                    stats_by_element[element] = float(stat['mean']) if stat['mean'] else 0
                
                # Get benchmark statistics (still called national_statistics for backward compatibility)
                # Normalize the academic year for benchmark comparisons
                normalized_year = normalize_academic_year_for_benchmark(academic_year) if academic_year else None
                nat_query = supabase_client.table('national_statistics').select('*').eq('cycle', cycle)
                if normalized_year:
                    nat_query = nat_query.eq('academic_year', normalized_year)
                else:
                    # If no academic year specified, get the most recent data for this cycle
                    recent_year_query = supabase_client.table('national_statistics')\
                        .select('academic_year')\
                        .eq('cycle', cycle)\
                        .order('academic_year', desc=True)\
                        .limit(1)\
                        .execute()
                    if recent_year_query.data:
                        most_recent_year = recent_year_query.data[0]['academic_year']
                        nat_query = nat_query.eq('academic_year', most_recent_year)
                nat_result = nat_query.execute()
                for stat in nat_result.data:
                    element = stat['element'].lower()
                    nat_stats_by_element[element] = float(stat['mean']) if stat['mean'] else 0
                
                # Convert 10-point scale to 5-point scale
                vespa_elements = ['vision', 'effort', 'systems', 'practice', 'attitude']
                
                for elem in vespa_elements:
                    # Convert from 10-point to 5-point scale
                    school_score = stats_by_element.get(elem, 0) / 2.0 if stats_by_element.get(elem, 0) > 5 else stats_by_element.get(elem, 0)
                    national_score = nat_stats_by_element.get(elem, 0) / 2.0 if nat_stats_by_element.get(elem, 0) > 5 else nat_stats_by_element.get(elem, 0)
                    
                    vespa_scores[elem] = round(school_score, 2)
                    vespa_scores[f'national{elem.capitalize()}'] = round(national_score, 2)
                    
                    comparison_school.append(round(school_score, 2))
                    comparison_national.append(round(national_score, 2))
                
                # Get total students - use appropriate count based on filters
                if has_other_filters:
                    total_students = len(student_ids)  # Filtered total
                else:
                    total_students = total_enrolled_students  # Total enrolled (no filters)
                students_with_vespa_scores = stats_result.data[0].get('count', 0) if stats_result.data else 0
                
                # Calculate overall average for school_statistics path
                overall_avg = stats_by_element.get('overall', sum(comparison_school) / len(comparison_school)) if comparison_school else 0
                vespa_scores['overall'] = round(overall_avg, 2)
            else:
                # No data at all
                # Still return the total enrolled/filtered count even if no VESPA data
                if has_other_filters:
                    no_data_total = len(student_ids)  # Filtered total
                else:
                    no_data_total = total_enrolled_students  # Total enrolled
                return jsonify({
                    'totalStudents': no_data_total,
                    'totalResponses': 0,
                    'averageERI': 0,
                    'eriChange': 0,
                    'completionRate': 0,
                    'averageScore': 0,
                    'scoreChange': 0,
                    'nationalERI': 0,
                    'eriTrend': 'stable',
                    'vespaScores': {
                        'vision': 0,
                        'effort': 0,
                        'systems': 0,
                        'practice': 0,
                        'attitude': 0,
                        'nationalVision': 0,
                        'nationalEffort': 0,
                        'nationalSystems': 0,
                        'nationalPractice': 0,
                        'nationalAttitude': 0
                    },
                    'comparison': {
                        'school': [0, 0, 0, 0, 0],
                        'national': [0, 0, 0, 0, 0]
                    },
                    'yearGroupPerformance': {
                        'labels': [],
                        'scores': []
                    },
                    'establishment_id': establishment_id,
                    'cycle': cycle,
                    'academic_year': academic_year
                })
        
        # Process VESPA data if we have it and not using school stats
        elif vespa_result.data and not using_school_stats:
            # Calculate averages from actual VESPA scores
            # Use the count of unique students with VESPA scores for display
            students_with_vespa_scores = len(seen_student_ids)
            # Use the appropriate total based on whether filters are applied
            if has_other_filters:
                total_students = len(student_ids)  # Filtered total
            else:
                # When no filters except cycle, use the maximum students across all cycles as the baseline
                # This gives us the "100%" reference point
                total_students = total_enrolled_students  # Total enrolled in establishment
            
            app.logger.info(f"Students analysis - Total: {total_students} (filtered: {has_other_filters}), With VESPA scores: {students_with_vespa_scores})")
            
            # Check if this is for a single student
            if student_id and students_with_vespa_scores == 1:
                # Individual student view - return their actual scores
                individual_scores = vespa_result.data[0]
                vespa_scores = {
                    'vision': individual_scores.get('vision', 0),
                    'effort': individual_scores.get('effort', 0),
                    'systems': individual_scores.get('systems', 0),
                    'practice': individual_scores.get('practice', 0),
                    'attitude': individual_scores.get('attitude', 0),
                    'overall': individual_scores.get('overall', 0)
                }
                comparison_school = [
                    vespa_scores['vision'],
                    vespa_scores['effort'],
                    vespa_scores['systems'],
                    vespa_scores['practice'],
                    vespa_scores['attitude']
                ]
                overall_avg = vespa_scores['overall']
                # No distributions for individual student
                vespa_distributions = None
            else:
                # Multiple students - calculate averages and distributions
                vespa_sums = {'vision': 0, 'effort': 0, 'systems': 0, 'practice': 0, 'attitude': 0, 'overall': 0}
                vespa_counts = {'vision': 0, 'effort': 0, 'systems': 0, 'practice': 0, 'attitude': 0, 'overall': 0}
                
                # Initialize distributions (1-10 scale)
                vespa_distributions = {}
                for elem in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                    vespa_distributions[elem] = [0] * 10  # 10 slots for scores 1-10
                
                for score in vespa_result.data:
                    for elem in vespa_sums:
                        if score.get(elem) is not None:
                            score_value = score[elem]
                            vespa_sums[elem] += score_value
                            vespa_counts[elem] += 1
                            # Add to distribution (round to nearest integer for histogram)
                            # VESPA scores are 1-10, so subtract 1 for array index
                            rounded_score = round(score_value)
                            if 1 <= rounded_score <= 10:
                                vespa_distributions[elem][rounded_score - 1] += 1
                
                # Calculate school averages (already on correct scale)
                vespa_scores = {}
                comparison_school = []
                
                for elem in ['vision', 'effort', 'systems', 'practice', 'attitude']:
                    avg = vespa_sums[elem] / vespa_counts[elem] if vespa_counts[elem] > 0 else 0
                    vespa_scores[elem] = round(avg, 2)
                    comparison_school.append(round(avg, 2))
                
                # Add overall average
                overall_avg = vespa_sums['overall'] / vespa_counts['overall'] if vespa_counts['overall'] > 0 else 0
                vespa_scores['overall'] = round(overall_avg, 2)
            
            # Get benchmark statistics (still called national_statistics for backward compatibility)
            # Normalize the academic year for benchmark comparisons
            normalized_year = normalize_academic_year_for_benchmark(academic_year) if academic_year else None
            nat_query = supabase_client.table('national_statistics').select('*').eq('cycle', cycle)
            if normalized_year:
                nat_query = nat_query.eq('academic_year', normalized_year)
            else:
                # If no academic year specified, get the most recent data for this cycle
                # First get the most recent academic year for this cycle
                recent_year_query = supabase_client.table('national_statistics')\
                    .select('academic_year')\
                    .eq('cycle', cycle)\
                    .order('academic_year', desc=True)\
                    .limit(1)\
                    .execute()
                if recent_year_query.data:
                    most_recent_year = recent_year_query.data[0]['academic_year']
                    nat_query = nat_query.eq('academic_year', most_recent_year)
                    app.logger.info(f"Using most recent academic year for national stats: {most_recent_year}")
            nat_result = nat_query.execute()
            
            app.logger.info(f"National statistics query returned {len(nat_result.data)} records")
            nat_stats_by_element = {}
            for stat in nat_result.data:
                element = stat['element'].lower()
                value = float(stat['mean']) if stat['mean'] else 0
                nat_stats_by_element[element] = value
                app.logger.info(f"National stat: {element} = {value}")
            
            # Add national scores and log them
            comparison_national = []
            for elem in ['vision', 'effort', 'systems', 'practice', 'attitude']:
                national_score = round(nat_stats_by_element.get(elem, 0), 2)
                vespa_scores[f'national{elem.capitalize()}'] = national_score
                comparison_national.append(national_score)
            
            app.logger.info(f"National scores for comparison: {comparison_national}")
            app.logger.info(f"National stats by element: {nat_stats_by_element}")
            
            # Add national overall
            vespa_scores['nationalOverall'] = round(nat_stats_by_element.get('overall', 0), 2)
        
        # Calculate ERI from outcome questions
        eri_calculated = False
        school_eri = 0
        national_eri = 0
        
        if student_ids:
            # Get outcome question responses for these students
            outcome_questions = ['outcome_q_confident', 'outcome_q_equipped', 'outcome_q_support']
            
            # Get question responses for outcome questions in batches
            BATCH_SIZE = 50
            all_outcome_responses = []
            
            for i in range(0, len(student_ids), BATCH_SIZE):
                batch_ids = student_ids[i:i + BATCH_SIZE]
                batch_result = supabase_client.table('question_responses')\
                    .select('*')\
                    .in_('student_id', batch_ids)\
                    .in_('question_id', outcome_questions)\
                    .eq('cycle', cycle)\
                    .execute()
                if batch_result.data:
                    all_outcome_responses.extend(batch_result.data)
            
            outcome_responses = SimpleNamespace(data=all_outcome_responses)
            
            if outcome_responses.data:
                # Calculate average ERI from outcome questions (1-5 scale)
                eri_sum = 0
                eri_count = 0
                
                for response in outcome_responses.data:
                    if response.get('response_value') is not None:
                        eri_sum += int(response['response_value'])
                        eri_count += 1
                
                if eri_count > 0:
                    school_eri = eri_sum / eri_count
                    eri_calculated = True
                    
                    # Get benchmark ERI from national_statistics (global benchmarks)
                    # Normalize the academic year for benchmark comparisons
                    normalized_year = normalize_academic_year_for_benchmark(academic_year) if academic_year else None
                    eri_query = supabase_client.table('national_statistics')\
                        .select('eri_score, academic_year')\
                        .eq('cycle', cycle)\
                        .eq('element', 'ERI')
                    
                    if normalized_year:
                        eri_query = eri_query.eq('academic_year', normalized_year)
                        app.logger.info(f"Querying benchmark ERI for cycle {cycle}, normalized_year {normalized_year}")
                    else:
                        # If no academic year specified, first get the most recent academic year for this cycle
                        app.logger.info(f"No academic year specified for national ERI, fetching most recent for cycle {cycle}")
                        recent_year_query = supabase_client.table('national_statistics')\
                            .select('academic_year')\
                            .eq('cycle', cycle)\
                            .eq('element', 'ERI')\
                            .order('academic_year', desc=True)\
                            .limit(1)\
                            .execute()
                        
                        if recent_year_query.data and recent_year_query.data[0]['academic_year']:
                            most_recent_year = recent_year_query.data[0]['academic_year']
                            eri_query = eri_query.eq('academic_year', most_recent_year)
                            app.logger.info(f"Using most recent academic year for national ERI: {most_recent_year}")
                    
                    eri_result = eri_query.execute()
                    
                    if eri_result.data and eri_result.data[0].get('eri_score'):
                        national_eri = float(eri_result.data[0]['eri_score'])
                        app.logger.info(f"Found national ERI: {national_eri} for cycle {cycle}, academic_year: {eri_result.data[0].get('academic_year')}")
                    else:
                        # Fallback to calculated average from national VESPA scores
                        app.logger.warning(f"No national ERI found in database for cycle {cycle}, using fallback calculation")
                        national_eri = sum(comparison_national) / len(comparison_national) if comparison_national else 3.5
        
        # Fallback to VESPA average if no outcome data
        if not eri_calculated:
            school_eri = sum(comparison_school) / len(comparison_school) if comparison_school else 0
            # Try to get national ERI from database first
            if not national_eri or national_eri == 0:
                eri_query = supabase_client.table('national_statistics')\
                    .select('eri_score, academic_year')\
                    .eq('cycle', cycle)\
                    .eq('element', 'ERI')
                    
                if academic_year:
                    eri_query = eri_query.eq('academic_year', academic_year)
                else:
                    # If no academic year specified, first get the most recent academic year for this cycle
                    recent_year_query = supabase_client.table('national_statistics')\
                        .select('academic_year')\
                        .eq('cycle', cycle)\
                        .eq('element', 'ERI')\
                        .order('academic_year', desc=True)\
                        .limit(1)\
                        .execute()
                    
                    if recent_year_query.data and recent_year_query.data[0]['academic_year']:
                        most_recent_year = recent_year_query.data[0]['academic_year']
                        eri_query = eri_query.eq('academic_year', most_recent_year)
                        app.logger.info(f"Using most recent academic year for fallback national ERI: {most_recent_year}")
                
                eri_result = eri_query.execute()
                
                if eri_result.data and eri_result.data[0].get('eri_score'):
                    national_eri = float(eri_result.data[0]['eri_score'])
                    app.logger.info(f"Found fallback national ERI: {national_eri} for cycle {cycle}")
                else:
                    # Final fallback to VESPA average
                    app.logger.warning(f"No national ERI found even in fallback, calculating from VESPA averages")
                    national_eri = sum(comparison_national) / len(comparison_national) if comparison_national else 0
        
        # Calculate completion rate
        # students_with_vespa_scores is the count of students with vespa scores for this cycle
        # total_students is either all enrolled (if only cycle filter) or filtered total (if other filters applied)
        completion_rate = (students_with_vespa_scores / total_students * 100) if total_students > 0 else 0
        
        # Determine ERI trend
        eri_diff = school_eri - national_eri
        eri_trend = 'up' if eri_diff > 0.1 else 'down' if eri_diff < -0.1 else 'stable'
        
        # Build response with distributions
        app.logger.info(f"Building response - Cycle: {cycle}, Academic Year: {academic_year}")
        app.logger.info(f"Total Students: {total_students}, Students with VESPA: {students_with_vespa_scores}")
        app.logger.info(f"National ERI: {national_eri}, School ERI: {school_eri}")
        app.logger.info(f"Has other filters: {has_other_filters}, Total enrolled: {total_enrolled_students}")
        
        response_data = {
            'totalStudents': total_students,  # Total enrolled (if only cycle) or filtered total (if other filters)
            'totalResponses': students_with_vespa_scores,  # Students who completed VESPA in this cycle
            'averageERI': round(school_eri, 1),
            'eriChange': round(eri_diff, 1),
            'completionRate': round(completion_rate, 0),
            'averageScore': round(sum(comparison_school) / len(comparison_school), 1) if comparison_school else 0,
            'scoreChange': round(eri_diff, 1),
            'nationalERI': round(national_eri, 1),
            'eriTrend': eri_trend,
            'vespaScores': vespa_scores,
            'comparison': {
                'school': comparison_school,
                'national': comparison_national
            },
            'yearGroupPerformance': {
                'labels': [],  # TODO: Add year group breakdown
                'scores': []   # TODO: Add year group scores
            },
            'establishment_id': establishment_id,
            'cycle': cycle,
            'academic_year': academic_year
        }
        
        # Add distributions if we calculated them from actual vespa data
        if vespa_distributions is not None:
            response_data['distributions'] = vespa_distributions
            app.logger.info(f"Returning distributions for {len(vespa_distributions)} elements")
        
        # Get national distributions
        try:
            # First, calculate national averages from current_school_averages (primary method)
            app.logger.info(f"Calculating national averages from current_school_averages")
            
            # Get all school averages for this cycle
            school_avg_query = supabase_client.table('current_school_averages')\
                .select('element,mean,count')\
                .eq('cycle', cycle)
            
            if academic_year:
                school_avg_query = school_avg_query.eq('academic_year', academic_year)
            else:
                # If no academic year specified, get the most recent data for this cycle
                app.logger.info(f"No academic year specified, fetching most recent data for cycle {cycle}")
                
            school_avg_result = school_avg_query.execute()
            
            if school_avg_result.data:
                # Calculate weighted average for each element
                element_sums = {}
                element_counts = {}
                
                for avg in school_avg_result.data:
                    elem = avg['element'].lower() if avg['element'] else None
                    if elem and elem in ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall']:
                        if elem not in element_sums:
                            element_sums[elem] = 0
                            element_counts[elem] = 0
                        
                        # Weighted average: sum(mean * count) / sum(count)
                        mean_val = float(avg.get('mean', 0)) if avg.get('mean') is not None else 0
                        count_val = int(avg.get('count', 0)) if avg.get('count') is not None else 0
                        
                        element_sums[elem] += mean_val * count_val
                        element_counts[elem] += count_val
                
                # Calculate national averages
                for elem in element_sums:
                    if element_counts[elem] > 0:
                        national_avg = element_sums[elem] / element_counts[elem]
                        nat_stats_by_element[elem] = round(national_avg, 2)
                        app.logger.info(f"Calculated national average for {elem}: {national_avg} from {element_counts[elem]} students")
                
                # Update comparison_national with calculated values
                if nat_stats_by_element:
                    comparison_national = []
                    for elem in ['vision', 'effort', 'systems', 'practice', 'attitude']:
                        comparison_national.append(nat_stats_by_element.get(elem, 0))
                    response_data['comparison']['national'] = comparison_national
                    
                    # Also update vespaScores with national values
                    for elem in ['vision', 'effort', 'systems', 'practice', 'attitude']:
                        response_data['vespaScores'][f'national{elem.capitalize()}'] = nat_stats_by_element.get(elem, 0)
                    response_data['vespaScores']['nationalOverall'] = nat_stats_by_element.get('overall', 0)
                    
                    app.logger.info(f"National averages from current_school_averages: {comparison_national}")
            
            # Then get distributions from national_statistics
            query = supabase_client.table('national_statistics')\
                .select('element,distribution,mean,academic_year')\
                .eq('cycle', cycle)
            
            # Only filter by academic_year if provided
            if academic_year:
                query = query.eq('academic_year', academic_year)
                app.logger.info(f"Querying national distributions for cycle {cycle}, academic_year {academic_year}")
            else:
                # If no academic year specified, get the most recent data for this cycle
                app.logger.info(f"No academic year specified for national distributions, fetching most recent for cycle {cycle}")
                # First find the most recent academic year for this cycle
                recent_year_query = supabase_client.table('national_statistics')\
                    .select('academic_year')\
                    .eq('cycle', cycle)\
                    .order('academic_year', desc=True)\
                    .limit(1)\
                    .execute()
                
                if recent_year_query.data and recent_year_query.data[0]['academic_year']:
                    most_recent_year = recent_year_query.data[0]['academic_year']
                    query = query.eq('academic_year', most_recent_year)
                    app.logger.info(f"Using most recent academic year for national distributions: {most_recent_year}")
            
            national_dist_result = query.execute()
            
            if national_dist_result.data:
                national_distributions = {}
                for stat in national_dist_result.data:
                    if stat['element'] and stat['distribution']:
                        # Distribution is stored as JSONB, should be an array
                        element_key = stat['element'].lower()
                        # Ensure the distribution is an array of 10 values for 1-10 scale
                        dist_data = stat['distribution']
                        if isinstance(dist_data, list) and len(dist_data) == 10:
                            national_distributions[element_key] = dist_data
                        else:
                            app.logger.warning(f"Invalid distribution data for {element_key}: {dist_data}")
                
                # If we only have overall distribution, try to get individual element distributions from vespa_scores
                if len(national_distributions) == 1 and 'overall' in national_distributions:
                    app.logger.info("Only overall distribution found, calculating element distributions from all schools")
                    
                    # Get a sample of vespa_scores from all schools for distribution calculation
                    # We'll batch this to avoid huge queries
                    element_distributions = {elem: [0] * 10 for elem in ['vision', 'effort', 'systems', 'practice', 'attitude']}
                    
                    # Get sample of establishments to calculate from
                    est_result = supabase_client.table('establishments')\
                        .select('id')\
                        .limit(50)\
                        .execute()
                    
                    if est_result.data:
                        for est in est_result.data:
                            # First get students for this establishment
                            students_sample = supabase_client.table('students')\
                                .select('id')\
                                .eq('establishment_id', est['id'])\
                                .limit(100)\
                                .execute()
                            
                            if students_sample.data:
                                student_ids = [s['id'] for s in students_sample.data]
                                # Get vespa scores for these students
                                vespa_sample = supabase_client.table('vespa_scores')\
                                    .select('vision,effort,systems,practice,attitude')\
                                    .in_('student_id', student_ids)\
                                    .eq('cycle', cycle)\
                                    .limit(100)\
                                    .execute()
                                
                                if vespa_sample.data:
                                    for score in vespa_sample.data:
                                        for elem in ['vision', 'effort', 'systems', 'practice', 'attitude']:
                                            if score.get(elem) is not None:
                                                rounded_score = round(score[elem])
                                                if 1 <= rounded_score <= 10:
                                                    element_distributions[elem][rounded_score - 1] += 1
                        
                        # Add these to national_distributions
                        for elem, dist in element_distributions.items():
                            if sum(dist) > 0:  # Only add if we have data
                                national_distributions[elem] = dist
                                app.logger.info(f"Calculated distribution for {elem}: total={sum(dist)}")
                
                # Fallback: Use national_statistics means if available (for future when element-specific data exists)
                if (not comparison_national or all(v == 0 for v in comparison_national)) and national_dist_result.data:
                    app.logger.info(f"No data from current_school_averages, checking national_statistics as fallback")
                    for stat in national_dist_result.data:
                        if stat['element'] and stat['element'].lower() != 'overall' and stat.get('mean') is not None:
                            element_key = stat['element'].lower()
                            # Store the mean for use in comparison
                            if element_key in ['vision', 'effort', 'systems', 'practice', 'attitude']:
                                if element_key not in nat_stats_by_element or nat_stats_by_element[element_key] == 0:
                                    nat_stats_by_element[element_key] = float(stat['mean'])
                                    app.logger.info(f"Setting national {element_key} = {stat['mean']} from national_statistics (fallback)")
                    
                    # Recalculate comparison_national if we got new data
                    if nat_stats_by_element and any(v > 0 for v in nat_stats_by_element.values()):
                        comparison_national = []
                        for elem in ['vision', 'effort', 'systems', 'practice', 'attitude']:
                            national_score = round(nat_stats_by_element.get(elem, 0), 2)
                            comparison_national.append(national_score)
                        response_data['comparison']['national'] = comparison_national
                        app.logger.info(f"Updated comparison_national from national_statistics fallback: {comparison_national}")
                
                response_data['nationalDistributions'] = national_distributions
                app.logger.info(f"Returning national distributions for {len(national_distributions)} elements: {list(national_distributions.keys())}")
                app.logger.info(f"Sample national distribution: {list(national_distributions.values())[0] if national_distributions else 'None'}")
            else:
                app.logger.warning(f"No national distribution data found for cycle {cycle}, academic_year {academic_year}")
                # Return empty distributions so frontend knows they're missing
                response_data['nationalDistributions'] = {}
        except Exception as e:
            app.logger.error(f"Failed to fetch national distributions: {e}")
            # Ensure nationalDistributions is set even on error
            if 'nationalDistributions' not in response_data:
                response_data['nationalDistributions'] = {}
        
        # Log the complete response structure
        app.logger.info(f"Final response data keys: {list(response_data.keys())}")
        app.logger.info(f"Response vespaScores: {response_data.get('vespaScores', {})}")
        app.logger.info(f"Response comparison: {response_data.get('comparison', {})}")
        app.logger.info(f"Response has nationalDistributions: {'nationalDistributions' in response_data}")
        
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch school statistics: {e}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        raise ApiError(f"Failed to fetch school statistics: {str(e)}", 500)

@app.route('/api/qla', methods=['GET'])
def get_qla_data_query():
    """Get QLA data with comprehensive filtering and insights"""
    try:
        establishment_id = request.args.get('establishment_id')
        if not establishment_id:
            raise ApiError("establishment_id is required", 400)
            
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Convert establishment ID
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        if not establishment_uuid:
            raise ApiError(f"Establishment not found with ID: {establishment_id}", 404)
        
        # Get filter parameters - note camelCase from frontend
        cycle = request.args.get('cycle', type=int, default=1)
        academic_year = request.args.get('academic_year')  # Changed to snake_case for consistency
        year_group = request.args.get('yearGroup')
        group = request.args.get('group')
        faculty = request.args.get('faculty')
        student_id = request.args.get('studentId')
        
        app.logger.info(f"QLA endpoint called with establishment_id={establishment_id}, cycle={cycle}, academic_year={academic_year}")
        
        # Define insight configurations
        insight_configs = {
            'growth_mindset': {
                'title': 'Growth Mindset',
                'question_ids': ['q5', 'q26', 'q27', 'q16'],
                'icon': '🌱',
                'question': 'What percentage believe intelligence can be developed?'
            },
            'academic_momentum': {
                'title': 'Academic Momentum',
                'question_ids': ['q14', 'q16', 'q17', 'q9'],
                'icon': '🚀',
                'question': 'What percentage show strong drive and engagement?'
            },
            'vision_purpose': {
                'title': 'Vision & Purpose',
                'question_ids': ['q1', 'q3', 'q29'],
                'icon': '🎯',
                'question': 'What percentage have clear educational purpose?'
            },
            'study_strategies': {
                'title': 'Study Strategies',
                'question_ids': ['q7', 'q12', 'q15', 'q18'],
                'icon': '📚',
                'question': 'What percentage use effective study techniques?'
            },
            'exam_confidence': {
                'title': 'Exam Confidence',
                'question_ids': ['outcome_q_confident', 'q10', 'q28'],
                'icon': '⭐',
                'question': 'What percentage feel confident about exams?'
            },
            'organization_materials': {
                'title': 'Organization & Materials',
                'question_ids': ['q22', 'q18', 'q25'],
                'icon': '📦',
                'question': 'What percentage are well-organized?'
            },
            'resilience_factor': {
                'title': 'Resilience Factor',
                'question_ids': ['q13', 'q27', 'q8'],
                'icon': '💪',
                'question': 'What percentage show academic resilience?'
            },
            'stress_management': {
                'title': 'Stress Management',
                'question_ids': ['q20', 'q28', 'q24'],
                'icon': '😌',
                'question': 'What percentage handle pressure well?'
            },
            'support_help_seeking': {
                'title': 'Support & Help-Seeking',
                'question_ids': ['outcome_q_support', 'q24', 'q27'],
                'icon': '🤝',
                'question': 'What percentage feel supported and seek help?'
            },
            'time_management': {
                'title': 'Time Management',
                'question_ids': ['q2', 'q4', 'q11'],
                'icon': '⏰',
                'question': 'What percentage manage time effectively?'
            },
            'active_learning': {
                'title': 'Active Learning',
                'question_ids': ['q23', 'q19', 'q7'],
                'icon': '🎓',
                'question': 'What percentage engage in active learning?'
            },
            'revision_readiness': {
                'title': 'Revision Readiness',
                'question_ids': ['outcome_q_equipped', 'q7', 'q12', 'q18'],
                'icon': '📖',
                'question': 'What percentage feel equipped for revision challenges?'
            }
        }
        
        # Try question_statistics table first (more likely to have data)
        qla_query = supabase_client.table('question_statistics').select('*')\
            .eq('establishment_id', establishment_uuid)\
            .eq('cycle', cycle)
        
        if academic_year:
            # Convert academic year from frontend format (2025-26) to database format (2025/2026)
            formatted_year = convert_academic_year_format(academic_year, to_database=True)
            app.logger.info(f"Converting academic year from {academic_year} to {formatted_year}")
            qla_query = qla_query.eq('academic_year', formatted_year)
            
        qla_result = qla_query.execute()
        
        app.logger.info(f"question_statistics result count: {len(qla_result.data) if qla_result.data else 0}")
        if qla_result.data:
            app.logger.info(f"Sample question_statistics data: {qla_result.data[0] if qla_result.data else 'None'}")
        
        # If no data in question_statistics, try qla_question_performance
        if not qla_result.data:
            qla_query = supabase_client.table('qla_question_performance').select('*')\
                .eq('establishment_id', establishment_uuid)\
                .eq('cycle', cycle)
            
            if academic_year:
                # Convert academic year from frontend format (2025-26) to database format (2025/2026)
                formatted_year = convert_academic_year_format(academic_year, to_database=True)
                qla_query = qla_query.eq('academic_year', formatted_year)
                
            qla_result = qla_query.execute()
            app.logger.info(f"qla_question_performance result count: {len(qla_result.data) if qla_result.data else 0}")
        
        # FIX: If STILL no data in pre-aggregated tables, calculate from raw question_responses
        # This handles the case where statistics haven't been calculated yet for new academic years
        force_calculate_from_raw = not qla_result.data
        
        # If we have filters OR no pre-aggregated data, we need to calculate from raw data
        if year_group or group or faculty or student_id or force_calculate_from_raw:
            # Get filtered student IDs first
            students_query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)
            
            # DON'T filter by academic_year on students table - check VESPA data instead
            # if academic_year:
            #     students_query = students_query.eq('academic_year', academic_year)  # REMOVED - same bug
            
            if year_group:
                students_query = students_query.eq('year_group', year_group)
            if group:
                students_query = students_query.eq('group', group)
            if faculty:
                students_query = students_query.eq('faculty', faculty)
            if student_id:
                # Convert student ID if needed
                import uuid
                try:
                    uuid.UUID(student_id)
                    # It's already a UUID, use as is
                    students_query = students_query.eq('id', student_id)
                except ValueError:
                    # It's a Knack ID, need to convert
                    student_result = supabase_client.table('students').select('id').eq('knack_id', student_id).execute()
                    if student_result.data:
                        students_query = students_query.eq('id', student_result.data[0]['id'])
            
            students_result = students_query.execute()
            student_ids = [s['id'] for s in students_result.data]
            
            # NEW: Filter by who has VESPA data for the selected academic year
            if academic_year:
                students_with_vespa = []
                
                # Check in batches who has VESPA data for this year
                for i in range(0, len(student_ids), 50):
                    batch_ids = student_ids[i:i+50]
                    
                    # Check which students have VESPA data for the selected year
                    vespa_check = supabase_client.table('vespa_scores')\
                        .select('student_id')\
                        .in_('student_id', batch_ids)\
                        .eq('academic_year', academic_year)\
                        .eq('cycle', cycle)\
                        .limit(1000)\
                        .execute()
                    
                    students_with_vespa_ids = set(v['student_id'] for v in vespa_check.data)
                    
                    # Keep only students who have VESPA data
                    students_with_vespa.extend([sid for sid in batch_ids if sid in students_with_vespa_ids])
                
                student_ids = students_with_vespa
                app.logger.info(f"QLA: After academic year filter: {len(student_ids)} students have data for {academic_year}")
            
            # Get question responses for filtered students
            if student_ids:
                # Process in batches
                BATCH_SIZE = 50
                filtered_responses = []
                
                for i in range(0, len(student_ids), BATCH_SIZE):
                    batch_ids = student_ids[i:i + BATCH_SIZE]
                    responses_query = supabase_client.table('question_responses')\
                        .select('question_id, response_value')\
                        .in_('student_id', batch_ids)\
                        .eq('cycle', cycle)
                    
                    # CRITICAL FIX: Add academic_year filter if provided
                    if academic_year:
                        responses_query = responses_query.eq('academic_year', formatted_year)
                    
                    responses_result = responses_query.execute()
                    filtered_responses.extend(responses_result.data)
                
                # Calculate statistics for filtered data
                question_stats = {}
                for response in filtered_responses:
                    q_id = response['question_id']
                    if q_id not in question_stats:
                        question_stats[q_id] = {
                            'responses': [],
                            'distribution': [0] * 5  # 1-5 scale
                        }
                    if response['response_value'] is not None:
                        question_stats[q_id]['responses'].append(response['response_value'])
                        if 1 <= response['response_value'] <= 5:
                            question_stats[q_id]['distribution'][response['response_value'] - 1] += 1
                
                # Calculate mean, std_dev for each question
                import statistics
                qla_data_filtered = []
                for q_id, stats in question_stats.items():
                    if stats['responses']:
                        mean = statistics.mean(stats['responses'])
                        std_dev = statistics.stdev(stats['responses']) if len(stats['responses']) > 1 else 0
                        qla_data_filtered.append({
                            'question_id': q_id,
                            'mean': mean,
                            'std_dev': std_dev,
                            'count': len(stats['responses']),
                            'distribution': stats['distribution']
                        })
                
                # Use filtered data instead of pre-aggregated
                qla_data = qla_data_filtered
            else:
                qla_data = []
        else:
            # Use pre-aggregated data from qla_question_performance
            qla_data = qla_result.data
        
        # Get questions metadata
        questions_result = supabase_client.table('questions').select('*').eq('is_active', True).execute()
        questions_by_id = {q['question_id']: q for q in questions_result.data}
        
        # Sort by mean score
        sorted_stats = sorted(qla_data, key=lambda x: float(x.get('mean', 0)) if x.get('mean') else 0)
        
        # Get top 5 and bottom 5
        if len(sorted_stats) >= 10:
            bottom_5 = sorted_stats[:5]
            top_5 = sorted_stats[-5:][::-1]  # Reverse to get highest first
        else:
            half = len(sorted_stats) // 2
            bottom_5 = sorted_stats[:half]
            top_5 = sorted_stats[half:][::-1]
        
        # Format high/low questions
        top_questions = []
        for i, stat in enumerate(top_5):
            question_info = questions_by_id.get(stat['question_id'], {})
            top_questions.append({
                'id': stat['question_id'],
                'rank': i + 1,
                'text': question_info.get('question_text', f"Question {stat['question_id']}"),
                'score': float(stat['mean']) if stat.get('mean') else 0,
                'n': stat.get('count', 0),
                'std_dev': float(stat['std_dev']) if stat.get('std_dev') else 0,
                'distribution': stat.get('distribution', []),
                'count': stat.get('count', 0),
                'mode': stat.get('mode', 0)
            })
        
        bottom_questions = []
        for i, stat in enumerate(bottom_5):
            question_info = questions_by_id.get(stat['question_id'], {})
            bottom_questions.append({
                'id': stat['question_id'],
                'rank': i + 1,
                'text': question_info.get('question_text', f"Question {stat['question_id']}"),
                'score': float(stat['mean']) if stat.get('mean') else 0,
                'n': stat.get('count', 0),
                'std_dev': float(stat['std_dev']) if stat.get('std_dev') else 0,
                'distribution': stat.get('distribution', []),
                'count': stat.get('count', 0),
                'mode': stat.get('mode', 0)
            })
        
        # Calculate insights
        insights = []
        question_stats_by_id = {stat['question_id']: stat for stat in qla_data}
        
        # Check if this is an individual student (only one student in results)
        is_individual_student = student_id is not None
        
        for insight_id, config in insight_configs.items():
            # Calculate percentage agreement (scores 4-5) or average for individual
            total_responses_sum = 0
            agreement_count = 0
            student_count = 0
            scores_sum = 0
            scores_count = 0
            
            for q_id in config['question_ids']:
                if q_id in question_stats_by_id:
                    stat = question_stats_by_id[q_id]
                    distribution = stat.get('distribution', [])
                    if distribution and len(distribution) >= 5:
                        # Sum responses for scores 4 and 5
                        agreement_count += distribution[3] + distribution[4]  # indices 3,4 for scores 4,5
                        total_responses_sum += sum(distribution)
                        # Use the count from the first question as the student count
                        if student_count == 0:
                            student_count = stat.get('count', 0)
                    
                    # For individual students, also calculate average score
                    if is_individual_student and stat.get('mean'):
                        scores_sum += stat['mean']
                        scores_count += 1
            
            if is_individual_student and scores_count > 0:
                # For individual students, convert average score to percentage
                # Score 1 = 0%, Score 2 = 25%, Score 3 = 50%, Score 4 = 75%, Score 5 = 100%
                average_score = scores_sum / scores_count
                # Convert 1-5 scale to 0-100% scale: (score - 1) * 25
                percentage_from_score = (average_score - 1) * 25
                
                insights.append({
                    'id': insight_id,
                    'title': config['title'],
                    'percentageAgreement': round(percentage_from_score, 1),
                    'questionIds': config['question_ids'],
                    'icon': config['icon'],
                    'totalResponses': 1,
                    'question': config.get('question', f'What percentage show {config["title"].lower()}?')
                })
            else:
                # For groups, show percentage agreement as before
                percentage_agreement = (agreement_count / total_responses_sum * 100) if total_responses_sum > 0 else 0
                
                insights.append({
                    'id': insight_id,
                    'title': config['title'],
                    'percentageAgreement': round(percentage_agreement, 1),
                    'questionIds': config['question_ids'],
                    'icon': config['icon'],
                    'totalResponses': student_count,  # Use student count instead of total responses
                    'question': config.get('question', f'What percentage show {config["title"].lower()}?')
                })
        
        # Sort insights by percentage agreement (high to low)
        insights.sort(key=lambda x: x['percentageAgreement'], reverse=True)
        
        # Prepare response
        response_data = {
            'highLowQuestions': {
                'topQuestions': top_questions,
                'bottomQuestions': bottom_questions
            },
            'insights': insights,
            'metadata': {
                'totalQuestions': len(qla_data),
                'cycle': cycle,
                'filters': {
                    'yearGroup': year_group,
                    'group': group,
                    'faculty': faculty,
                    'studentId': student_id,
                    'academicYear': academic_year
                }
            }
        }
        
        app.logger.info(f"QLA data retrieved successfully for establishment {establishment_id}")
        app.logger.info(f"QLA response - top questions count: {len(top_questions)}, bottom questions count: {len(bottom_questions)}, insights count: {len(insights)}")
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch QLA data: {e}")
        raise ApiError(f"Failed to fetch QLA data: {str(e)}", 500)

@app.route('/api/student-responses', methods=['GET'])
def get_student_responses():
    """Get all question responses for an individual student"""
    try:
        student_id = request.args.get('student_id')
        cycle = request.args.get('cycle', type=int, default=1)
        
        if not student_id:
            raise ApiError("studentId is required", 400)
            
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Convert student ID if needed
        import uuid
        student_uuid = None
        try:
            uuid.UUID(student_id)
            student_uuid = student_id
        except ValueError:
            # It's a Knack ID, need to convert
            student_result = supabase_client.table('students').select('id, name, email').eq('knack_id', student_id).execute()
            if student_result.data:
                student_uuid = student_result.data[0]['id']
                student_info = student_result.data[0]
            else:
                raise ApiError(f"Student not found with ID: {student_id}", 404)
        
        if not student_uuid:
            raise ApiError(f"Could not convert student ID: {student_id}", 400)
            
        # Get student info if we don't have it
        if 'student_info' not in locals():
            student_result = supabase_client.table('students').select('name, email').eq('id', student_uuid).execute()
            if student_result.data:
                student_info = student_result.data[0]
            else:
                student_info = {'name': 'Unknown', 'email': ''}
        
        # Get all question responses for this student and cycle
        responses_result = supabase_client.table('question_responses')\
            .select('question_id, response_value, created_at')\
            .eq('student_id', student_uuid)\
            .eq('cycle', cycle)\
            .execute()
            
        # Get questions metadata
        questions_result = supabase_client.table('questions')\
            .select('question_id, question_text, vespa_category')\
            .eq('is_active', True)\
            .execute()
        
        questions_by_id = {q['question_id']: q for q in questions_result.data}
        
        # Format responses with question text and RAG rating
        formatted_responses = []
        for response in responses_result.data:
            question_info = questions_by_id.get(response['question_id'], {})
            
            # Determine RAG rating
            score = response['response_value']
            if score:
                if score >= 4:
                    rag_rating = 'green'
                elif score == 3:
                    rag_rating = 'amber'
                else:
                    rag_rating = 'red'
            else:
                rag_rating = 'none'
            
            formatted_responses.append({
                'questionId': response['question_id'],
                'questionText': question_info.get('question_text', f"Question {response['question_id']}"),
                'category': question_info.get('vespa_category', 'General'),
                'responseValue': score,
                'ragRating': rag_rating,
                'timestamp': response.get('created_at', '')
            })
        
        # Sort by question ID
        formatted_responses.sort(key=lambda x: x['questionId'])
        
        # Group by category
        categories = {}
        for response in formatted_responses:
            cat = response['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(response)
        
        return jsonify({
            'student': {
                'name': student_info.get('name', 'Unknown'),
                'email': student_info.get('email', ''),
                'id': student_uuid
            },
            'responses': formatted_responses,
            'categorizedResponses': categories,
            'cycle': cycle,
            'totalQuestions': len(formatted_responses),
            'summary': {
                'green': len([r for r in formatted_responses if r['ragRating'] == 'green']),
                'amber': len([r for r in formatted_responses if r['ragRating'] == 'amber']),
                'red': len([r for r in formatted_responses if r['ragRating'] == 'red']),
                'none': len([r for r in formatted_responses if r['ragRating'] == 'none'])
            }
        })
        
    except Exception as e:
        app.logger.error(f"Failed to fetch student responses: {e}")
        raise ApiError(f"Failed to fetch student responses: {str(e)}", 500)

@app.route('/api/word-cloud', methods=['GET'])
def get_word_cloud_data():
    """Get word cloud data from student comments"""
    try:
        establishment_id = request.args.get('establishment_id')
        if not establishment_id:
            raise ApiError("establishment_id is required", 400)
            
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        cycle = request.args.get('cycle', type=int, default=1)
        
        # For now, return mock data since comments aren't synced yet
        # TODO: Implement actual comment word cloud from Supabase
        
        mock_words = [
            {"text": "supportive", "size": 45, "count": 89},
            {"text": "helpful", "size": 40, "count": 76},
            {"text": "understanding", "size": 35, "count": 65},
            {"text": "challenging", "size": 30, "count": 54},
            {"text": "engaging", "size": 28, "count": 48},
            {"text": "improvement", "size": 25, "count": 41},
            {"text": "excellent", "size": 22, "count": 35}
        ]
        
        return jsonify(mock_words)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch word cloud data: {e}")
        raise ApiError(f"Failed to fetch word cloud data: {str(e)}", 500)

@app.route('/api/comment-insights', methods=['GET'])
def get_comment_insights():
    """Get comment insights"""
    try:
        establishment_id = request.args.get('establishment_id')
        if not establishment_id:
            raise ApiError("establishment_id is required", 400)
            
        # Return mock data for now
        return jsonify({
            'themes': [
                {
                    'theme': 'Teaching Quality',
                    'count': 45,
                    'sentiment': 'positive',
                    'examples': ['Great teaching methods', 'Very supportive teachers']
                },
                {
                    'theme': 'Resources',
                    'count': 32,
                    'sentiment': 'mixed',
                    'examples': ['Good online resources', 'Need more textbooks']
                }
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Failed to fetch comment insights: {e}")
        raise ApiError(f"Failed to fetch comment insights: {str(e)}", 500)

# ===== END FIXED ENDPOINTS =====



@app.route('/api/staff-admin/<email>', methods=['GET'])
@cached(ttl_key='staff_admin', ttl_seconds=600)
def get_staff_admin_by_email(email):
    """Get Staff Admin record by email from Supabase"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
        
        # Get staff admin by email
        result = supabase_client.table('staff_admins').select('*').eq('email', email).execute()
        
        if not result.data:
            return jsonify({'error': 'Staff Admin not found'}), 404
        
        staff_admin = result.data[0]
        
        # Format response to match dashboard expectations
        response = {
            'id': staff_admin['knack_id'],  # Use knack_id for compatibility
            'email': staff_admin['email'],
            'name': staff_admin['name'],
            'field_110_raw': []  # Establishment connection
        }
        
        # If there's an establishment_id, format it as Knack expects
        if staff_admin.get('establishment_id'):
            # Get establishment details
            est_result = supabase_client.table('establishments').select('*').eq('id', staff_admin['establishment_id']).execute()
            if est_result.data:
                establishment = est_result.data[0]
                response['field_110_raw'] = [{
                    'id': establishment['knack_id'],  # Use knack_id for compatibility
                    'identifier': establishment['name']
                }]
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"Failed to fetch staff admin: {e}")
        raise ApiError(f"Failed to fetch staff admin: {str(e)}", 500)

# ===== COMPARATIVE REPORT ENDPOINT =====

@app.route('/api/comparative-report', methods=['POST', 'OPTIONS'])
def generate_comparative_report():
    """Generate an interactive HTML comparative report that can be edited in-browser"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, X-Knack-Application-Id, X-Knack-REST-API-Key, x-knack-application-id, x-knack-rest-api-key')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        if not data:
            raise ApiError("Missing request body", 400)
        
        # Extract configuration
        establishment_id = data.get('establishmentId')
        establishment_name = data.get('establishmentName', 'Unknown School')
        report_type = data.get('reportType')
        config = data.get('config', {})
        filters = data.get('filters', {})
        
        # Extract context fields
        organizational_context = config.get('organizationalContext', '')
        specific_questions = config.get('specificQuestions', '')
        historical_context = config.get('historicalContext', '')
        
        # Extract branding
        establishment_logo_url = config.get('establishmentLogoUrl', '')
        primary_color = config.get('primaryColor', '#667eea')
        
        app.logger.info(f"Generating interactive HTML report for {establishment_name}")
        app.logger.info(f"Report type: {report_type}")
        app.logger.info(f"Has context: {bool(organizational_context)}")
        
        # Use data passed from frontend if available, otherwise fetch from Supabase
        frontend_data = data.get('data', {})
        app.logger.info(f"Frontend data keys: {frontend_data.keys() if frontend_data else 'No frontend data'}")
        app.logger.info(f"Frontend vespaScores: {frontend_data.get('vespaScores', {})}")
        
        # Always fetch fresh data from Supabase for accurate comparison
        app.logger.info(f"Fetching fresh data from Supabase for establishment: {establishment_id}")
        comparison_data = fetch_comparison_data(
            establishment_id, 
            report_type, 
            config,
            filters
        )
        
        app.logger.info(f"Fetched comparison data keys: {comparison_data.keys() if comparison_data else 'No data fetched'}")
        
        # Log the actual data values
        for key, value in comparison_data.items():
            if isinstance(value, dict) and 'mean' in value:
                app.logger.info(f"Data for {key}: mean={value.get('mean')}, count={value.get('count')}")
        
        # Generate AI insights with context
        ai_insights = generate_contextual_insights(
            comparison_data, 
            organizational_context,
            specific_questions,
            historical_context,
            report_type,
            establishment_name
        )
        
        # Create interactive HTML report (not PDF)
        html_content = create_interactive_html_report(
            establishment_name,
            establishment_logo_url,
            primary_color,
            comparison_data,
            ai_insights,
            config,
            report_type
        )
        
        # Return HTML content that can be displayed and edited
        return jsonify({
            'success': True,
            'html': html_content,
            'data': comparison_data,
            'insights': ai_insights
        })
        
    except Exception as e:
        app.logger.error(f"Failed to generate comparative report: {e}")
        traceback.print_exc()
        raise ApiError(f"Report generation failed: {str(e)}", 500)

def process_frontend_data(frontend_data, report_type, config):
    """Process data from frontend dashboard for report generation"""
    try:
        app.logger.info(f"Processing frontend data for report type: {report_type}")
        app.logger.info(f"Frontend data keys: {frontend_data.keys()}")
        
        statistics = frontend_data.get('statistics', {})
        qla_data = frontend_data.get('qlaData', {})
        
        if report_type == 'cycle_vs_cycle':
            # Extract cycle data from statistics
            cycles = config.get('cycles', ['Cycle 1', 'Cycle 2'])
            data = {}
            
            # Get VESPA scores for each cycle
            vespa_scores = statistics.get('vespaScores', {})
            comparison = statistics.get('comparison', {})
            
            for i, cycle in enumerate(cycles):
                cycle_num = int(cycle.split()[-1]) if 'Cycle' in cycle else i + 1
                cycle_key = f'cycle_{cycle_num}'
                
                # Use comparison data if available
                if comparison and 'school' in comparison:
                    school_data = comparison['school']
                    if isinstance(school_data, list) and len(school_data) > i:
                        data[cycle_key] = {
                            'mean': school_data[i],
                            'vespa_breakdown': {
                                'vision': vespa_scores.get('vision', 0),
                                'effort': vespa_scores.get('effort', 0),
                                'systems': vespa_scores.get('systems', 0),
                                'practice': vespa_scores.get('practice', 0),
                                'attitude': vespa_scores.get('attitude', 0)
                            },
                            'count': statistics.get('totalResponses', 0)
                        }
                
            app.logger.info(f"Processed cycle data: {data}")
            return data
            
        elif report_type == 'year_vs_year':
            # Process year group comparison
            year_groups = config.get('yearGroups', [])
            data = {}
            
            for year_group in year_groups:
                # This would need actual year group data from statistics
                data[year_group] = {
                    'mean': statistics.get('averageScore', 0),
                    'count': statistics.get('totalResponses', 0),
                    'vespa_breakdown': statistics.get('vespaScores', {})
                }
            
            return data
            
        elif report_type == 'group_vs_group':
            # Process group comparison
            groups = config.get('groups', [])
            data = {}
            
            for group in groups:
                # This would need actual group data
                data[group] = {
                    'mean': statistics.get('averageScore', 0),
                    'count': statistics.get('totalResponses', 0)
                }
            
            return data
            
        else:
            # Default: return statistics as-is
            return {
                'statistics': statistics,
                'qla': qla_data
            }
            
    except Exception as e:
        app.logger.error(f"Error processing frontend data: {e}")
        return {}

def fetch_comparison_data(establishment_id, report_type, config, filters):
    """Fetch data from comparative_metrics view or raw tables - Enhanced with academic year support"""
    try:
        if not SUPABASE_ENABLED:
            raise ApiError("Supabase not configured", 503)
            
        # Log the original establishment ID
        app.logger.info(f"Original establishment_id: {establishment_id}")
        
        # Convert Knack ID to UUID if needed
        if establishment_id and not establishment_id.startswith('00000000'):
            converted_id = convert_knack_id_to_uuid(establishment_id)
            app.logger.info(f"Converted {establishment_id} to {converted_id}")
            establishment_id = converted_id
        
        app.logger.info(f"Final establishment_id to use: {establishment_id}")
        
        # Import QLA module
        from qla_analysis import fetch_question_level_data
        
        # Get current academic year if not specified
        # Default to 2024/2025 which has data
        current_academic_year = config.get('academicYear', '2024/2025')
        app.logger.info(f"Using academic year: {current_academic_year}")
            
        if report_type == 'cycle_vs_cycle':
            # Compare cycles within same or different academic years
            cycle1 = int(config.get('cycle1', 1))
            cycle2 = int(config.get('cycle2', 2))
            academic_year1 = config.get('academicYear1', current_academic_year)
            academic_year2 = config.get('academicYear2', current_academic_year)
            
            data = {}
            
            # Fetch data for cycle 1
            data[f'cycle_{cycle1}'] = fetch_cycle_data(
                establishment_id, cycle1, academic_year1
            )
            
            # Fetch data for cycle 2
            data[f'cycle_{cycle2}'] = fetch_cycle_data(
                establishment_id, cycle2, academic_year2
            )
            
            # Add QLA data
            data['qla_data'] = fetch_question_level_data(
                supabase_client, establishment_id, 'cycle_vs_cycle', 
                {'cycle1': cycle1, 'cycle2': cycle2, 'academicYear': current_academic_year}
            )
            
            return data
            
        elif report_type == 'year_group_vs_year_group':
            # Compare year groups
            year_group1 = config.get('yearGroup1')
            year_group2 = config.get('yearGroup2')
            cycle = int(config.get('cycle', 1))
            academic_year = config.get('academicYear', current_academic_year)
            
            data = {}
            
            # Fetch data for each year group
            data[f'year_{year_group1}'] = fetch_year_group_data(
                establishment_id, year_group1, cycle, academic_year
            )
            data[f'year_{year_group2}'] = fetch_year_group_data(
                establishment_id, year_group2, cycle, academic_year
            )
            
            # Add QLA data
            data['qla_data'] = fetch_question_level_data(
                supabase_client, establishment_id, 'year_group_vs_year_group',
                {'yearGroup1': year_group1, 'yearGroup2': year_group2, 'cycle': cycle, 'academicYear': academic_year}
            )
            
            return data
            
        elif report_type == 'faculty_vs_faculty':
            # Compare faculties
            faculty1 = config.get('faculty1')
            faculty2 = config.get('faculty2')
            cycle = int(config.get('cycle', 1))
            academic_year = config.get('academicYear', current_academic_year)
            
            data = {}
            
            app.logger.info(f"Comparing faculties: {faculty1} vs {faculty2}")
            
            # Fetch data for each faculty
            data[f'faculty_{faculty1}'] = fetch_faculty_data(
                establishment_id, faculty1, cycle, academic_year
            )
            data[f'faculty_{faculty2}'] = fetch_faculty_data(
                establishment_id, faculty2, cycle, academic_year
            )
            
            # Add QLA data if needed
            data['qla_data'] = fetch_question_level_data(
                supabase_client, establishment_id, 'faculty_vs_faculty',
                {'faculty1': faculty1, 'faculty2': faculty2, 'cycle': cycle, 'academicYear': academic_year}
            )
            
            return data
            
        elif report_type == 'faculty_progression':
            # Track a single faculty's progression over time
            faculty = config.get('faculty')
            academic_years = config.get('academicYears', [current_academic_year])
            cycles = config.get('cycles', [1, 2, 3])
            
            data = {}
            
            app.logger.info(f"Tracking faculty {faculty} progression across years: {academic_years}")
            
            # Fetch data for each year/cycle combination
            for year in academic_years:
                for cycle in cycles:
                    key = f'faculty_{faculty}_year_{year.replace("/", "_")}_cycle_{cycle}'
                    data[key] = fetch_faculty_data(
                        establishment_id, faculty, cycle, year
                    )
            
            return data
            
        elif report_type == 'academic_year_vs_academic_year':
            # Compare across academic years
            year1 = config.get('academicYear1')
            year2 = config.get('academicYear2')
            year_group = config.get('yearGroup')  # Optional
            cycle = int(config.get('cycle', 1))
            
            data = {}
            
            # Fetch data for each academic year
            data[f'year_{year1.replace("/", "_")}'] = fetch_academic_year_data(
                establishment_id, year1, year_group, cycle
            )
            data[f'year_{year2.replace("/", "_")}'] = fetch_academic_year_data(
                establishment_id, year2, year_group, cycle
            )
            
            # Add QLA data
            data['qla_data'] = fetch_question_level_data(
                supabase_client, establishment_id, 'academic_year_vs_academic_year',
                {'academicYear1': year1, 'academicYear2': year2, 'yearGroup': year_group, 'cycle': cycle}
            )
            
            return data
            
        elif report_type == 'hybrid':
            # Hybrid report - combination of cycle and year group/group comparison
            cycle1 = int(config.get('cycle1', 1))
            cycle2 = int(config.get('cycle2', 2))
            dimension = config.get('hybridDimension', 'year_group')
            item1 = config.get('hybridItem1')
            item2 = config.get('hybridItem2')
            academic_year = config.get('academicYear', current_academic_year)
            
            data = {}
            
            # Fetch primary comparison (cycles)
            data[f'cycle_{cycle1}'] = fetch_cycle_data(
                establishment_id, cycle1, academic_year
            )
            data[f'cycle_{cycle2}'] = fetch_cycle_data(
                establishment_id, cycle2, academic_year
            )
            
            # Fetch secondary comparison based on dimension
            if dimension == 'year_group' and item1 and item2:
                data[f'year_{item1}_cycle_{cycle1}'] = fetch_year_group_data(
                    establishment_id, item1, cycle1, academic_year
                )
                data[f'year_{item2}_cycle_{cycle2}'] = fetch_year_group_data(
                    establishment_id, item2, cycle2, academic_year
                )
            
            # Add QLA if needed
            if any(v for v in data.values()):
                data['qla_data'] = fetch_question_level_data(
                    supabase_client, establishment_id, 'hybrid',
                    config
                )
            
            return data
            
        elif report_type == 'cycle_progression' or report_type == 'progress':
            cycles = config.get('cycles', [1, 2, 3])
            
            # Query data for each cycle
            data = {}
            for cycle in cycles:
                # Get vespa_scores for this cycle
                students_result = supabase_client.table('students')\
                    .select('id')\
                    .eq('establishment_id', establishment_id)\
                    .execute()
                
                if students_result.data:
                    student_ids = [s['id'] for s in students_result.data]
                    
                    # Batch fetch vespa scores
                    all_scores = []
                    BATCH_SIZE = 50
                    for i in range(0, len(student_ids), BATCH_SIZE):
                        batch_ids = student_ids[i:i + BATCH_SIZE]
                        batch_result = supabase_client.table('vespa_scores')\
                            .select('*')\
                            .in_('student_id', batch_ids)\
                            .eq('cycle', cycle)\
                            .execute()
                        if batch_result.data:
                            all_scores.extend(batch_result.data)
                    
                    if all_scores:
                        # Calculate statistics
                        overall_scores = [s['overall'] for s in all_scores if s.get('overall') is not None]
                        vision_scores = [s['vision'] for s in all_scores if s.get('vision') is not None]
                        effort_scores = [s['effort'] for s in all_scores if s.get('effort') is not None]
                        systems_scores = [s['systems'] for s in all_scores if s.get('systems') is not None]
                        practice_scores = [s['practice'] for s in all_scores if s.get('practice') is not None]
                        attitude_scores = [s['attitude'] for s in all_scores if s.get('attitude') is not None]
                        
                        data[f'cycle_{cycle}'] = {
                            'mean': float(np.mean(overall_scores)) if overall_scores else 0,
                            'std': float(np.std(overall_scores)) if overall_scores else 0,
                            'count': len(overall_scores),
                            'vespa_breakdown': {
                                'vision': float(np.mean(vision_scores)) if vision_scores else 0,
                                'effort': float(np.mean(effort_scores)) if effort_scores else 0,
                                'systems': float(np.mean(systems_scores)) if systems_scores else 0,
                                'practice': float(np.mean(practice_scores)) if practice_scores else 0,
                                'attitude': float(np.mean(attitude_scores)) if attitude_scores else 0
                            },
                            'raw_data': all_scores[:10]  # Sample for debugging
                        }
            
            return data
            
        elif report_type == 'group_comparison':
            dimension = config.get('groupDimension', 'year_group')
            groups = config.get('groups', [])
            
            data = {}
            for group in groups:
                # Get students in this group
                students_query = supabase_client.table('students')\
                    .select('id')\
                    .eq('establishment_id', establishment_id)
                
                if dimension == 'year_group':
                    students_query = students_query.eq('year_group', group)
                elif dimension == 'faculty':
                    students_query = students_query.eq('faculty', group)
                elif dimension == 'group':
                    students_query = students_query.eq('group', group)
                    
                students_result = students_query.execute()
                
                if students_result.data:
                    student_ids = [s['id'] for s in students_result.data]
                    
                    # Get vespa scores for these students
                    all_scores = []
                    BATCH_SIZE = 50
                    for i in range(0, len(student_ids), BATCH_SIZE):
                        batch_ids = student_ids[i:i + BATCH_SIZE]
                        batch_result = supabase_client.table('vespa_scores')\
                            .select('*')\
                            .in_('student_id', batch_ids)\
                            .execute()
                        if batch_result.data:
                            all_scores.extend(batch_result.data)
                    
                    if all_scores:
                        overall_scores = [s['overall'] for s in all_scores if s.get('overall') is not None]
                        data[group] = {
                            'mean': float(np.mean(overall_scores)) if overall_scores else 0,
                            'std': float(np.std(overall_scores)) if overall_scores else 0,
                            'count': len(overall_scores),
                            'raw_data': all_scores[:10]
                        }
            
            return data
            
        else:
            # Default/custom report type
            return {}
            
    except Exception as e:
        app.logger.error(f"Failed to fetch comparison data: {e}")
        traceback.print_exc()
        return {}

def fetch_cycle_data(establishment_id, cycle, academic_year):
    """Fetch VESPA data for a specific cycle and academic year"""
    try:
        app.logger.info(f"fetch_cycle_data called: establishment={establishment_id}, cycle={cycle}, year={academic_year}")
        
        # Get students for this establishment
        students_query = supabase_client.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)
        
        # Also filter students by academic year if provided
        if academic_year:
            students_query = students_query.eq('academic_year', academic_year)
        
        students_result = students_query.execute()
        student_ids = [s['id'] for s in students_result.data] if students_result.data else []
        
        app.logger.info(f"Found {len(student_ids)} students for establishment {establishment_id}")
        
        if not student_ids:
            app.logger.warning(f"No students found for establishment {establishment_id}")
            return {'mean': 0, 'std': 0, 'count': 0, 'vespa_breakdown': {}, 'academic_year': academic_year}
        
        # Get vespa scores for these students
        scores = []
        BATCH_SIZE = 50
        
        for i in range(0, len(student_ids), BATCH_SIZE):
            batch_ids = student_ids[i:i + BATCH_SIZE]
            
            # Build query for this batch
            vespa_query = supabase_client.table('vespa_scores')\
                .select('*')\
                .in_('student_id', batch_ids)\
                .eq('cycle', cycle)
            
            # Add academic year filter if provided
            if academic_year:
                vespa_query = vespa_query.eq('academic_year', academic_year)
            
            batch_result = vespa_query.execute()
            
            if batch_result.data:
                scores.extend(batch_result.data)
                app.logger.info(f"Batch {i//BATCH_SIZE + 1}: Found {len(batch_result.data)} scores")
        
        app.logger.info(f"Total vespa_scores found: {len(scores)} for cycle {cycle}, year {academic_year}")
        
        if scores:
            # Calculate statistics
            overall_scores = [s['overall'] for s in scores if s.get('overall') is not None]
            vision_scores = [s['vision'] for s in scores if s.get('vision') is not None]
            effort_scores = [s['effort'] for s in scores if s.get('effort') is not None]
            systems_scores = [s['systems'] for s in scores if s.get('systems') is not None]
            practice_scores = [s['practice'] for s in scores if s.get('practice') is not None]
            attitude_scores = [s['attitude'] for s in scores if s.get('attitude') is not None]
            
            return {
                'mean': float(np.mean(overall_scores)) if overall_scores else 0,
                'std': float(np.std(overall_scores)) if overall_scores else 0,
                'count': len(overall_scores),
                'vespa_breakdown': {
                    'vision': float(np.mean(vision_scores)) if vision_scores else 0,
                    'effort': float(np.mean(effort_scores)) if effort_scores else 0,
                    'systems': float(np.mean(systems_scores)) if systems_scores else 0,
                    'practice': float(np.mean(practice_scores)) if practice_scores else 0,
                    'attitude': float(np.mean(attitude_scores)) if attitude_scores else 0
                },
                'academic_year': academic_year
            }
        else:
            return {
                'mean': 0,
                'std': 0,
                'count': 0,
                'vespa_breakdown': {},
                'academic_year': academic_year
            }
            
    except Exception as e:
        app.logger.error(f"Failed to fetch cycle data: {e}")
        app.logger.error(f"Error details: {traceback.format_exc()}")
        return {
            'mean': 0,
            'std': 0,
            'count': 0,
            'vespa_breakdown': {},
            'academic_year': academic_year,
            'error': str(e)
        }

def fetch_faculty_data(establishment_id, faculty, cycle, academic_year):
    """Fetch VESPA data for a specific faculty"""
    try:
        app.logger.info(f"fetch_faculty_data called: establishment={establishment_id}, faculty={faculty}, cycle={cycle}, year={academic_year}")
        
        # Get students for this faculty
        students_query = supabase_client.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)\
            .eq('faculty', faculty)
        
        # Filter by academic year if provided
        if academic_year:
            students_query = students_query.eq('academic_year', academic_year)
            
        students_result = students_query.execute()
        student_ids = [s['id'] for s in students_result.data] if students_result.data else []
        
        app.logger.info(f"Found {len(student_ids)} students in faculty {faculty}")
        
        if not student_ids:
            return {'mean': 0, 'std': 0, 'count': 0, 'vespa_breakdown': {}, 'faculty': faculty}
        
        # Get vespa scores
        vespa_query = supabase_client.table('vespa_scores')\
            .select('*')\
            .in_('student_id', student_ids)\
            .eq('cycle', cycle)
        
        if academic_year:
            vespa_query = vespa_query.eq('academic_year', academic_year)
            
        vespa_result = vespa_query.execute()
        scores = vespa_result.data if vespa_result.data else []
        
        app.logger.info(f"Found {len(scores)} scores for faculty {faculty}")
        
        if scores:
            # Calculate statistics
            overall_scores = [s['overall'] for s in scores if s.get('overall') is not None]
            
            return {
                'mean': float(np.mean(overall_scores)) if overall_scores else 0,
                'std': float(np.std(overall_scores)) if overall_scores else 0,
                'count': len(overall_scores),
                'vespa_breakdown': {
                    'vision': float(np.mean([s['vision'] for s in scores if s.get('vision') is not None])) if scores else 0,
                    'effort': float(np.mean([s['effort'] for s in scores if s.get('effort') is not None])) if scores else 0,
                    'systems': float(np.mean([s['systems'] for s in scores if s.get('systems') is not None])) if scores else 0,
                    'practice': float(np.mean([s['practice'] for s in scores if s.get('practice') is not None])) if scores else 0,
                    'attitude': float(np.mean([s['attitude'] for s in scores if s.get('attitude') is not None])) if scores else 0
                },
                'faculty': faculty,
                'academic_year': academic_year
            }
        else:
            return {'mean': 0, 'std': 0, 'count': 0, 'vespa_breakdown': {}, 'faculty': faculty}
            
    except Exception as e:
        app.logger.error(f"Failed to fetch faculty data: {e}")
        return {}

def fetch_year_group_data(establishment_id, year_group, cycle, academic_year):
    """Fetch VESPA data for a specific year group"""
    try:
        # Get students for this year group
        students_query = supabase_client.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)\
            .eq('year_group', year_group)
        
        # Filter by academic year if provided
        if academic_year:
            students_query = students_query.eq('academic_year', academic_year)
            
        students_result = students_query.execute()
        student_ids = [s['id'] for s in students_result.data] if students_result.data else []
        
        if not student_ids:
            return {'mean': 0, 'std': 0, 'count': 0, 'vespa_breakdown': {}}
        
        # Get vespa scores
        vespa_query = supabase_client.table('vespa_scores')\
            .select('*')\
            .in_('student_id', student_ids)\
            .eq('cycle', cycle)
        
        if academic_year:
            vespa_query = vespa_query.eq('academic_year', academic_year)
            
        vespa_result = vespa_query.execute()
        scores = vespa_result.data if vespa_result.data else []
        
        if scores:
            # Calculate statistics
            overall_scores = [s['overall'] for s in scores if s.get('overall') is not None]
            
            return {
                'mean': float(np.mean(overall_scores)) if overall_scores else 0,
                'std': float(np.std(overall_scores)) if overall_scores else 0,
                'count': len(overall_scores),
                'vespa_breakdown': {
                    'vision': float(np.mean([s['vision'] for s in scores if s.get('vision') is not None])) if scores else 0,
                    'effort': float(np.mean([s['effort'] for s in scores if s.get('effort') is not None])) if scores else 0,
                    'systems': float(np.mean([s['systems'] for s in scores if s.get('systems') is not None])) if scores else 0,
                    'practice': float(np.mean([s['practice'] for s in scores if s.get('practice') is not None])) if scores else 0,
                    'attitude': float(np.mean([s['attitude'] for s in scores if s.get('attitude') is not None])) if scores else 0
                },
                'year_group': year_group,
                'academic_year': academic_year
            }
        else:
            return {'mean': 0, 'std': 0, 'count': 0, 'vespa_breakdown': {}, 'year_group': year_group}
            
    except Exception as e:
        app.logger.error(f"Failed to fetch year group data: {e}")
        return {}

def fetch_academic_year_data(establishment_id, academic_year, year_group=None, cycle=1):
    """Fetch VESPA data for a specific academic year"""
    try:
        # Get students for this academic year
        students_query = supabase_client.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)
        
        # Filter by year group if specified
        if year_group:
            students_query = students_query.eq('year_group', year_group)
            
        students_result = students_query.execute()
        student_ids = [s['id'] for s in students_result.data] if students_result.data else []
        
        if not student_ids:
            return {'mean': 0, 'std': 0, 'count': 0, 'vespa_breakdown': {}, 'academic_year': academic_year}
        
        # Get vespa scores for this academic year
        vespa_result = supabase_client.table('vespa_scores')\
            .select('*')\
            .in_('student_id', student_ids)\
            .eq('academic_year', academic_year)\
            .eq('cycle', cycle)\
            .execute()
        
        scores = vespa_result.data if vespa_result.data else []
        
        if scores:
            # Calculate statistics
            overall_scores = [s['overall'] for s in scores if s.get('overall') is not None]
            
            return {
                'mean': float(np.mean(overall_scores)) if overall_scores else 0,
                'std': float(np.std(overall_scores)) if overall_scores else 0,
                'count': len(overall_scores),
                'vespa_breakdown': {
                    'vision': float(np.mean([s['vision'] for s in scores if s.get('vision') is not None])) if scores else 0,
                    'effort': float(np.mean([s['effort'] for s in scores if s.get('effort') is not None])) if scores else 0,
                    'systems': float(np.mean([s['systems'] for s in scores if s.get('systems') is not None])) if scores else 0,
                    'practice': float(np.mean([s['practice'] for s in scores if s.get('practice') is not None])) if scores else 0,
                    'attitude': float(np.mean([s['attitude'] for s in scores if s.get('attitude') is not None])) if scores else 0
                },
                'academic_year': academic_year,
                'year_group': year_group
            }
        else:
            return {'mean': 0, 'std': 0, 'count': 0, 'vespa_breakdown': {}, 'academic_year': academic_year}
            
    except Exception as e:
        app.logger.error(f"Failed to fetch academic year data: {e}")
        return {}

def generate_contextual_insights(comparison_data, org_context, questions, historical, report_type, school_name):
    """Generate AI insights with organizational context"""
    
    if not OPENAI_API_KEY:
        return {
            'summary': 'AI insights not available - API key not configured',
            'key_findings': [],
            'recommendations': []
        }
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        # Build comprehensive context
        data_summary = summarize_comparison_data(comparison_data)
        
        # Enhanced system prompt with context awareness
        system_prompt = """You are an expert educational data analyst specializing in VESPA metrics and student performance analysis. 
        You provide evidence-based, actionable insights that are specific to the school's context and concerns.
        Focus on practical recommendations that can be implemented immediately.
        When the user provides organizational context, pay special attention to addressing their specific concerns and questions."""
        
        # Build user prompt with all context
        user_prompt = f"""
        School: {school_name}
        Report Type: {report_type}
        
        DATA SUMMARY:
        {data_summary}
        
        ORGANIZATIONAL CONTEXT:
        {org_context if org_context else 'No specific context provided'}
        
        SPECIFIC QUESTIONS TO ADDRESS:
        {questions if questions else 'No specific questions provided'}
        
        HISTORICAL CONTEXT:
        {historical if historical else 'No historical context provided'}
        
        Please provide:
        1. An executive summary (2-3 paragraphs) that directly addresses the organizational context
        2. 3-5 key findings with statistical support
        3. 3-5 specific, actionable recommendations
        4. If questions were provided, ensure each is answered with data-driven insights
        
        Focus especially on:
        - Explaining unexpected patterns (e.g., if Year 13 shows lower confidence than Year 12)
        - Identifying root causes based on the data
        - Providing practical interventions
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use gpt-3.5-turbo for reliability
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse the response
        ai_text = response.choices[0].message['content']
        
        # Extract sections (basic parsing)
        sections = ai_text.split('\n\n')
        
        return {
            'summary': sections[0] if sections else '',
            'key_findings': extract_bullet_points(ai_text, 'findings'),
            'recommendations': extract_bullet_points(ai_text, 'recommendations'),
            'full_analysis': ai_text
        }
        
    except Exception as e:
        app.logger.error(f"AI generation failed: {e}")
        traceback.print_exc()
        return {
            'summary': 'Unable to generate AI insights',
            'key_findings': [],
            'recommendations': [],
            'error': str(e)
        }

def summarize_comparison_data(data):
    """Create a text summary of comparison data for AI context"""
    summary = []
    
    for key, values in data.items():
        if isinstance(values, dict) and 'mean' in values:
            summary.append(f"{key}: Mean={values['mean']:.2f}, StdDev={values['std']:.2f}, N={values['count']}")
            
            # Add VESPA breakdowns if available
            if 'vespa_breakdown' in values:
                vespa = values['vespa_breakdown']
                summary.append(f"  VESPA breakdown: Vision={vespa.get('vision', 0):.2f}, Effort={vespa.get('effort', 0):.2f}, Systems={vespa.get('systems', 0):.2f}, Practice={vespa.get('practice', 0):.2f}, Attitude={vespa.get('attitude', 0):.2f}")
    
    return '\n'.join(summary)

def extract_bullet_points(text, section_type):
    """Extract bullet points from AI response"""
    lines = text.split('\n')
    bullets = []
    
    for line in lines:
        if line.strip().startswith(('-', '•', '*', '1.', '2.', '3.', '4.', '5.')):
            bullets.append(line.strip().lstrip('-•*0123456789. '))
    
    return bullets[:5]  # Return top 5

def create_interactive_html_report(school_name, logo_url, primary_color, data, insights, config, report_type):
    """Create an interactive HTML report using real data - no mockup dependency"""
    
    app.logger.info(f"Creating interactive HTML report for {school_name}")
    app.logger.info(f"Report type: {report_type}, Config: {config}")
    app.logger.info(f"Data keys: {data.keys() if data else 'No data'}")
    
    # Always generate from template with real data - no mockup
    html_content = create_html_from_template(school_name, logo_url, primary_color, data, insights, config, report_type)
    
    # Replace placeholders with real data
    comparison_title = get_comparison_title(report_type, config)
    
    app.logger.info(f"Loaded HTML template with length: {len(html_content)}")
    app.logger.info(f"Report type: {report_type}, Config: {config}")
    app.logger.info(f"Data keys: {data.keys() if data else 'No data'}")
    
    # Build dynamic sections with real data
    vespa_section = build_vespa_comparison_section(data, report_type)
    qla_section = generate_qla_insights_html(data, report_type)
    chart_data = prepare_chart_data(data, report_type)
    
    # Inject real data into the HTML
    replacements = {
        'Rochdale Sixth Form College': school_name,
        'Year 12 vs Year 13 Comparative Analysis': comparison_title,
        'This analysis compares VESPA scores between Year 12 and Year 13 students': config.get('organizationalContext', 'This analysis compares VESPA scores to identify trends and opportunities.'),
        '<!-- EXECUTIVE_SUMMARY_PLACEHOLDER -->': insights.get('summary', 'Executive summary based on data analysis.'),
        '<!-- KEY_FINDINGS_PLACEHOLDER -->': generate_key_findings_html(insights.get('key_findings', [])),
        '<!-- RECOMMENDATIONS_PLACEHOLDER -->': generate_recommendations_html(insights.get('recommendations', [])),
        '<!-- DATA_JSON_PLACEHOLDER -->': json.dumps(chart_data) if chart_data else '{}',
        '<!-- VESPA_SECTION_PLACEHOLDER -->': vespa_section,
        '<!-- QLA_SECTION_PLACEHOLDER -->': qla_section,
        '#667eea': primary_color,
        '{{academic_year}}': config.get('academicYear', config.get('academicYear1', '2024/2025')),
        '{{report_date}}': datetime.now().strftime('%B %d, %Y')
    }
    
    for old_text, new_text in replacements.items():
        html_content = html_content.replace(old_text, new_text)
    
    # Add logo URL if provided
    if logo_url:
        html_content = html_content.replace(
            'src="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\'',
            f'src="{logo_url}"'
        )
    
    # Inject real data as JavaScript
    data_script = f"""
    <script>
        // Real data from backend
        window.realReportData = {json.dumps(data) if data else '{}'};
        window.realInsights = {json.dumps(insights) if insights else '{}'};
        window.chartData = {json.dumps(chart_data) if chart_data else '{}'};
        window.vespaColors = {{
            'vision': '#e59437',
            'effort': '#86b4f0', 
            'systems': '#72cb44',
            'practice': '#7f31a4',
            'attitude': '#f032e6',
            'overall': '#667eea'
        }};
        
        // Initialize with real data when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('Real data loaded:', window.realReportData);
            console.log('Chart data:', window.chartData);
            
            // Initialize VESPA Radar Chart if data exists
            if (window.chartData && window.chartData.vespaRadar) {{
                const radarCanvas = document.getElementById('vespaRadarChart');
                if (!radarCanvas) {{
                    // Create canvas if it doesn't exist
                    const chartSection = document.querySelector('.chart-section') || document.querySelector('.vespa-comparison-section');
                    if (chartSection) {{
                        const canvas = document.createElement('canvas');
                        canvas.id = 'vespaRadarChart';
                        canvas.style.maxHeight = '400px';
                        chartSection.appendChild(canvas);
                    }}
                }}
                
                const radarCtx = document.getElementById('vespaRadarChart');
                if (radarCtx && radarCtx.getContext) {{
                    new Chart(radarCtx.getContext('2d'), {{
                        type: 'radar',
                        data: window.chartData.vespaRadar,
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ position: 'top' }},
                                title: {{ display: true, text: 'VESPA Profile Comparison' }}
                            }},
                            scales: {{
                                r: {{
                                    min: 0,
                                    max: 100,
                                    ticks: {{ stepSize: 20 }}
                                }}
                            }}
                        }}
                    }});
                }}
            }}
            
            // Initialize Trend Chart if data exists
            if (window.chartData && window.chartData.trendLine) {{
                const trendCanvas = document.getElementById('trendLineChart');
                if (!trendCanvas) {{
                    const chartSection = document.querySelector('.chart-section') || document.querySelector('.vespa-comparison-section');
                    if (chartSection) {{
                        const canvas = document.createElement('canvas');
                        canvas.id = 'trendLineChart';
                        canvas.style.maxHeight = '400px';
                        const container = document.createElement('div');
                        container.style.marginTop = '30px';
                        container.appendChild(canvas);
                        chartSection.appendChild(container);
                    }}
                }}
                
                const trendCtx = document.getElementById('trendLineChart');
                if (trendCtx && trendCtx.getContext) {{
                    new Chart(trendCtx.getContext('2d'), {{
                        type: 'line',
                        data: window.chartData.trendLine,
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ position: 'top' }},
                                title: {{ display: true, text: 'VESPA Trends' }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    max: 100
                                }}
                            }}
                        }}
                    }});
                }}
            }}
        }});
    </script>
    """
    
    # Inject the data script before closing body tag
    html_content = html_content.replace('</body>', data_script + '\n</body>')
    
    return html_content

def create_html_from_template(school_name, logo_url, primary_color, data, insights, config, report_type):
    """Create HTML from template if mockup file is not available"""
    html_template = create_html_template()
    
    # Prepare chart data
    chart_data = prepare_chart_data(data, report_type)
    
    # Format the comparison title
    comparison_title = get_comparison_title(report_type, config)
    
    # Build the interactive HTML
    html_content = html_template.format(
        school_name=school_name,
        comparison_title=comparison_title,
        report_date=datetime.now().strftime('%B %d, %Y'),
        primary_color=primary_color,
        logo_url=logo_url or 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24"%3E%3Cpath fill="%23667eea" d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72L5.18 9L12 5.28L18.82 9zM17 15.99l-5 2.73l-5-2.73v-3.72L12 15l5-2.73v3.72z"/%3E%3C/svg%3E',
        organizational_context=config.get('organizationalContext', 'No specific organizational context provided.'),
        executive_summary=insights.get('summary', 'Executive summary will be generated based on the data analysis.'),
        key_findings_html=generate_key_findings_html(insights.get('key_findings', [])),
        recommendations_html=generate_recommendations_html(insights.get('recommendations', [])),
        data_table_html=generate_data_table_html(data),
        chart_data_json=json.dumps(chart_data),
        vespa_colors=json.dumps({
            'vision': '#e59437',
            'effort': '#86b4f0', 
            'systems': '#72cb44',
            'practice': '#7f31a4',
            'attitude': '#f032e6',
            'overall': '#667eea'
        }),
        qla_insights_html=generate_qla_insights_html(data, report_type)
    )
    
    return html_content

def create_html_template():
    """Create the HTML template based on the mockup"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparative Report - {school_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/timdream/wordcloud2.js@gh-pages/src/wordcloud2.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .report-container {{ max-width: 1200px; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
        .control-panel {{ position: fixed; right: 20px; top: 20px; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; max-height: 80vh; overflow-y: auto; width: 280px; }}
        .control-panel h3 {{ margin-bottom: 15px; color: {primary_color}; font-size: 18px; }}
        .control-group {{ margin-bottom: 15px; }}
        .control-group label {{ display: flex; align-items: center; margin-bottom: 8px; cursor: pointer; font-size: 14px; }}
        .control-group input[type="checkbox"] {{ margin-right: 8px; }}
        .report-header {{ background: linear-gradient(135deg, {primary_color}, {primary_color}dd); color: white; padding: 40px; display: flex; align-items: center; justify-content: space-between; }}
        .header-title h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header-logo {{ width: 80px; height: 80px; border-radius: 8px; background: white; padding: 10px; }}
        .report-section {{ padding: 30px 40px; border-bottom: 1px solid #eee; }}
        .section-title {{ color: {primary_color}; font-size: 24px; margin-bottom: 20px; font-weight: 600; }}
        .editable {{ border: 1px dashed transparent; padding: 2px 4px; border-radius: 4px; transition: all 0.2s; }}
        .editable:hover {{ border-color: {primary_color}; background: #f0f0f0; cursor: text; }}
        .editable:focus {{ outline: none; border-color: {primary_color}; background: white; }}
        .key-finding {{ background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-left: 4px solid {primary_color}; border-radius: 4px; }}
        .recommendation {{ background: #e6f7ff; padding: 15px; margin-bottom: 10px; border-left: 4px solid #1890ff; border-radius: 4px; }}
        .data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .data-table th {{ background: {primary_color}; color: white; padding: 12px; text-align: left; }}
        .data-table td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        .data-table tr:hover {{ background: #f5f5f5; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 30px; margin-top: 20px; }}
        .chart-container {{ background: #f8f9fa; padding: 20px; border-radius: 8px; }}
        .btn {{ padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.3s; }}
        .btn-primary {{ background: {primary_color}; color: white; }}
        .btn-primary:hover {{ background: {primary_color}dd; }}
        @media print {{ .control-panel {{ display: none; }} }}
    </style>
</head>
<body>
    <!-- Control Panel -->
    <div class="control-panel" id="controlPanel">
        <h3>🎨 Report Customization</h3>
        <div class="control-group">
            <label style="font-weight: bold; margin-bottom: 10px;">Show/Hide Sections:</label>
            <label><input type="checkbox" checked onchange="toggleSection(\'executive-summary\')" /> Executive Summary</label>
            <label><input type="checkbox" checked onchange="toggleSection(\'key-findings\')" /> Key Findings</label>
            <label><input type="checkbox" checked onchange="toggleSection(\'data-analysis\')" /> Data Analysis</label>
            <label><input type="checkbox" checked onchange="toggleSection(\'recommendations\')" /> Recommendations</label>
        </div>
        <div class="btn-group" style="margin-top: 20px;">
            <button class="btn btn-primary" onclick="window.print()">🖨️ Print Report</button>
            <button class="btn btn-primary" onclick="exportHTML()">💾 Save HTML</button>
        </div>
    </div>
    
    <!-- Report Content -->
    <div class="report-container">
        <!-- Header -->
        <div class="report-header">
            <img src="{logo_url}" alt="School Logo" class="header-logo" onerror="this.style.display=\'none\'" />
            <div class="header-title">
                <h1 class="editable" contenteditable="true">{school_name}</h1>
                <p class="editable" contenteditable="true">{comparison_title}</p>
                <p>Generated: {report_date}</p>
            </div>
            <img src="https://vespa.academy/_astro/vespalogo.BGrK1ARl.png" alt="VESPA Logo" class="header-logo" />
        </div>
        
        <!-- Organizational Context -->
        <div class="report-section" id="context">
            <h2 class="section-title">Organizational Context</h2>
            <p class="editable" contenteditable="true">{organizational_context}</p>
        </div>
        
        <!-- Executive Summary -->
        <div class="report-section" id="executive-summary">
            <h2 class="section-title">Executive Summary</h2>
            <div class="editable" contenteditable="true">
                {executive_summary}
            </div>
        </div>
        
        <!-- Key Findings -->
        <div class="report-section" id="key-findings">
            <h2 class="section-title">Key Findings</h2>
            {key_findings_html}
        </div>
        
        <!-- Data Analysis -->
        <div class="report-section" id="data-analysis">
            <h2 class="section-title">Data Analysis</h2>
            {data_table_html}
            <div class="charts-grid" id="chartsContainer"></div>
        </div>
        
        <!-- Recommendations -->
        <div class="report-section" id="recommendations">
            <h2 class="section-title">Recommendations</h2>
            {recommendations_html}
        </div>
    </div>
    
    <script>
        const chartData = {chart_data_json};
        const vespaColors = {vespa_colors};
        
        function toggleSection(sectionId) {{
            const section = document.getElementById(sectionId);
            section.style.display = section.style.display === \'none\' ? \'block\' : \'none\';
        }}
        
        function exportHTML() {{
            const html = document.documentElement.outerHTML;
            const blob = new Blob([html], {{type: \'text/html\'}}); 
            const url = URL.createObjectURL(blob);
            const a = document.createElement(\'a\');
            a.href = url;
            a.download = \'comparative_report.html\';
            a.click();
        }}
        
        // Initialize charts when page loads
        window.addEventListener(\'load\', () => {{
            if (chartData && chartData.datasets) {{
                createCharts();
            }}
        }});
        
        function createCharts() {{
            // Implementation would create Chart.js charts based on chartData
            console.log(\'Charts would be created here with:\', chartData);
        }}
    </script>
</body>
</html>'''

def generate_key_findings_html(findings):
    """Generate HTML for key findings"""
    if not findings:
        return '<div class="key-finding editable" contenteditable="true">Key findings will appear here based on the data analysis.</div>'
    
    html = ''
    for finding in findings:
        html += f'<div class="key-finding editable" contenteditable="true">{finding}</div>'
    return html

def generate_recommendations_html(recommendations):
    """Generate HTML for recommendations"""
    if not recommendations:
        return '<div class="recommendation editable" contenteditable="true">Recommendations will appear here based on the analysis.</div>'
    
    html = ''
    for rec in recommendations:
        html += f'<div class="recommendation editable" contenteditable="true">{rec}</div>'
    return html

def generate_data_table_html(data):
    """Generate HTML table for data comparison"""
    app.logger.info(f"Generating data table HTML with data keys: {data.keys() if data else 'No data'}")
    
    html = '<table class="data-table">'
    html += '<thead><tr><th>Group</th><th>Mean Score</th><th>Std Dev</th><th>Sample Size</th></tr></thead>'
    html += '<tbody>'
    
    has_data = False
    for key, values in data.items():
        # Skip non-data keys
        if key in ['qla_data', 'insights', 'charts']:
            continue
            
        if isinstance(values, dict) and 'mean' in values:
            group_name = key.replace('_', ' ').title()
            mean_val = values.get('mean', 0)
            std_val = values.get('std', 0) 
            count_val = values.get('count', 0)
            
            # Convert to percentage if needed (VESPA scores are 1-10)
            if 0 <= mean_val <= 10:
                mean_display = f'{mean_val * 10:.1f}%'
                std_display = f'{std_val * 10:.1f}'
            else:
                mean_display = f'{mean_val:.2f}'
                std_display = f'{std_val:.2f}'
            
            html += f'<tr>'
            html += f'<td>{group_name}</td>'
            html += f'<td>{mean_display}</td>'
            html += f'<td>{std_display}</td>'
            html += f'<td>{count_val}</td>'
            html += f'</tr>'
            has_data = True
            
            app.logger.info(f"Added row for {group_name}: mean={mean_val}, std={std_val}, count={count_val}")
    
    if not has_data:
        html += '<tr><td colspan="4" style="text-align: center; color: #999;">No data available</td></tr>'
    
    html += '</tbody></table>'
    return html

def prepare_chart_data(data, report_type):
    """Prepare data for Chart.js visualization"""
    chart_data = {
        'vespaRadar': None,
        'comparisonBar': None,
        'trendLine': None,
        'distribution': None,
        'heatmap': None
    }
    
    # Extract VESPA scores for radar chart
    vespa_categories = ['vision', 'effort', 'systems', 'practice', 'attitude']
    
    if report_type in ['cycle_vs_cycle', 'cycle_progression']:
        # Prepare radar chart data for VESPA comparison
        datasets = []
        for key, values in data.items():
            if isinstance(values, dict) and 'vespa_breakdown' in values:
                vespa = values['vespa_breakdown']
                datasets.append({
                    'label': key.replace('_', ' ').title(),
                    'data': [
                        vespa.get('vision', 0) * 10,  # Convert to 0-100 scale
                        vespa.get('effort', 0) * 10,
                        vespa.get('systems', 0) * 10,
                        vespa.get('practice', 0) * 10,
                        vespa.get('attitude', 0) * 10
                    ],
                    'backgroundColor': f'rgba(102, 126, 234, {0.2 if len(datasets) == 0 else 0.1})',
                    'borderColor': '#667eea' if len(datasets) == 0 else '#764ba2',
                    'pointBackgroundColor': '#667eea' if len(datasets) == 0 else '#764ba2',
                    'pointBorderColor': '#fff',
                    'pointHoverBackgroundColor': '#fff',
                    'pointHoverBorderColor': '#667eea' if len(datasets) == 0 else '#764ba2'
                })
        
        if datasets:
            chart_data['vespaRadar'] = {
                'type': 'radar',
                'labels': ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude'],
                'datasets': datasets
            }
    
    # Prepare comparison bar chart
    if report_type in ['year_group_vs_year_group', 'group_vs_group']:
        labels = []
        overall_scores = []
        
        for key, values in data.items():
            if isinstance(values, dict) and 'mean' in values:
                labels.append(key.replace('_', ' ').title())
                overall_scores.append(values['mean'] * 10)  # Convert to 0-100 scale
        
        if labels:
            chart_data['comparisonBar'] = {
                'type': 'bar',
                'labels': labels,
                'datasets': [{
                    'label': 'Overall VESPA Score',
                    'data': overall_scores,
                    'backgroundColor': ['#667eea', '#764ba2', '#8b5cf6', '#a78bfa'],
                    'borderColor': ['#667eea', '#764ba2', '#8b5cf6', '#a78bfa'],
                    'borderWidth': 1
                }]
            }
    
    # Prepare trend line chart for progression reports
    if report_type == 'cycle_progression' or report_type == 'progress':
        cycles = sorted([k for k in data.keys() if k.startswith('cycle_')])
        
        if cycles:
            vespa_trends = {cat: [] for cat in vespa_categories}
            overall_trend = []
            
            for cycle in cycles:
                if cycle in data and 'vespa_breakdown' in data[cycle]:
                    vespa = data[cycle]['vespa_breakdown']
                    for cat in vespa_categories:
                        vespa_trends[cat].append(vespa.get(cat, 0) * 10)
                    overall_trend.append(data[cycle].get('mean', 0) * 10)
            
            datasets = []
            colors = {
                'vision': '#e59437',
                'effort': '#86b4f0',
                'systems': '#72cb44',
                'practice': '#7f31a4',
                'attitude': '#f032e6'
            }
            
            for cat in vespa_categories:
                if vespa_trends[cat]:
                    datasets.append({
                        'label': cat.capitalize(),
                        'data': vespa_trends[cat],
                        'borderColor': colors[cat],
                        'backgroundColor': colors[cat] + '20',  # Add transparency
                        'tension': 0.3,
                        'fill': False
                    })
            
            # Add overall trend
            if overall_trend:
                datasets.append({
                    'label': 'Overall',
                    'data': overall_trend,
                    'borderColor': '#667eea',
                    'backgroundColor': '#667eea20',
                    'borderWidth': 3,
                    'tension': 0.3,
                    'fill': False
                })
            
            if datasets:
                chart_data['trendLine'] = {
                    'type': 'line',
                    'labels': [c.replace('cycle_', 'Cycle ') for c in cycles],
                    'datasets': datasets
                }
    
    # Add distribution data if available
    if any('distribution' in v for v in data.values() if isinstance(v, dict)):
        # This would need actual distribution data from QLA
        chart_data['distribution'] = {
            'type': 'bar',
            'labels': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
            'datasets': []
        }
    
    return chart_data

def get_comparison_title(report_type, config):
    """Generate appropriate title based on report type"""
    if report_type == 'cycle_progression':
        cycles = config.get('cycles', [])
        if len(cycles) >= 2:
            return f"Cycle {cycles[0]} vs Cycle {cycles[-1]} Comparative Analysis"
        return "Cycle Progression Analysis"
    elif report_type == 'group_comparison':
        dimension = config.get('groupDimension', 'group')
        return f"{dimension.replace('_', ' ').title()} Comparison Analysis"
    return "Comparative Analysis Report"

def build_vespa_comparison_section(data, report_type):
    """Build VESPA comparison section with real data"""
    html = '<div class="vespa-comparison-section">'
    html += '<h3 class="section-title">VESPA Score Comparison</h3>'
    
    # Extract VESPA data from comparison data
    vespa_data = {}
    for key, values in data.items():
        if isinstance(values, dict) and 'vespa_breakdown' in values:
            vespa_data[key] = values['vespa_breakdown']
    
    if vespa_data:
        # Create comparison table
        html += '<table class="vespa-table">'
        html += '<thead><tr><th>Element</th>'
        
        # Add column headers for each comparison group
        for key in vespa_data.keys():
            label = key.replace('_', ' ').title()
            html += f'<th>{label}</th>'
        html += '<th>Difference</th></tr></thead>'
        
        html += '<tbody>'
        vespa_elements = ['vision', 'effort', 'systems', 'practice', 'attitude']
        
        for element in vespa_elements:
            html += f'<tr><td class="element-name">{element.capitalize()}</td>'
            
            scores = []
            for key, breakdown in vespa_data.items():
                score = breakdown.get(element, 0) * 10  # Convert to percentage
                scores.append(score)
                color_class = f'vespa-{element}'
                html += f'<td class="score {color_class}">{score:.1f}%</td>'
            
            # Calculate difference
            if len(scores) >= 2:
                diff = scores[1] - scores[0]
                diff_class = 'positive' if diff > 0 else 'negative' if diff < 0 else 'neutral'
                html += f'<td class="difference {diff_class}">{diff:+.1f}%</td>'
            else:
                html += '<td class="difference">-</td>'
            
            html += '</tr>'
        
        # Add overall row
        html += '<tr class="overall-row"><td class="element-name"><strong>Overall</strong></td>'
        overall_scores = []
        for key, values in data.items():
            if isinstance(values, dict) and 'mean' in values:
                score = values['mean'] * 10
                overall_scores.append(score)
                html += f'<td class="score overall"><strong>{score:.1f}%</strong></td>'
        
        if len(overall_scores) >= 2:
            diff = overall_scores[1] - overall_scores[0]
            diff_class = 'positive' if diff > 0 else 'negative' if diff < 0 else 'neutral'
            html += f'<td class="difference {diff_class}"><strong>{diff:+.1f}%</strong></td>'
        else:
            html += '<td class="difference">-</td>'
        
        html += '</tr></tbody></table>'
    else:
        html += '<p>No VESPA data available for comparison.</p>'
    
    html += '</div>'
    return html

def generate_qla_insights_html(data, report_type):
    """Generate Question Level Analysis insights HTML"""
    
    # Check if QLA data exists
    qla_data = data.get('qla_data', {})
    if not qla_data:
        return ''
    
    html = '''
    <div class="qla-section">
        <h3 class="section-title">Question Level Analysis</h3>
    '''
    
    # Add top differences if available
    if 'questions' in qla_data:
        questions = qla_data['questions'][:10]  # Top 10 differences
        
        html += '<h4>Questions with Largest Differences</h4>'
        html += '<div class="qla-grid">'
        
        for idx, q in enumerate(questions):
            diff = q.get('difference', 0)
            diff_class = 'high-diff' if abs(diff) > 1.5 else 'medium-diff' if abs(diff) > 0.8 else 'low-diff'
            
            html += f'''
            <div class="question-diff-card {diff_class}">
                <div class="diff-rank">{idx + 1}</div>
                <div class="question-content">
                    <p class="question-text editable" contenteditable="true">{q.get('text', 'Question text')}</p>
                    <div class="diff-scores">
                        <div class="score-group">
                            <span class="score-label">Group 1</span>
                            <span class="score-value">{q.get('group1Score', 0):.2f}</span>
                        </div>
                        <div class="diff-arrow {"up" if diff > 0 else "down"}">
                            {"↑" if diff > 0 else "↓"} {abs(diff):.2f}
                        </div>
                        <div class="score-group">
                            <span class="score-label">Group 2</span>
                            <span class="score-value">{q.get('group2Score', 0):.2f}</span>
                        </div>
                    </div>
                    <span class="category-badge {q.get('category', 'overall').lower()}">{q.get('category', 'OVERALL')}</span>
                </div>
            </div>
            '''
        
        html += '</div>'
        
        # Add statistical summary
        if 'totalQuestions' in qla_data:
            html += f'''
            <div class="stats-summary">
                <div class="stat-item">
                    <span class="stat-label">Total Questions Analyzed:</span>
                    <span class="stat-value">{qla_data.get('totalQuestions', 0)}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Significant Differences (p < 0.05):</span>
                    <span class="stat-value">{qla_data.get('significantDifferences', 0)}</span>
                </div>
            </div>
            '''
    
    # Add QLA insights if available
    if 'insights' in qla_data and qla_data['insights']:
        html += '<h4>Question-Level Insights</h4>'
        html += '<div class="qla-insights">'
        for insight in qla_data['insights']:
            html += f'<p class="insight-item editable" contenteditable="true">• {insight}</p>'
        html += '</div>'
    
    html += '</div>'
    
    return html

@app.route('/api/comparative-report/export-pdf', methods=['POST', 'OPTIONS'])
def export_comparative_report_pdf():
    """Export the edited HTML report as a PDF"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, X-Knack-Application-Id, X-Knack-REST-API-Key, x-knack-application-id, x-knack-rest-api-key')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        if not data:
            raise ApiError("Missing request body", 400)
        
        # Get the edited HTML content
        html_content = data.get('html', '')
        establishment_name = data.get('establishmentName', 'Report')
        
        if not html_content:
            raise ApiError("No HTML content provided", 400)
        
        # Convert HTML to PDF using a library like weasyprint or pdfkit
        # For now, return a simple PDF with the content
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Parse key content from HTML (simplified for now)
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"<b>{establishment_name} - Comparative Report</b>", styles['Title']))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("This PDF was exported from the interactive HTML report editor.", styles['Normal']))
        elements.append(Paragraph("Full HTML-to-PDF conversion would require additional libraries like weasyprint.", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Comparative_Report_{establishment_name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Failed to export PDF: {e}")
        traceback.print_exc()
        raise ApiError(f"PDF export failed: {str(e)}", 500)

# ===== END COMPARATIVE REPORT ENDPOINT =====


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv('PORT', 5001)) # Use port 5001 for local dev if 5000 is common 