import os
import json
import traceback
import requests
from datetime import datetime, timedelta
from types import SimpleNamespace
from flask import Flask, request, jsonify, send_file, current_app, Response
from dotenv import load_dotenv
from flask_cors import CORS # Import CORS
import logging # Import Python's standard logging
from functools import wraps
import hashlib
import secrets
import redis
import pickle
import pandas as pd
from scipy.stats import pearsonr
import gzip  # Add gzip for compression
from threading import Thread
import time
import random  # Add random for sampling comments
import uuid  # For UCAS application comment IDs

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
    'academic_profile': 300,  # 5 minutes for academic profiles (like vespa_results)
}

# --- Supabase Setup ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
# Prefer service role key for write operations; fall back to SUPABASE_KEY (often anon) if that's all we have.
# NOTE: Do NOT log the key values.
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase_client = None
SUPABASE_ENABLED = False

if SUPABASE_URL and (SUPABASE_SERVICE_KEY or SUPABASE_KEY):
    try:
        # Create client with basic options only - avoid proxy issues on Heroku
        import os
        # Clear any proxy settings that might interfere
        for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
        
        # Use service key if present (required for updates when RLS is on)
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_KEY)
        SUPABASE_ENABLED = True
        app.logger.info(f"Supabase client initialized for {SUPABASE_URL} (service_key={'yes' if SUPABASE_SERVICE_KEY else 'no'})")
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
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'X-Knack-Application-Id', 'X-Knack-REST-API-Key', 'x-knack-application-id', 'x-knack-rest-api-key', 'X-User-Role', 'x-user-role'],
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
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-Knack-Application-Id, X-Knack-REST-API-Key, x-knack-application-id, x-knack-rest-api-key, X-User-Role, x-user-role'
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
KNACK_API_URL = os.getenv('KNACK_API_URL') or 'https://api.knack.com/v1'
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
@app.route('/api/sync/refresh-establishment', methods=['POST'])
def refresh_establishment_data():
    """
    Trigger real-time sync for a single establishment
    Allows staff admins to refresh their data on-demand without waiting for scheduled sync
    """
    data = request.get_json()
    if not data:
        raise ApiError("Missing request body")
    
    establishment_id = data.get('establishmentId')  # Knack ID
    
    if not establishment_id:
        raise ApiError("establishmentId is required")
    
    try:
        # Import the single establishment sync function
        import subprocess
        import json
        
        app.logger.info(f"Starting real-time sync for establishment: {establishment_id}")
        
        # Run sync as subprocess
        result = subprocess.run(
            ['python', 'sync_single_establishment.py', '--establishment-id', establishment_id],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            # Parse JSON output from sync script
            try:
                summary = json.loads(result.stdout.strip().split('\n')[-1])
                app.logger.info(f"Sync completed: {summary}")
                
                # Clear cache for this establishment
                if CACHE_ENABLED:
                    patterns = [
                        f'*:{establishment_id}:*',
                        f'dashboard_data:*:{establishment_id}:*',
                        f'dataset:{establishment_id}:*',
                        f'metadata:{establishment_id}:*'
                    ]
                    for pattern in patterns:
                        keys = redis_client.keys(pattern)
                        if keys:
                            redis_client.delete(*keys)
                
                return jsonify({
                    'success': True,
                    'message': f"Data refreshed successfully for {summary.get('establishment_name', 'establishment')}",
                    'summary': summary
                })
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return jsonify({
                    'success': True,
                    'message': 'Data refreshed successfully',
                    'details': 'Sync completed but summary unavailable'
                })
        else:
            app.logger.error(f"Sync failed: {result.stderr}")
            raise ApiError(f"Sync failed: {result.stderr[:200]}")
    
    except subprocess.TimeoutExpired:
        raise ApiError("Sync timeout - please try again later")
    except Exception as e:
        app.logger.error(f"Error refreshing establishment data: {e}")
        raise ApiError(f"Failed to refresh data: {str(e)}")


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
    academic_year = data.get('academicYear')  # Get selected academic year from request
    
    app.logger.info(f"Generating word cloud for fields: {comment_fields}, cycle: {cycle}, academic_year: {academic_year}")
    
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
        
        # FIXED: Only add academic year filter if NO academic year is explicitly provided
        # This allows the frontend to specify which academic year's comments to show
        if not academic_year:
            # Use auto-calculated current academic year as fallback
            academic_year_filter = get_academic_year_filters(establishment_id, 'field_855', 'field_3511')
            knack_filters.append(academic_year_filter)
            app.logger.info(f"Using auto-calculated academic year filter")
        else:
            # Use the selected academic year from the frontend
            # Convert to database format if needed (2025-26 -> 2025/2026)
            formatted_year = convert_academic_year_format(academic_year, to_database=True)
            app.logger.info(f"Using selected academic year: {formatted_year} (from frontend: {academic_year})")
            # Note: We can't filter Object_10 directly by academic_year field (doesn't exist in Knack)
            # Instead, we rely on the completion date field_855 being in range
            # For now, still apply date range filter but log what we're looking for
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
            
            # Enhanced logging for debugging
            app.logger.info(f"Comment Analysis - Page {page}: Fetched {len(records)} VESPA records")
            
            # Extract comments from records
            records_with_comments = 0
            for record in records:
                has_comment_this_record = False
                for field in comment_fields:
                    comment = record.get(field + '_raw')
                    if comment and isinstance(comment, str) and len(comment.strip()) > 0:
                        all_comments.append(comment.strip())
                        has_comment_this_record = True
                if has_comment_this_record:
                    records_with_comments += 1
            
            app.logger.info(f"Comment Analysis - Page {page}: {records_with_comments} records had comments")
            
            if len(records) < 500:
                # Don't break - there might be more data on subsequent pages
                pass
            page += 1
        
        app.logger.info(f"Comment Analysis FINAL: Collected {len(all_comments)} comments from {page-1} pages")
        app.logger.info(f"Comment Analysis FILTERS USED: {json.dumps(knack_filters, indent=2)}")
        
        # If no comments found, return empty result
        if not all_comments:
            return jsonify({
                'wordCloudData': [],
                'totalComments': 0,
                'uniqueWords': 0,
                'topWord': None,
                'message': 'No comments found for the selected filters',
                'cycle': cycle,  # FIXED: Return cycle even when empty
                'academicYear': academic_year  # FIXED: Return academic year even when empty
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
            'topWord': top_words[0] if top_words else None,
            'cycle': cycle,  # FIXED: Return cycle so Vue badge can display it
            'academicYear': academic_year  # FIXED: Return academic year for badge
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
    cycle = data.get('cycle')  # Get cycle from request
    academic_year = data.get('academicYear')  # Get selected academic year from request
    
    app.logger.info(f"Analyzing themes for fields: {comment_fields}, cycle: {cycle}, academic_year: {academic_year}")
    
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
        
        # FIXED: Only add academic year filter if NO academic year is explicitly provided
        if not academic_year:
            # Use auto-calculated current academic year as fallback
            academic_year_filter = get_academic_year_filters(establishment_id, 'field_855', 'field_3511')
            knack_filters.append(academic_year_filter)
            app.logger.info(f"Theme analysis: Using auto-calculated academic year filter")
        else:
            # Use the selected academic year from the frontend
            formatted_year = convert_academic_year_format(academic_year, to_database=True)
            app.logger.info(f"Theme analysis: Using selected academic year: {formatted_year}")
            # Apply date range filter for selected academic year
            academic_year_filter = get_academic_year_filters(establishment_id, 'field_855', 'field_3511')
            knack_filters.append(academic_year_filter)
        
        # Add cycle filter if provided
        if cycle:
            knack_filters.append({
                'field': 'field_146',
                'operator': 'is',
                'value': str(cycle)
            })
            app.logger.info(f"Theme analysis: Added cycle filter for cycle {cycle}")
        
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
        gender = request.args.get('gender')
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
        if gender and gender != 'all':
            students_query = students_query.eq('gender', gender)
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
                'message': 'No students found for the selected filters',
                'cycle': cycle if cycle else 'All Cycles',
                'academicYear': academic_year
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
                'message': 'No comments found for the selected filters',
                'cycle': cycle if cycle else 'All Cycles',
                'academicYear': academic_year
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
                'message': 'No meaningful words found in comments',
                'cycle': cycle if cycle else 'All Cycles',
                'academicYear': academic_year
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
        gender = request.args.get('gender')
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
        if gender and gender != 'all':
            students_query = students_query.eq('gender', gender)
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

@app.route('/api/genders', methods=['GET'])
def get_genders():
    """Return available genders, optionally filtered by establishment (best-effort)."""
    try:
        establishment_id = request.args.get('establishment_id')
        
        if not establishment_id or not SUPABASE_ENABLED:
            return jsonify([])
        
        # Convert Knack ID to UUID if needed
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        
        # Best-effort: genders must exist on students table (column name: gender)
        result = supabase_client.table('students')\
            .select('gender')\
            .eq('establishment_id', establishment_uuid)\
            .execute()
        
        if result.data:
            genders = list(set(r.get('gender') for r in result.data if r.get('gender')))
            genders.sort()
            return jsonify(genders)
        
        return jsonify([])
        
    except Exception as e:
        # Best-effort: if the column doesn't exist yet, don't break the dashboard.
        app.logger.error(f"Failed to fetch genders: {e}")
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

        # Accept either Supabase UUID or Knack establishment ID
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        if not establishment_uuid:
            raise ApiError("Establishment not found", 404)
        
        result = supabase_client.table('establishments')\
            .select('id, name, knack_id, is_australian, trust_id')\
            .eq('id', establishment_uuid)\
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
        gender = request.args.get('gender')
        student_id = request.args.get('studentId')
        
        # Check if we have any filters other than cycle
        has_other_filters = (year_group and year_group != 'all') or \
                           (group and group != 'all') or \
                           (faculty and faculty != 'all') or \
                           (gender and gender != 'all') or \
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
                if gender and gender != 'all':
                    query = query.eq('gender', gender)
            
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
        gender = request.args.get('gender')
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
        # CRITICAL FIX: Ignore 'all' filter values - frontend sends 'all' to mean no filter
        has_filters = (
            (year_group and year_group != 'all') or 
            (group and group != 'all') or 
            (faculty and faculty != 'all') or 
            (gender and gender != 'all') or
            student_id
        )
        
        if has_filters or force_calculate_from_raw:
            # Get filtered student IDs first
            students_query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)
            
            # FIXED: Filter by academic_year on students table first to avoid cross-year contamination
            if academic_year:
                students_query = students_query.eq('academic_year', formatted_year)
            
            if year_group and year_group != 'all':
                students_query = students_query.eq('year_group', year_group)
            if group and group != 'all':
                students_query = students_query.eq('group', group)
            if faculty and faculty != 'all':
                students_query = students_query.eq('faculty', faculty)
            if gender and gender != 'all':
                students_query = students_query.eq('gender', gender)
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
            
            # CRITICAL FIX: Add limit to handle large schools (Supabase default is 1000)
            students_result = students_query.limit(10000).execute()
            student_ids = [s['id'] for s in students_result.data]
            app.logger.info(f"QLA DEBUG: Initial students from query: {len(student_ids)}")
            
            # NEW: Filter by who has VESPA data for the selected academic year
            if academic_year:
                students_with_vespa = []
                
                # Check in batches who has VESPA data for this year
                total_batches = (len(student_ids) + 49) // 50
                app.logger.info(f"QLA DEBUG: Processing {total_batches} batches of students for VESPA check")
                
                for i in range(0, len(student_ids), 50):
                    batch_ids = student_ids[i:i+50]
                    batch_num = (i // 50) + 1
                    
                    # Check which students have VESPA data for the selected year
                    # FIXED: Remove limit to get all results (batch of 50 should never exceed limits)
                    vespa_check = supabase_client.table('vespa_scores')\
                        .select('student_id')\
                        .in_('student_id', batch_ids)\
                        .eq('academic_year', formatted_year)\
                        .eq('cycle', cycle)\
                        .execute()
                    
                    students_with_vespa_ids = set(v['student_id'] for v in vespa_check.data)
                    app.logger.info(f"QLA DEBUG: Batch {batch_num}/{total_batches}: {len(batch_ids)} students queried, {len(students_with_vespa_ids)} have VESPA")
                    
                    # Keep only students who have VESPA data
                    students_with_vespa.extend([sid for sid in batch_ids if sid in students_with_vespa_ids])
                
                student_ids = students_with_vespa
                app.logger.info(f"QLA DEBUG: After VESPA filter: {len(student_ids)} students (expected 396)")
            
            # Get question responses for filtered students
            if student_ids:
                # FIXED: Reduce batch size to 30 students to stay under Supabase's 1000-record hard limit
                # 30 students × 32 questions = 960 responses (safely under 1000)
                BATCH_SIZE = 30
                filtered_responses = []
                total_qr_batches = (len(student_ids) + BATCH_SIZE - 1) // BATCH_SIZE
                app.logger.info(f"QLA DEBUG: Fetching question responses in {total_qr_batches} batches for {len(student_ids)} students")
                
                for i in range(0, len(student_ids), BATCH_SIZE):
                    batch_ids = student_ids[i:i + BATCH_SIZE]
                    batch_num = (i // BATCH_SIZE) + 1
                    
                    # Use range-based pagination to ensure we get ALL responses for these students
                    offset = 0
                    PAGE_SIZE = 1000  # Supabase's hard limit
                    batch_responses = []
                    
                    while True:
                        responses_query = supabase_client.table('question_responses')\
                            .select('question_id, response_value')\
                            .in_('student_id', batch_ids)\
                            .eq('cycle', cycle)
                        
                        # Add academic_year filter if provided
                        if academic_year:
                            responses_query = responses_query.eq('academic_year', formatted_year)
                        
                        # Use range() for proper pagination instead of limit()
                        responses_result = responses_query.range(offset, offset + PAGE_SIZE - 1).execute()
                        
                        if not responses_result.data:
                            break
                        
                        batch_responses.extend(responses_result.data)
                        app.logger.info(f"QLA DEBUG: Batch {batch_num}/{total_qr_batches}, Page offset {offset}: Fetched {len(responses_result.data)} responses")
                        
                        # If we got less than PAGE_SIZE, we've reached the end
                        if len(responses_result.data) < PAGE_SIZE:
                            break
                        
                        offset += PAGE_SIZE
                    
                    app.logger.info(f"QLA DEBUG: Batch {batch_num}/{total_qr_batches}: Fetched {len(batch_responses)} total responses for {len(batch_ids)} students")
                    filtered_responses.extend(batch_responses)
                
                app.logger.info(f"QLA DEBUG: Total responses collected: {len(filtered_responses)}, unique students: {len(set(r['question_id'] for r in filtered_responses))}")
                
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

# ===== VESPA QUESTIONNAIRE V2 ENDPOINTS =====

# Load question mappings for Knack field IDs
QUESTION_MAPPINGS_FILE = os.path.join(os.path.dirname(__file__), 'AIVESPACoach', 'psychometric_question_details.json')
try:
    with open(QUESTION_MAPPINGS_FILE, 'r', encoding='utf-8') as f:
        QUESTION_MAPPINGS = json.load(f)
        app.logger.info(f"Loaded {len(QUESTION_MAPPINGS)} question mappings")
        
        # Create a mapping dict keyed by questionId for fast lookup
        # Also add alias mappings for Vue app IDs that don't match JSON
        QUESTION_MAP_BY_ID = {}
        for q in QUESTION_MAPPINGS:
            QUESTION_MAP_BY_ID[q['questionId']] = q
        
        # Add aliases for Vue app question IDs that don't match psychometric JSON
        ID_ALIASES = {
            'q29': 'q29_vision_grades',
            'q30': 'outcome_q_support',
            'q31': 'outcome_q_equipped',
            'q32': 'outcome_q_confident'
        }
        
        for vue_id, json_id in ID_ALIASES.items():
            if json_id in QUESTION_MAP_BY_ID:
                QUESTION_MAP_BY_ID[vue_id] = QUESTION_MAP_BY_ID[json_id]
                app.logger.info(f"Added alias: {vue_id} → {json_id}")
        
except Exception as e:
    app.logger.error(f"Failed to load question mappings: {e}")
    QUESTION_MAPPINGS = []
    QUESTION_MAP_BY_ID = {}

def calculate_academic_year_for_student(date_obj=None, is_australian=False, use_standard_year=None):
    """Calculate academic year based on date and school location
    
    Priority:
    1. If use_standard_year is YES or NULL: Use UK August cutoff
    2. If use_standard_year is NO and is_australian: Use calendar year
    3. Otherwise: UK August cutoff
    """
    if date_obj is None:
        date_obj = datetime.now()
    
    # Priority: use_standard_year flag overrides is_australian
    # NULL or YES = use standard UK calculation
    if use_standard_year is None or use_standard_year == True:
        # Use standard UK academic year (Aug-Jul)
        if date_obj.month >= 8:
            return f"{date_obj.year}/{date_obj.year + 1}"
        else:
            return f"{date_obj.year - 1}/{date_obj.year}"
    elif is_australian:
        # Australian school NOT using standard: Calendar year (Jan-Dec)
        return f"{date_obj.year}/{date_obj.year}"
    else:
        # UK school: Academic year (Aug-Jul)
        if date_obj.month >= 8:
            return f"{date_obj.year}/{date_obj.year + 1}"
        else:
            return f"{date_obj.year - 1}/{date_obj.year}"

@app.route('/api/vespa/questionnaire/validate', methods=['GET'])
def validate_questionnaire_access():
    """
    Validate if a student can take the VESPA questionnaire
    Checks:
    1. VESPA Customer (establishment) from Object_6 or Object_3
    2. Cycle dates from Object_66 for that establishment
    3. Which cycle is currently active (based on today's date)
    4. Whether student has already completed the active cycle
    """
    try:
        email = request.args.get('email')
        account_id = request.args.get('accountId')
        
        if not email:
            return jsonify({'allowed': False, 'reason': 'error', 'message': 'Email is required'}), 400
        
        app.logger.info(f"[Questionnaire Validate] Checking access for {email}")
        
        headers = {
            'X-Knack-Application-Id': os.getenv('KNACK_APP_ID'),
            'X-Knack-REST-API-Key': os.getenv('KNACK_API_KEY'),
            'Content-Type': 'application/json'
        }
        
        # STEP 1: Get VESPA Customer (establishment) from Object_6 (primary) or Object_3 (fallback)
        vespa_customer_id = None
        
        # Try Object_6 first (student record)
        app.logger.info(f"[Questionnaire Validate] Looking up VESPA Customer from Object_6...")
        obj6_filters = {
            'match': 'and',
            'rules': [{
                'field': 'field_182',  # Email connection in Object_6
                'operator': 'is',
                'value': email
            }]
        }
        
        obj6_response = requests.get(
            "https://api.knack.com/v1/objects/object_6/records",
            headers=headers,
            params={'filters': json.dumps(obj6_filters)},
            timeout=30
        )
        
        if obj6_response.ok:
            obj6_records = obj6_response.json().get('records', [])
            if obj6_records:
                obj6_record = obj6_records[0]
                vespa_customer_field = obj6_record.get('field_179_raw', [])
                if vespa_customer_field and isinstance(vespa_customer_field, list) and len(vespa_customer_field) > 0:
                    vespa_customer_id = vespa_customer_field[0].get('id') if isinstance(vespa_customer_field[0], dict) else vespa_customer_field[0]
                    app.logger.info(f"[Questionnaire Validate] Found VESPA Customer from Object_6: {vespa_customer_id}")
        
        # Fallback to Object_3 (user profile) if not found
        if not vespa_customer_id and account_id:
            app.logger.info(f"[Questionnaire Validate] Trying Object_3 fallback...")
            obj3_filters = {
                'match': 'and',
                'rules': [{
                    'field': 'field_70',  # Email in Object_3
                    'operator': 'is',
                    'value': email
                }]
            }
            
            obj3_response = requests.get(
                "https://api.knack.com/v1/objects/object_3/records",
                headers=headers,
                params={'filters': json.dumps(obj3_filters)},
                timeout=30
            )
            
            if obj3_response.ok:
                obj3_records = obj3_response.json().get('records', [])
                if obj3_records:
                    vespa_customer_field = obj3_records[0].get('field_122_raw', [])
                    if vespa_customer_field and isinstance(vespa_customer_field, list) and len(vespa_customer_field) > 0:
                        vespa_customer_id = vespa_customer_field[0].get('id') if isinstance(vespa_customer_field[0], dict) else vespa_customer_field[0]
                        app.logger.info(f"[Questionnaire Validate] Found VESPA Customer from Object_3: {vespa_customer_id}")
        
        if not vespa_customer_id:
            return jsonify({
                'allowed': False,
                'reason': 'no_establishment',
                'message': 'Unable to identify your school/establishment. Please contact support.'
            }), 400
        
        # STEP 2: Get cycle dates from Object_66 for this VESPA Customer
        app.logger.info(f"[Questionnaire Validate] Fetching cycle dates from Object_66...")
        cycle_filters = {
            'match': 'and',
            'rules': [{
                'field': 'field_1585',  # Connected VESPA Customer in Object_66
                'operator': 'is',
                'value': vespa_customer_id
            }]
        }
        
        cycles_response = requests.get(
            "https://api.knack.com/v1/objects/object_66/records",
            headers=headers,
            params={'filters': json.dumps(cycle_filters)},
            timeout=30
        )
        
        if not cycles_response.ok:
            app.logger.error(f"Failed to fetch cycles: {cycles_response.status_code}")
            return jsonify({
                'allowed': False,
                'reason': 'error',
                'message': 'Unable to load cycle dates for your school'
            }), 500
        
        cycle_records = cycles_response.json().get('records', [])
        
        if not cycle_records:
            app.logger.warning(f"No cycle dates found for VESPA Customer: {vespa_customer_id}")
            return jsonify({
                'allowed': False,
                'reason': 'no_cycles',
                'message': 'No questionnaire cycles have been set up for your school yet'
            }), 400
        
        # STEP 3: Determine which cycle is currently active based on dates
        today = datetime.now().date()
        active_cycle = None
        active_cycle_record = None
        
        app.logger.info(f"[Questionnaire Validate] Checking {len(cycle_records)} cycle periods for today's date: {today}")
        
        for cycle_record in cycle_records:
            cycle_num = cycle_record.get('field_1579_raw')  # Cycle number
            start_date_str = cycle_record.get('field_1678')  # Start date
            end_date_str = cycle_record.get('field_1580')    # End date
            
            if not start_date_str or not end_date_str:
                continue
            
            try:
                # Parse dates (UK format DD/MM/YYYY)
                start_date = datetime.strptime(start_date_str, '%d/%m/%Y').date()
                end_date = datetime.strptime(end_date_str, '%d/%m/%Y').date()
                
                app.logger.info(f"[Questionnaire Validate] Cycle {cycle_num}: {start_date} to {end_date}")
                
                # Check if today is within this cycle
                if start_date <= today <= end_date:
                    active_cycle = int(cycle_num) if cycle_num else None
                    active_cycle_record = cycle_record
                    app.logger.info(f"[Questionnaire Validate] ACTIVE CYCLE FOUND: Cycle {active_cycle}")
                    break
            except Exception as e:
                app.logger.warning(f"Error parsing cycle dates: {e}")
                continue
        
        if not active_cycle:
            # No active cycle right now - check if there's an override (Cycle Unlocked)
            app.logger.info(f"[Questionnaire Validate] No active cycle for today: {today}")
            app.logger.info(f"[Questionnaire Validate] Checking for Cycle Unlocked override...")
            
            # Fetch student's Object_10 record to check field_1679 (Cycle Unlocked)
            obj10_filters = {
                'match': 'and',
                'rules': [{
                    'field': 'field_197',  # Student email
                    'operator': 'is',
                    'value': email
                }]
            }
            
            obj10_response = requests.get(
                f"https://api.knack.com/v1/objects/object_10/records",
                headers=headers,
                params={'filters': json.dumps(obj10_filters)},
                timeout=30
            )
            
            cycle_unlocked = False
            obj10_record = None
            
            if obj10_response.ok:
                obj10_records = obj10_response.json().get('records', [])
                if obj10_records:
                    obj10_record = obj10_records[0]
                    cycle_unlocked_raw = obj10_record.get('field_1679_raw')
                    cycle_unlocked_display = obj10_record.get('field_1679')
                    
                    # Knack boolean: _raw = true/false (boolean), display = "Yes"/"No" (string)
                    cycle_unlocked = cycle_unlocked_raw is True or cycle_unlocked_raw == True or cycle_unlocked_display == 'Yes'
                    
                    app.logger.info(f"[Questionnaire Validate] Cycle Unlocked field_1679_raw: {cycle_unlocked_raw} (type: {type(cycle_unlocked_raw).__name__})")
                    app.logger.info(f"[Questionnaire Validate] Cycle Unlocked field_1679 display: {cycle_unlocked_display}")
                    app.logger.info(f"[Questionnaire Validate] Cycle Unlocked result: {cycle_unlocked}")
            
            if cycle_unlocked:
                # OVERRIDE: Student has permission to complete despite no active cycle
                # Determine which cycle they should complete (first incomplete)
                cycle1_complete = obj10_record.get('field_155_raw') not in [None, '', 0]
                cycle2_complete = obj10_record.get('field_161_raw') not in [None, '', 0]
                cycle3_complete = obj10_record.get('field_167_raw') not in [None, '', 0]
                
                if not cycle1_complete:
                    override_cycle = 1
                elif not cycle2_complete:
                    override_cycle = 2
                elif not cycle3_complete:
                    override_cycle = 3
                else:
                    # All cycles complete - no override needed
                    return jsonify({
                        'allowed': False,
                        'cycle': None,
                        'reason': 'all_completed',
                        'message': 'You have completed all three VESPA questionnaires',
                        'userRecord': obj10_record
                    })
                
                app.logger.info(f"[Questionnaire Validate] OVERRIDE ACTIVE - Allowing Cycle {override_cycle} completion")
                
                # Get establishment for academic year
                establishment_id = None
                is_australian = False
                use_standard_year = None
                
                est_field = obj10_record.get('field_133_raw', [])
                if est_field and isinstance(est_field, list) and len(est_field) > 0:
                    est_knack_id = est_field[0].get('id') if isinstance(est_field[0], dict) else est_field[0]
                    if supabase_client:
                        try:
                            est_result = supabase_client.table('establishments').select('id', 'is_australian', 'use_standard_year').eq('knack_id', est_knack_id).execute()
                            if est_result.data:
                                establishment_id = est_result.data[0]['id']
                                is_australian = est_result.data[0].get('is_australian', False)
                                use_standard_year = est_result.data[0].get('use_standard_year')
                        except Exception as e:
                            app.logger.warning(f"Could not fetch establishment: {e}")
                
                academic_year = calculate_academic_year_for_student(
                    is_australian=is_australian,
                    use_standard_year=use_standard_year
                )
                
                return jsonify({
                    'allowed': True,
                    'cycle': override_cycle,
                    'reason': 'cycle_unlocked_override',
                    'message': f'Special access granted - Please complete your Cycle {override_cycle} questionnaire',
                    'academicYear': academic_year,
                    'userRecord': obj10_record,
                    'isOverride': True
                })
            
            # No override - find next upcoming cycle
            future_cycles = []
            for cycle_record in cycle_records:
                start_date_str = cycle_record.get('field_1678')
                if start_date_str:
                    try:
                        start_date = datetime.strptime(start_date_str, '%d/%m/%Y').date()
                        if start_date > today:
                            future_cycles.append({
                                'cycle': int(cycle_record.get('field_1579_raw', 0)),
                                'start_date': start_date,
                                'start_date_formatted': start_date.strftime('%d/%m/%Y')
                            })
                    except:
                        pass
            
            if future_cycles:
                future_cycles.sort(key=lambda x: x['start_date'])
                next_cycle_info = future_cycles[0]
                return jsonify({
                    'allowed': False,
                    'cycle': None,
                    'reason': 'before_start',
                    'message': f"The next questionnaire cycle opens on {next_cycle_info['start_date_formatted']}",
                    'nextStartDate': next_cycle_info['start_date_formatted']
                })
            else:
                return jsonify({
                    'allowed': False,
                    'cycle': None,
                    'reason': 'no_active_cycle',
                    'message': 'There are no questionnaire cycles currently scheduled'
                })
        
        # STEP 4: Check if student has already completed the active cycle
        app.logger.info(f"[Questionnaire Validate] Active cycle is {active_cycle}, checking if student completed it...")
        
        # Fetch student's Object_10 record
        obj10_filters = {
            'match': 'and',
            'rules': [{
                'field': 'field_197',  # Student email
                'operator': 'is',
                'value': email
            }]
        }
        
        obj10_response = requests.get(
            f"https://api.knack.com/v1/objects/object_10/records",
            headers=headers,
            params={'filters': json.dumps(obj10_filters)},
            timeout=30
        )
        
        obj10_record = None
        if obj10_response.ok:
            obj10_records = obj10_response.json().get('records', [])
            if obj10_records:
                obj10_record = obj10_records[0]
        
        # Check completion status for the active cycle using HISTORICAL cycle fields
        # These are permanent and don't get overwritten like current fields (147-152)
        if obj10_record:
            # Map cycle to historical Vision fields (reliable indicator of completion)
            historical_vision_fields = {
                1: 'field_155',  # V1
                2: 'field_161',  # V2
                3: 'field_167'   # V3
            }
            
            vision_field = historical_vision_fields.get(active_cycle)
            vision_value = obj10_record.get(f'{vision_field}_raw') if vision_field else None
            
            current_cycle_field = obj10_record.get('field_146_raw')
            
            app.logger.info(f"[Questionnaire Validate] Checking if Cycle {active_cycle} is complete...")
            app.logger.info(f"[Questionnaire Validate] Historical Vision field ({vision_field}): {vision_value}")
            app.logger.info(f"[Questionnaire Validate] Current cycle field (146): {current_cycle_field}")
            
            # Check if this specific cycle has been completed
            # A cycle is complete if its historical Vision field has a value (not null, not empty, not 0)
            if vision_value is not None and vision_value != '' and vision_value != 0:
                app.logger.info(f"[Questionnaire Validate] Student already completed Cycle {active_cycle} (Vision score: {vision_value})")
                return jsonify({
                    'allowed': False,
                    'cycle': active_cycle,
                    'reason': 'already_completed',
                    'message': f'You have already completed the questionnaire for Cycle {active_cycle}',
                    'userRecord': obj10_record
                })
        
        # Student can take the active cycle
        app.logger.info(f"[Questionnaire Validate] Allowing student to complete Cycle {active_cycle}")
        
        # Get establishment for academic year
        establishment_id = None
        is_australian = False
        use_standard_year = None
        
        if obj10_record:
            est_field = obj10_record.get('field_133_raw', [])
            if est_field and isinstance(est_field, list) and len(est_field) > 0:
                est_knack_id = est_field[0].get('id') if isinstance(est_field[0], dict) else est_field[0]
                if supabase_client:
                    try:
                        est_result = supabase_client.table('establishments').select('id', 'is_australian', 'use_standard_year').eq('knack_id', est_knack_id).execute()
                        if est_result.data:
                            establishment_id = est_result.data[0]['id']
                            is_australian = est_result.data[0].get('is_australian', False)
                            use_standard_year = est_result.data[0].get('use_standard_year')
                    except Exception as e:
                        app.logger.warning(f"Could not fetch establishment: {e}")
        
        academic_year = calculate_academic_year_for_student(
            is_australian=is_australian,
            use_standard_year=use_standard_year
        )
        
        return jsonify({
            'allowed': True,
            'cycle': active_cycle,
            'reason': f'cycle_{active_cycle}_active',
            'message': f'Please complete your Cycle {active_cycle} VESPA questionnaire',
            'academicYear': academic_year,
            'userRecord': obj10_record,
            'cycleInfo': {
                'startDate': active_cycle_record.get('field_1678'),
                'endDate': active_cycle_record.get('field_1580')
            }
        })
        
    except Exception as e:
        app.logger.error(f"[Questionnaire Validate] Error: {e}")
        traceback.print_exc()
        return jsonify({
            'allowed': False,
            'reason': 'error',
            'message': f'Validation error: {str(e)}'
        }), 500

@app.route('/api/vespa/questionnaire/submit', methods=['POST'])
def submit_questionnaire():
    """
    Submit completed VESPA questionnaire
    Dual-writes to both Supabase (primary) and Knack (legacy compatibility)
    """
    try:
        data = request.json
        app.logger.info(f"[Questionnaire Submit] Received submission for {data.get('studentEmail')}")
        
        # Validate required fields
        required_fields = ['studentEmail', 'studentName', 'cycle', 'responses', 'vespaScores', 'academicYear']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        student_email = data['studentEmail']
        student_name = data['studentName']
        cycle = data['cycle']
        responses = data['responses']
        vespa_scores = data['vespaScores']
        category_averages = data.get('categoryAverages', {})
        academic_year = data['academicYear']
        knack_record_id = data.get('knackRecordId')
        
        app.logger.info(f"[Questionnaire Submit] Cycle {cycle} for {student_email}, Academic Year: {academic_year}")
        
        # Get establishment info and staff connections from Knack
        establishment_id = None
        establishment_knack_id = None
        staff_connections = {
            'staff_admin': None,
            'tutor': None,
            'head_of_year': None,
            'subject_teacher': None
        }
        
        # Setup headers for Knack API calls
        headers = {
            'X-Knack-Application-Id': os.getenv('KNACK_APP_ID'),
            'X-Knack-REST-API-Key': os.getenv('KNACK_API_KEY'),
            'Content-Type': 'application/json'
        }
        
        # STEP 1: Get Object_10 record (for establishment + check existing staff connections)
        obj10_record = None
        need_staff_lookup = False  # Flag to determine if we need to look up staff
        
        if knack_record_id:
            try:
                record_response = requests.get(
                    f"https://api.knack.com/v1/objects/object_10/records/{knack_record_id}",
                    headers=headers,
                    timeout=30
                )
                
                if record_response.ok:
                    obj10_record = record_response.json()
                    
                    # Get establishment
                    est_field = obj10_record.get('field_133_raw', [])
                    if est_field and isinstance(est_field, list) and len(est_field) > 0:
                        establishment_knack_id = est_field[0].get('id') if isinstance(est_field[0], dict) else est_field[0]
                        
                        # Map to Supabase establishment_id
                        if supabase_client and establishment_knack_id:
                            try:
                                est_result = supabase_client.table('establishments').select('id').eq('knack_id', establishment_knack_id).execute()
                                if est_result.data:
                                    establishment_id = est_result.data[0]['id']
                            except Exception as e:
                                app.logger.warning(f"Could not map establishment: {e}")
                    
                    # CHECK: Do staff connections already exist in Object_10?
                    existing_staff_admin = obj10_record.get('field_439_raw')
                    existing_tutor = obj10_record.get('field_145_raw')
                    existing_hoy = obj10_record.get('field_429_raw')
                    existing_teacher = obj10_record.get('field_2191_raw')
                    
                    # If ALL connections exist, use them and skip lookup
                    if existing_staff_admin and existing_tutor and existing_hoy and existing_teacher:
                        app.logger.info(f"[Questionnaire Submit] All staff connections exist in Object_10 - skipping lookup")
                        staff_connections['staff_admin'] = existing_staff_admin
                        staff_connections['tutor'] = existing_tutor
                        staff_connections['head_of_year'] = existing_hoy
                        staff_connections['subject_teacher'] = existing_teacher
                        need_staff_lookup = False
                    else:
                        # Some connections missing - need to look them up
                        missing = []
                        if not existing_staff_admin: missing.append('staff_admin')
                        if not existing_tutor: missing.append('tutor')
                        if not existing_hoy: missing.append('head_of_year')
                        if not existing_teacher: missing.append('subject_teacher')
                        
                        app.logger.info(f"[Questionnaire Submit] Missing connections in Object_10: {missing} - will look up")
                        
                        # Store existing ones so we don't overwrite
                        if existing_staff_admin: staff_connections['staff_admin'] = existing_staff_admin
                        if existing_tutor: staff_connections['tutor'] = existing_tutor
                        if existing_hoy: staff_connections['head_of_year'] = existing_hoy
                        if existing_teacher: staff_connections['subject_teacher'] = existing_teacher
                        
                        need_staff_lookup = True
            except Exception as e:
                app.logger.warning(f"[Questionnaire Submit] Could not fetch Object_10 record: {e}")
                need_staff_lookup = True  # If we can't check, look them up to be safe
        else:
            # No Object_10 record yet (new student) - need to look up staff
            app.logger.info(f"[Questionnaire Submit] New student - will look up staff connections")
            need_staff_lookup = True
        
        # STEP 2: Only look up staff from Object_6 if needed
        if need_staff_lookup:
            app.logger.info(f"[Questionnaire Submit] Looking up staff connections in Object_6...")
            try:
                obj6_filters = {
                    'match': 'and',
                    'rules': [{
                        'field': 'field_182',  # Email connection field in Object_6
                        'operator': 'is',
                        'value': student_email
                    }]
                }
                
                obj6_response = requests.get(
                    "https://api.knack.com/v1/objects/object_6/records",
                    headers=headers,
                    params={'filters': json.dumps(obj6_filters)},
                    timeout=30
                )
                
                if obj6_response.ok:
                    obj6_records = obj6_response.json().get('records', [])
                    if obj6_records:
                        obj6_record = obj6_records[0]
                        app.logger.info(f"[Questionnaire Submit] Found Object_6 record for {student_email}")
                        
                        # Only fill in MISSING connections from Object_6
                        if not staff_connections['staff_admin'] and obj6_record.get('field_190_raw'):
                            staff_connections['staff_admin'] = obj6_record['field_190_raw']
                            app.logger.info(f"[Questionnaire Submit] Found staff_admin in Object_6")
                        
                        if not staff_connections['tutor'] and obj6_record.get('field_1682_raw'):
                            staff_connections['tutor'] = obj6_record['field_1682_raw']
                            app.logger.info(f"[Questionnaire Submit] Found tutor in Object_6")
                        
                        if not staff_connections['head_of_year'] and obj6_record.get('field_547_raw'):
                            staff_connections['head_of_year'] = obj6_record['field_547_raw']
                            app.logger.info(f"[Questionnaire Submit] Found head_of_year in Object_6")
                        
                        if not staff_connections['subject_teacher'] and obj6_record.get('field_2177_raw'):
                            staff_connections['subject_teacher'] = obj6_record['field_2177_raw']
                            app.logger.info(f"[Questionnaire Submit] Found subject_teacher in Object_6")
            except Exception as e:
                app.logger.warning(f"[Questionnaire Submit] Could not fetch Object_6 record: {e}")
        
        # ===== PHASE 1: WRITE TO SUPABASE =====
        supabase_success = False
        student_id = None
        
        if supabase_client:
            try:
                app.logger.info(f"[Questionnaire Submit] Writing to Supabase...")
                
                # 1. Upsert student record
                student_data = {
                    'knack_id': knack_record_id or f'temp_{student_email}',  # Temporary ID if no Knack record yet
                    'email': student_email,
                    'name': student_name,
                    'establishment_id': establishment_id,
                    'academic_year': academic_year
                }
                
                student_result = supabase_client.table('students').upsert(
                    student_data,
                    on_conflict='email,academic_year'
                ).execute()
                
                if student_result.data:
                    student_id = student_result.data[0]['id']
                    app.logger.info(f"[Questionnaire Submit] Student upserted: {student_id}")
                else:
                    raise Exception("Failed to upsert student - no data returned")
                
                # 2. Write VESPA scores
                completion_date = datetime.now().strftime('%Y-%m-%d')
                vespa_data = {
                    'student_id': student_id,
                    'student_email': student_email,  # For activities app linking
                    'cycle': cycle,
                    'vision': vespa_scores.get('VISION'),
                    'effort': vespa_scores.get('EFFORT'),
                    'systems': vespa_scores.get('SYSTEMS'),
                    'practice': vespa_scores.get('PRACTICE'),
                    'attitude': vespa_scores.get('ATTITUDE'),
                    'overall': vespa_scores.get('OVERALL'),
                    'completion_date': completion_date,
                    'academic_year': academic_year
                }
                
                supabase_client.table('vespa_scores').upsert(
                    vespa_data,
                    on_conflict='student_id,cycle,academic_year'
                ).execute()
                
                app.logger.info(f"[Questionnaire Submit] VESPA scores written for cycle {cycle}")
                
                # Sync scores to vespa_students cache for activities app
                try:
                    sync_result = supabase_client.rpc(
                        'sync_latest_vespa_scores_to_student',
                        {'p_student_email': student_email}
                    ).execute()
                    app.logger.info(f"[Questionnaire Submit] Synced scores to activities cache: {student_email}")
                except Exception as e:
                    app.logger.warning(f"[Questionnaire Submit] Cache sync failed (non-critical): {e}")
                
                # 3. Write question responses (32 rows)
                response_batch = []
                for question_id, response_value in responses.items():
                    if response_value is not None:
                        response_batch.append({
                            'student_id': student_id,
                            'cycle': cycle,
                            'academic_year': academic_year,
                            'question_id': question_id,
                            'response_value': response_value
                        })
                
                if response_batch:
                    supabase_client.table('question_responses').upsert(
                        response_batch,
                        on_conflict='student_id,cycle,academic_year,question_id'
                    ).execute()
                    
                    app.logger.info(f"[Questionnaire Submit] {len(response_batch)} question responses written")
                
                supabase_success = True
                
            except Exception as e:
                app.logger.error(f"[Questionnaire Submit] Supabase write failed: {e}")
                traceback.print_exc()
                # Continue to Knack write even if Supabase fails
        
        # ===== PHASE 2: DUAL-WRITE TO KNACK =====
        knack_success = False
        
        try:
            app.logger.info(f"[Questionnaire Submit] Dual-writing to Knack...")
            
            headers = {
                'X-Knack-Application-Id': os.getenv('KNACK_APP_ID'),
                'X-Knack-REST-API-Key': os.getenv('KNACK_API_KEY'),
                'Content-Type': 'application/json'
            }
            
            # Prepare Knack update data for Object_10 (VESPA scores)
            completion_date_knack = datetime.now().strftime('%d/%m/%Y')  # UK format DD/MM/YYYY
            
            knack_score_data = {
                'field_146': str(cycle),  # Cycle field
                'field_855': completion_date_knack,  # Completion date
                'field_1679': 'No'  # Reset Cycle Unlocked to No after successful completion
            }
            
            # CRITICAL: Write to CURRENT fields (147-152), not historical cycle fields
            # Knack's conditional formulas will automatically copy to historical fields based on field_146 (cycle)
            current_score_fields = {
                'VISION': 'field_147',
                'EFFORT': 'field_148',
                'SYSTEMS': 'field_149',
                'PRACTICE': 'field_150',
                'ATTITUDE': 'field_151',
                'OVERALL': 'field_152'
            }
            
            app.logger.info(f"[Questionnaire Submit] Writing VESPA scores to CURRENT fields (147-152)")
            for key, field_id in current_score_fields.items():
                score_value = vespa_scores.get(key)
                if score_value is not None:
                    knack_score_data[field_id] = str(score_value)
                    app.logger.info(f"[Questionnaire Submit] {key}: {score_value} → {field_id}")
            
            # Helper to extract connection ID from various formats
            def extract_connection_id(connection_data):
                """Helper to extract ID from connection field (handles different formats)"""
                if not connection_data:
                    return None
                if isinstance(connection_data, list) and len(connection_data) > 0:
                    item = connection_data[0]
                    if isinstance(item, dict):
                        return item.get('id')
                    return item
                return None
            
            # Only add staff connections if we have them (don't send empty values)
            connections_added = []
            
            if staff_connections['staff_admin']:
                staff_admin_id = extract_connection_id(staff_connections['staff_admin'])
                if staff_admin_id:
                    knack_score_data['field_439'] = [staff_admin_id]
                    connections_added.append('staff_admin')
            
            if staff_connections['tutor']:
                tutor_id = extract_connection_id(staff_connections['tutor'])
                if tutor_id:
                    knack_score_data['field_145'] = [tutor_id]
                    connections_added.append('tutor')
            
            if staff_connections['head_of_year']:
                hoy_id = extract_connection_id(staff_connections['head_of_year'])
                if hoy_id:
                    knack_score_data['field_429'] = [hoy_id]
                    connections_added.append('head_of_year')
            
            if staff_connections['subject_teacher']:
                teacher_id = extract_connection_id(staff_connections['subject_teacher'])
                if teacher_id:
                    knack_score_data['field_2191'] = [teacher_id]
                    connections_added.append('subject_teacher')
            
            if connections_added:
                app.logger.info(f"[Questionnaire Submit] Adding staff connections to Object_10: {connections_added}")
            
            # Update or create Object_10 record
            if knack_record_id:
                # Update existing record
                response = requests.put(
                    f"https://api.knack.com/v1/objects/object_10/records/{knack_record_id}",
                    headers=headers,
                    json=knack_score_data,
                    timeout=30
                )
            else:
                # Create new record (include email and name)
                knack_score_data['field_197'] = student_email
                knack_score_data['field_187'] = student_name
                if establishment_knack_id:
                    knack_score_data['field_133'] = [establishment_knack_id]
                
                response = requests.post(
                    "https://api.knack.com/v1/objects/object_10/records",
                    headers=headers,
                    json=knack_score_data,
                    timeout=30
                )
                
                if response.ok:
                    knack_record_id = response.json().get('id')
                    app.logger.info(f"[Questionnaire Submit] Created new Knack Object_10 record: {knack_record_id}")
            
            if not response.ok:
                app.logger.error(f"[Questionnaire Submit] Knack Object_10 write failed: {response.status_code} - {response.text}")
            else:
                app.logger.info(f"[Questionnaire Submit] Knack Object_10 updated successfully")
            
            # Now write to Object_29 (question responses)
            knack_response_data = {
                'field_863': str(cycle),  # Cycle field for Object_29
                'field_856': completion_date_knack  # Completion date for Object_29
            }
            
            # Map each response to BOTH current AND historical Knack fields
            app.logger.info(f"[Questionnaire Submit] Mapping 32 question responses to Object_29 fields")
            
            mapped_count = 0
            for vue_question_id, response_value in responses.items():
                # Look up the question mapping (with alias support)
                question = QUESTION_MAP_BY_ID.get(vue_question_id)
                
                if not question:
                    app.logger.warning(f"[Questionnaire Submit] No mapping found for question ID: {vue_question_id}")
                    continue
                
                # WRITE TO CURRENT FIELD (triggers conditional formulas)
                current_field_id = question.get('currentCycleFieldId')
                if current_field_id:
                    knack_response_data[current_field_id] = str(response_value)
                    mapped_count += 1
                
                # ALSO WRITE TO HISTORICAL FIELD (direct write as backup)
                if cycle == 1:
                    historical_field_id = question.get('fieldIdCycle1')
                elif cycle == 2:
                    historical_field_id = question.get('fieldIdCycle2')
                elif cycle == 3:
                    historical_field_id = question.get('fieldIdCycle3')
                else:
                    historical_field_id = None
                
                if historical_field_id:
                    knack_response_data[historical_field_id] = str(response_value)
                    mapped_count += 1
            
            app.logger.info(f"[Questionnaire Submit] Mapped {mapped_count} fields (current + historical) to Object_29")
            
            # Add VESPA scores to Object_29 (current AND historical fields)
            app.logger.info(f"[Questionnaire Submit] Adding VESPA scores to Object_29...")
            
            # CURRENT VESPA score fields in Object_29
            knack_response_data['field_857'] = str(vespa_scores.get('VISION', ''))      # V current
            knack_response_data['field_858'] = str(vespa_scores.get('EFFORT', ''))      # E current
            knack_response_data['field_859'] = str(vespa_scores.get('SYSTEMS', ''))     # S current
            knack_response_data['field_861'] = str(vespa_scores.get('PRACTICE', ''))    # P current
            knack_response_data['field_860'] = str(vespa_scores.get('ATTITUDE', ''))    # A current
            knack_response_data['field_862'] = str(vespa_scores.get('OVERALL', ''))     # O current
            
            # HISTORICAL VESPA score fields by cycle
            historical_score_fields = {
                1: {
                    'VISION': 'field_1935', 'EFFORT': 'field_1936', 'SYSTEMS': 'field_1937',
                    'PRACTICE': 'field_1938', 'ATTITUDE': 'field_1939', 'OVERALL': 'field_1940'
                },
                2: {
                    'VISION': 'field_1941', 'EFFORT': 'field_1942', 'SYSTEMS': 'field_1943',
                    'PRACTICE': 'field_1944', 'ATTITUDE': 'field_1945', 'OVERALL': 'field_1946'
                },
                3: {
                    'VISION': 'field_1947', 'EFFORT': 'field_1948', 'SYSTEMS': 'field_1949',
                    'PRACTICE': 'field_1950', 'ATTITUDE': 'field_1951', 'OVERALL': 'field_1952'
                }
            }
            
            # Write to historical fields for this cycle
            if cycle in historical_score_fields:
                for score_key, field_id in historical_score_fields[cycle].items():
                    score_value = vespa_scores.get(score_key)
                    if score_value is not None:
                        knack_response_data[field_id] = str(score_value)
            
            app.logger.info(f"[Questionnaire Submit] Added VESPA scores to Object_29 (current: 857-862, historical C{cycle}: {list(historical_score_fields.get(cycle, {}).values())})")
            
            # Link to Object_10 record
            if knack_record_id:
                knack_response_data['field_792'] = [knack_record_id]  # Connection to Object_10
            
            # Add staff connections to Object_29 (only if we have them)
            obj29_connections_added = []
            
            if staff_connections['staff_admin']:
                staff_admin_id = extract_connection_id(staff_connections['staff_admin'])
                if staff_admin_id:
                    knack_response_data['field_2069'] = [staff_admin_id]
                    obj29_connections_added.append('staff_admin')
            
            if staff_connections['tutor']:
                tutor_id = extract_connection_id(staff_connections['tutor'])
                if tutor_id:
                    knack_response_data['field_2070'] = [tutor_id]
                    obj29_connections_added.append('tutor')
            
            if staff_connections['head_of_year']:
                hoy_id = extract_connection_id(staff_connections['head_of_year'])
                if hoy_id:
                    knack_response_data['field_3266'] = [hoy_id]
                    obj29_connections_added.append('head_of_year')
            
            if staff_connections['subject_teacher']:
                teacher_id = extract_connection_id(staff_connections['subject_teacher'])
                if teacher_id:
                    knack_response_data['field_2071'] = [teacher_id]
                    obj29_connections_added.append('subject_teacher')
            
            if obj29_connections_added:
                app.logger.info(f"[Questionnaire Submit] Adding staff connections to Object_29: {obj29_connections_added}")
            
            # CRITICAL: Find and update existing Object_29 record (not create new!)
            # Search by connected Object_10 record (field_792)
            obj29_id = None
            
            if knack_record_id:
                app.logger.info(f"[Questionnaire Submit] Searching for Object_29 record connected to Object_10: {knack_record_id}")
                
                filters = {
                    'match': 'and',
                    'rules': [
                        {
                            'field': 'field_792',
                            'operator': 'is',
                            'value': knack_record_id
                        }
                    ]
                }
                
                obj29_response = requests.get(
                    "https://api.knack.com/v1/objects/object_29/records",
                    headers=headers,
                    params={'filters': json.dumps(filters)},
                    timeout=30
                )
                
                if obj29_response.ok:
                    obj29_records = obj29_response.json().get('records', [])
                    if obj29_records:
                        obj29_id = obj29_records[0]['id']
                        app.logger.info(f"[Questionnaire Submit] Found existing Object_29 record: {obj29_id}")
                    else:
                        app.logger.warning(f"[Questionnaire Submit] No Object_29 record found for Object_10: {knack_record_id}")
                        app.logger.warning(f"[Questionnaire Submit] This student may not have been onboarded properly!")
                else:
                    app.logger.error(f"[Questionnaire Submit] Failed to search Object_29: {obj29_response.status_code}")
            
            # Update or create Object_29 record
            if obj29_id:
                # UPDATE existing record
                response = requests.put(
                    f"https://api.knack.com/v1/objects/object_29/records/{obj29_id}",
                    headers=headers,
                    json=knack_response_data,
                    timeout=30
                )
                app.logger.info(f"[Questionnaire Submit] Updated Object_29 record: {obj29_id}")
            else:
                # CREATE new record (should be rare - only for improperly onboarded students)
                app.logger.warning(f"[Questionnaire Submit] Creating NEW Object_29 record (student not properly onboarded?)")
                response = requests.post(
                    "https://api.knack.com/v1/objects/object_29/records",
                    headers=headers,
                    json=knack_response_data,
                    timeout=30
                )
                
                if response.ok:
                    obj29_id = response.json().get('id')
                    app.logger.info(f"[Questionnaire Submit] Created new Object_29 record: {obj29_id}")
            
            if not response.ok:
                app.logger.error(f"[Questionnaire Submit] Knack Object_29 write failed: {response.status_code} - {response.text}")
                app.logger.error(f"[Questionnaire Submit] Response body: {response.text[:500]}")
            else:
                knack_success = True
                app.logger.info(f"[Questionnaire Submit] Knack Object_29 written successfully")
            
        except Exception as e:
            app.logger.error(f"[Questionnaire Submit] Knack write failed: {e}")
            traceback.print_exc()
        
        # ===== RETURN RESULTS =====
        if supabase_success or knack_success:
            return jsonify({
                'success': True,
                'supabaseWritten': supabase_success,
                'knackWritten': knack_success,
                'studentId': student_id,
                'knackRecordId': knack_record_id,
                'scores': vespa_scores
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Both Supabase and Knack writes failed',
                'supabaseWritten': supabase_success,
                'knackWritten': knack_success
            }), 500
        
    except Exception as e:
        app.logger.error(f"[Questionnaire Submit] Fatal error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== END VESPA QUESTIONNAIRE V2 ENDPOINTS =====

# ===== VESPA REPORT V2 ENDPOINT =====

@app.route('/api/vespa/report/data', methods=['GET'])
def get_report_data():
    """
    Get VESPA report data from Supabase for all cycles
    Returns student info, scores, and question responses
    """
    try:
        email = request.args.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        app.logger.info(f"[Report Data] Fetching report for {email}")
        
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get student record
        # Handle duplicates by finding the MOST RECENT student_id with scores
        student_records = supabase_client.table('students')\
            .select('id, name, email, establishment_id, year_group, group, course, faculty, academic_year, created_at')\
            .eq('email', email)\
            .order('created_at', desc=True)\
            .execute()
        
        if not student_records.data:
            return jsonify({'error': 'Student not found'}), 404
        
        # If multiple student records, find the MOST RECENT one with scores
        student_data = None
        student_id = None
        
        if len(student_records.data) > 1:
            app.logger.warning(f"[Report Data] Found {len(student_records.data)} student records for {email}")
            # Check from most recent to oldest
            for record in student_records.data:
                score_check = supabase_client.table('vespa_scores')\
                    .select('id')\
                    .eq('student_id', record['id'])\
                    .limit(1)\
                    .execute()
                if score_check.data:
                    student_data = record
                    student_id = record['id']
                    app.logger.info(f"[Report Data] Using student_id {student_id} (academic_year: {record.get('academic_year')})")
                    break
        
        # If no duplicate or no scores found, use first (most recent) record
        if not student_data:
            student_data = student_records.data[0]
            student_id = student_data['id']
        
        app.logger.info(f"[Report Data] Using student_id: {student_id} for {email}")
        
        # Get student's Level AND Object_10 record ID from Knack
        student_level = 'Level 3'  # Default
        knack_obj10_id = None  # CRITICAL: Need this for saves!
        student_current_cycle = 1  # Default to Cycle 1
        if supabase_client:
            try:
                # Try to get from Supabase students table first (if we've stored it)
                # Otherwise fetch from Knack
                headers = {
                    'X-Knack-Application-Id': os.getenv('KNACK_APP_ID'),
                    'X-Knack-REST-API-Key': os.getenv('KNACK_API_KEY')
                }
                
                # Search Object_10 by email to get Level AND record ID
                obj10_response = requests.get(
                    "https://api.knack.com/v1/objects/object_10/records",
                    headers=headers,
                    params={'filters': json.dumps({'match': 'and', 'rules': [{'field': 'field_197', 'operator': 'is', 'value': email}]})},
                    timeout=5
                )
                
                if obj10_response.ok:
                    obj10_records = obj10_response.json().get('records', [])
                    if obj10_records:
                        knack_obj10_id = obj10_records[0].get('id')  # CRITICAL: Get Object_10 record ID
                        level_value = obj10_records[0].get('field_568_raw') or obj10_records[0].get('field_568', '')
                        if level_value:
                            student_level = level_value
                        # Get current cycle from Knack (field_146)
                        student_current_cycle_raw = obj10_records[0].get('field_146_raw', '')
                        student_current_cycle = int(student_current_cycle_raw) if student_current_cycle_raw and str(student_current_cycle_raw).isdigit() else 1
                        app.logger.info(f"[Report Data] Student level: {student_level}, Object_10 ID: {knack_obj10_id}, Current Cycle: {student_current_cycle}")
            except Exception as e:
                app.logger.warning(f"Could not fetch student level: {e}")
        
        # Get establishment info (including logo)
        establishment_info = None
        if student_data.get('establishment_id'):
            est_result = supabase_client.table('establishments')\
                .select('name, knack_id')\
                .eq('id', student_data['establishment_id'])\
                .execute()
            
            if est_result.data:
                establishment_info = est_result.data[0]
                
                # Get logo URL from Knack (field_3206)
                if establishment_info.get('knack_id'):
                    try:
                        headers = {
                            'X-Knack-Application-Id': os.getenv('KNACK_APP_ID'),
                            'X-Knack-REST-API-Key': os.getenv('KNACK_API_KEY')
                        }
                        knack_response = requests.get(
                            f"https://api.knack.com/v1/objects/object_2/records/{establishment_info['knack_id']}",
                            headers=headers,
                            timeout=5
                        )
                        if knack_response.ok:
                            knack_record = knack_response.json()
                            logo_url = knack_record.get('field_3206_raw') or knack_record.get('field_3206', '')
                            establishment_info['logoUrl'] = logo_url
                    except Exception as e:
                        app.logger.warning(f"Could not fetch logo: {e}")
        
        # Get VESPA scores for all cycles (most recent per cycle if duplicates exist)
        # Use student_email to get scores across all student_id records (handles multi-year students)
        all_scores_raw = supabase_client.table('vespa_scores')\
            .select('cycle, vision, effort, systems, practice, attitude, overall, completion_date')\
            .eq('student_email', email)\
            .order('completion_date', desc=True)\
            .execute()
        
        # Deduplicate - keep only most recent score per cycle
        scores_by_cycle = {}
        for score in all_scores_raw.data:
            cycle = score['cycle']
            if cycle not in scores_by_cycle:
                scores_by_cycle[cycle] = score
        
        # Convert back to list, sorted by cycle
        scores_result_data = sorted(scores_by_cycle.values(), key=lambda x: x['cycle'])
        
        # Get question responses for all cycles
        # Note: question_responses still uses student_id, so we need to get ALL student_ids for this email
        all_student_ids = [record['id'] for record in student_records.data]
        responses_result = supabase_client.table('question_responses')\
            .select('cycle, question_id, response_value')\
            .in_('student_id', all_student_ids)\
            .execute()
        
        # Organize responses by cycle
        responses_by_cycle = {1: {}, 2: {}, 3: {}}
        for response in responses_result.data:
            cycle = response['cycle']
            question_id = response['question_id']
            value = response['response_value']
            if cycle in responses_by_cycle:
                responses_by_cycle[cycle][question_id] = value
        
        # CRITICAL FIX: Get student responses, goals, and coaching FROM KNACK (not Supabase)
        # Supabase may not be in sync, but Knack is always the source of truth
        student_profile = {}
        
        if knack_obj10_id:
            # Fetch the full Object_10 record from Knack to get all text fields
            try:
                headers = {
                    'X-Knack-Application-Id': os.getenv('KNACK_APP_ID'),
                    'X-Knack-REST-API-Key': os.getenv('KNACK_API_KEY')
                }
                
                knack_record_response = requests.get(
                    f"https://api.knack.com/v1/objects/object_10/records/{knack_obj10_id}",
                    headers=headers,
                    timeout=10
                )
                
                if knack_record_response.ok:
                    record = knack_record_response.json()
                    
                    # Extract responses by cycle (fields 2302, 2303, 2304)
                    for cycle in [1, 2, 3]:
                        field_map = {
                            1: {'response': 'field_2302', 'goals': 'field_2499', 'coaching': 'field_2488'},
                            2: {'response': 'field_2303', 'goals': 'field_2493', 'coaching': 'field_2490'},
                            3: {'response': 'field_2304', 'goals': 'field_2494', 'coaching': 'field_2491'}
                        }
                        
                        # Get response text (strip HTML)
                        response_text = record.get(field_map[cycle]['response'], '') or record.get(field_map[cycle]['response'] + '_raw', '')
                        if response_text:
                            import re
                            response_text = response_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                            response_text = response_text.replace('</p>', '\n\n')
                            response_text = re.sub('<[^<]+?>', '', response_text)
                            response_text = response_text.strip()
                        
                        # Get goals text (strip HTML)
                        goals_text = record.get(field_map[cycle]['goals'], '') or record.get(field_map[cycle]['goals'] + '_raw', '')
                        if goals_text:
                            import re
                            goals_text = goals_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                            goals_text = goals_text.replace('</p>', '\n\n')
                            goals_text = re.sub('<[^<]+?>', '', goals_text)
                            goals_text = goals_text.strip()
                        
                        # Get coaching text (strip HTML)
                        coaching_text = record.get(field_map[cycle]['coaching'], '') or record.get(field_map[cycle]['coaching'] + '_raw', '')
                        if coaching_text:
                            import re
                            coaching_text = coaching_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                            coaching_text = coaching_text.replace('</p>', '\n\n')
                            coaching_text = re.sub('<[^<]+?>', '', coaching_text)
                            coaching_text = coaching_text.strip()
                        
                        student_profile[cycle] = {
                            'response': {'response_text': response_text, 'submitted_at': None} if response_text else None,
                            'goals': {'goal_text': goals_text, 'goal_set_date': None, 'goal_due_date': None} if goals_text else None,
                            'coaching': {'coaching_text': coaching_text, 'coaching_date': None} if coaching_text else None
                        }
                    
                    app.logger.info(f"[Report Data] Fetched text fields from Knack Object_10")
                else:
                    app.logger.warning(f"[Report Data] Could not fetch Knack Object_10 record, using empty profile")
                    for cycle in [1, 2, 3]:
                        student_profile[cycle] = {'response': None, 'goals': None, 'coaching': None}
            except Exception as e:
                app.logger.error(f"[Report Data] Error fetching from Knack: {e}")
                for cycle in [1, 2, 3]:
                    student_profile[cycle] = {'response': None, 'goals': None, 'coaching': None}
        else:
            # No Object_10 ID found, return empty profile
            for cycle in [1, 2, 3]:
                student_profile[cycle] = {'response': None, 'goals': None, 'coaching': None}
        
        # Get coaching content for each score
        coaching_content_map = {}
        
        for score_record in scores_result_data:
            cycle = score_record['cycle']
            coaching_content_map[cycle] = {}
            
            for category in ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude']:
                score_value = score_record.get(category.lower())
                if score_value:
                    # Fetch matching coaching content
                    try:
                        content_result = supabase_client.table('coaching_content')\
                            .select('statement_text, questions, coaching_comments, suggested_tools')\
                            .eq('level', student_level)\
                            .eq('category', category)\
                            .lte('score_min', score_value)\
                            .gte('score_max', score_value)\
                            .execute()
                        
                        if content_result.data:
                            coaching_content_map[cycle][category] = content_result.data[0]
                    except Exception as e:
                        app.logger.warning(f"Could not fetch coaching content for {category}: {e}")
        
        # Build response
        return jsonify({
            'success': True,
            'student': {
                'name': student_data.get('name', ''),
                'email': student_data.get('email', ''),
                'establishment': establishment_info.get('name', '') if establishment_info else '',
                'logoUrl': establishment_info.get('logoUrl', '') if establishment_info else '',
                'yearGroup': student_data.get('year_group', ''),
                'group': student_data.get('group', ''),
                'course': student_data.get('course', ''),
                'faculty': student_data.get('faculty', ''),
                'level': student_level,
                'knackRecordId': knack_obj10_id,  # CRITICAL: Object_10 record ID for saves
                'currentCycle': student_current_cycle  # CRITICAL: Current cycle from Knack field_146
            },
            'scores': scores_result_data,  # Deduplicated scores
            'responses': responses_by_cycle,
            'coachingContent': coaching_content_map,
            'studentProfile': student_profile  # Responses, goals, coaching notes by cycle
        })
        
    except Exception as e:
        app.logger.error(f"[Report Data] Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ===== END VESPA REPORT V2 ENDPOINT =====


# ===== VESPA STAFF OVERVIEW ENDPOINT =====

@app.route('/api/vespa/staff-overview', methods=['GET'])
def get_staff_overview():
    """
    Get VESPA overview data for all students connected to a staff member
    Returns student list with scores, responses, and goals for the current cycle
    
    Staff connections (many-to-many):
    - Staff Admin: Object_10 field_439 → Object_5 field_86 (email)
    - Tutor: Object_10 field_145 → Object_7 field_96 (email)
    - Head of Year: Object_10 field_429 → Object_18 field_417 (email)
    - Subject Teacher: Object_10 field_2191 → Object_78 field_1879 (email)
    """
    try:
        staff_email = request.args.get('email')
        cycle_filter = request.args.get('cycle')  # Optional cycle filter (1, 2, 3, or None for all)
        
        if not staff_email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Parse cycle filter if provided
        selected_cycle = None
        if cycle_filter and cycle_filter.isdigit():
            selected_cycle = int(cycle_filter)
            if selected_cycle not in [1, 2, 3]:
                selected_cycle = None
        
        app.logger.info(f"[Staff Overview] Fetching data for {staff_email}, cycle filter: {selected_cycle}")
        
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Headers for Knack API
        headers = {
            'X-Knack-Application-Id': os.getenv('KNACK_APP_ID'),
            'X-Knack-REST-API-Key': os.getenv('KNACK_API_KEY')
        }
        
        # Step 1: Detect staff role(s) and get staff member info
        staff_info = {
            'name': '',
            'email': staff_email,
            'roles': []
        }
        
        staff_id_mappings = {}
        
        # Check Staff Admin (Object_5)
        try:
            admin_response = requests.get(
                "https://api.knack.com/v1/objects/object_5/records",
                headers=headers,
                params={'filters': json.dumps({'match': 'and', 'rules': [{'field': 'field_86', 'operator': 'is', 'value': staff_email}]})},
                timeout=10
            )
            if admin_response.ok:
                admin_records = admin_response.json().get('records', [])
                if admin_records:
                    staff_info['roles'].append('staff_admin')
                    staff_info['name'] = admin_records[0].get('field_84', '') or admin_records[0].get('field_84_raw', '')
                    staff_id_mappings['staff_admin'] = admin_records[0].get('id')
                    app.logger.info(f"[Staff Overview] Detected Staff Admin role")
        except Exception as e:
            app.logger.warning(f"Could not check Staff Admin role: {e}")
        
        # Check Tutor (Object_7)
        try:
            tutor_response = requests.get(
                "https://api.knack.com/v1/objects/object_7/records",
                headers=headers,
                params={'filters': json.dumps({'match': 'and', 'rules': [{'field': 'field_96', 'operator': 'is', 'value': staff_email}]})},
                timeout=10
            )
            if tutor_response.ok:
                tutor_records = tutor_response.json().get('records', [])
                if tutor_records:
                    staff_info['roles'].append('tutor')
                    if not staff_info['name']:
                        staff_info['name'] = tutor_records[0].get('field_94', '') or tutor_records[0].get('field_94_raw', '')
                    staff_id_mappings['tutor'] = tutor_records[0].get('id')
                    app.logger.info(f"[Staff Overview] Detected Tutor role")
        except Exception as e:
            app.logger.warning(f"Could not check Tutor role: {e}")
        
        # Check Head of Year (Object_18)
        try:
            hoy_response = requests.get(
                "https://api.knack.com/v1/objects/object_18/records",
                headers=headers,
                params={'filters': json.dumps({'match': 'and', 'rules': [{'field': 'field_417', 'operator': 'is', 'value': staff_email}]})},
                timeout=10
            )
            if hoy_response.ok:
                hoy_records = hoy_response.json().get('records', [])
                if hoy_records:
                    staff_info['roles'].append('head_of_year')
                    if not staff_info['name']:
                        staff_info['name'] = hoy_records[0].get('field_415', '') or hoy_records[0].get('field_415_raw', '')
                    staff_id_mappings['head_of_year'] = hoy_records[0].get('id')
                    app.logger.info(f"[Staff Overview] Detected Head of Year role")
        except Exception as e:
            app.logger.warning(f"Could not check Head of Year role: {e}")
        
        # Check Subject Teacher (Object_78)
        try:
            teacher_response = requests.get(
                "https://api.knack.com/v1/objects/object_78/records",
                headers=headers,
                params={'filters': json.dumps({'match': 'and', 'rules': [{'field': 'field_1879', 'operator': 'is', 'value': staff_email}]})},
                timeout=10
            )
            if teacher_response.ok:
                teacher_records = teacher_response.json().get('records', [])
                if teacher_records:
                    staff_info['roles'].append('subject_teacher')
                    if not staff_info['name']:
                        staff_info['name'] = teacher_records[0].get('field_1877', '') or teacher_records[0].get('field_1877_raw', '')
                    staff_id_mappings['subject_teacher'] = teacher_records[0].get('id')
                    app.logger.info(f"[Staff Overview] Detected Subject Teacher role")
        except Exception as e:
            app.logger.warning(f"Could not check Subject Teacher role: {e}")
        
        if not staff_info['roles']:
            return jsonify({'error': 'No staff role found for this email'}), 404
        
        # Step 2: Get all Object_10 (VESPA Results) records connected to this staff member
        # Build filter rules based on detected roles
        filter_rules = []
        
        if 'staff_admin' in staff_info['roles']:
            filter_rules.append({'field': 'field_439', 'operator': 'contains', 'value': staff_id_mappings['staff_admin']})
        
        if 'tutor' in staff_info['roles']:
            filter_rules.append({'field': 'field_145', 'operator': 'contains', 'value': staff_id_mappings['tutor']})
        
        if 'head_of_year' in staff_info['roles']:
            filter_rules.append({'field': 'field_429', 'operator': 'contains', 'value': staff_id_mappings['head_of_year']})
        
        if 'subject_teacher' in staff_info['roles']:
            filter_rules.append({'field': 'field_2191', 'operator': 'contains', 'value': staff_id_mappings['subject_teacher']})
        
        # Build query with OR logic (any matching connection)
        filters = {'match': 'or', 'rules': filter_rules}
        
        app.logger.info(f"[Staff Overview] Fetching students with filters: {json.dumps(filters)}")
        
        # Fetch connected student records from Object_10 with pagination
        try:
            obj10_records = []
            page = 1
            total_pages = 1
            
            # Loop through all pages to get ALL students
            while page <= total_pages:
                app.logger.info(f"[Staff Overview] Fetching page {page}/{total_pages}")
                
                obj10_response = requests.get(
                    "https://api.knack.com/v1/objects/object_10/records",
                    headers=headers,
                    params={
                        'filters': json.dumps(filters),
                        'rows_per_page': 1000,  # Max per page
                        'page': page
                    },
                    timeout=30
                )
                
                if not obj10_response.ok:
                    app.logger.error(f"[Staff Overview] Knack API error on page {page}: {obj10_response.status_code} - {obj10_response.text}")
                    return jsonify({'error': 'Failed to fetch student data from Knack'}), 500
                
                response_data = obj10_response.json()
                page_records = response_data.get('records', [])
                obj10_records.extend(page_records)
                
                # Update total pages from response
                total_pages = response_data.get('total_pages', 1)
                page += 1
                
                app.logger.info(f"[Staff Overview] Page {page-1}: Got {len(page_records)} students, Total so far: {len(obj10_records)}")
            
            app.logger.info(f"[Staff Overview] ✅ Found {len(obj10_records)} total connected students across {total_pages} pages")
            
        except Exception as e:
            app.logger.error(f"[Staff Overview] Error fetching Object_10: {e}")
            return jsonify({'error': f'Failed to query student records: {str(e)}'}), 500
        
        # Step 3: Process each student and get their VESPA data from Supabase
        students_data = []
        filter_sets = {
            'groups': set(),
            'yearGroups': set(),
            'faculties': set(),
            'courses': set(),
            'cycles': set()
        }
        
        for record in obj10_records:
            try:
                # Extract student email from Object_10
                # field_197_raw is a dict with 'email' key, field_197 is the formatted display value (may be HTML)
                email_raw = record.get('field_197_raw', {})
                if isinstance(email_raw, dict):
                    student_email = email_raw.get('email', '')
                else:
                    student_email = record.get('field_197', '')
                
                # Extract student name from field_187_raw (compound field with first/last)
                name_raw = record.get('field_187_raw', {})
                if isinstance(name_raw, dict):
                    first_name = name_raw.get('first', '') or ''
                    last_name = name_raw.get('last', '') or ''
                    student_name = f"{first_name} {last_name}".strip()
                else:
                    # Fallback to field_198 if field_187_raw is not available
                    student_name = record.get('field_198', '') or record.get('field_198_raw', '') or ''
                
                if not student_email or not isinstance(student_email, str):
                    app.logger.warning(f"[Staff Overview] Invalid email for student: {student_name}, email: {student_email}")
                    continue
                
                # Get metadata fields
                group = record.get('field_223', '') or record.get('field_223_raw', '')
                year_group = record.get('field_144', '') or record.get('field_144_raw', '')
                faculty = record.get('field_782', '') or record.get('field_782_raw', '')
                course = record.get('field_2299', '') or record.get('field_2299_raw', '')
                current_cycle_raw = record.get('field_146_raw', '')
                current_cycle = int(current_cycle_raw) if current_cycle_raw and str(current_cycle_raw).isdigit() else 1
                
                # Determine which cycle to show data for
                # If cycle filter is specified, use that; otherwise use current_cycle
                target_cycle = selected_cycle if selected_cycle is not None else current_cycle
                
                # Add to filter sets (add ALL completed cycles, not just current)
                if group:
                    filter_sets['groups'].add(group)
                if year_group:
                    filter_sets['yearGroups'].add(year_group)
                if faculty:
                    filter_sets['faculties'].add(faculty)
                if course:
                    filter_sets['courses'].add(course)
                
                # Add all cycles this student has completed to filter sets
                for cycle_num in range(1, current_cycle + 1):
                    filter_sets['cycles'].add(cycle_num)
                
                # Get VESPA scores from Knack - need to check BOTH current and historical fields
                # Current cycle fields: 147-152 (V, E, S, P, A, Overall)
                # Historical fields: C1=155-160, C2=161-166, C3=167-172
                scores = None
                has_completed_target_cycle = False
                vision = effort = systems = practice = attitude = overall = None
                
                # If target_cycle matches current_cycle, use current fields (147-152)
                # Otherwise use historical fields
                if target_cycle == current_cycle:
                    # Use current cycle fields
                    vision = record.get('field_147_raw')
                    effort = record.get('field_148_raw')
                    systems = record.get('field_149_raw')
                    practice = record.get('field_150_raw')
                    attitude = record.get('field_151_raw')
                    overall = record.get('field_152_raw')
                    app.logger.debug(f"[Staff Overview] {student_name} - Using CURRENT fields for cycle {target_cycle}")
                elif target_cycle == 1:
                    # Use Cycle 1 historical fields
                    vision = record.get('field_155_raw')
                    effort = record.get('field_156_raw')
                    systems = record.get('field_157_raw')
                    practice = record.get('field_158_raw')
                    attitude = record.get('field_159_raw')
                    overall = record.get('field_160_raw')
                elif target_cycle == 2:
                    # Use Cycle 2 historical fields
                    vision = record.get('field_161_raw')
                    effort = record.get('field_162_raw')
                    systems = record.get('field_163_raw')
                    practice = record.get('field_164_raw')
                    attitude = record.get('field_165_raw')
                    overall = record.get('field_166_raw')
                elif target_cycle == 3:
                    # Use Cycle 3 historical fields
                    vision = record.get('field_167_raw')
                    effort = record.get('field_168_raw')
                    systems = record.get('field_169_raw')
                    practice = record.get('field_170_raw')
                    attitude = record.get('field_171_raw')
                    overall = record.get('field_172_raw')
                
                # Check if student has completed this target cycle (has at least one score)
                # Note: We check if ANY score exists, as some students may have partial data
                if vision or effort or systems or practice or attitude:
                    has_completed_target_cycle = True
                    # Calculate overall if not present from individual scores
                    if not overall:
                        score_values = []
                        for s in [vision, effort, systems, practice, attitude]:
                            if s is not None:
                                # Try to convert to float
                                try:
                                    score_values.append(float(s))
                                except (ValueError, TypeError):
                                    pass
                        
                        overall = round(sum(score_values) / len(score_values), 1) if score_values else None
                    
                    scores = {
                        'vision': vision,
                        'effort': effort,
                        'systems': systems,
                        'practice': practice,
                        'attitude': attitude,
                        'overall': overall
                    }
                else:
                    # No scores for this cycle, set to None structure
                    scores = {
                        'vision': None,
                        'effort': None,
                        'systems': None,
                        'practice': None,
                        'attitude': None,
                        'overall': None
                    }
                
                # Debug logging for Alena Ramsey AFTER the check
                if student_name and 'Alena' in student_name:
                    app.logger.info(f"[DEBUG Alena] After check - Target:{target_cycle}, Current:{current_cycle}")
                    app.logger.info(f"  Selected: V={vision}, E={effort}, S={systems}, P={practice}, A={attitude}, O={overall}")
                    app.logger.info(f"  has_completed_target_cycle = {has_completed_target_cycle}")
                    app.logger.info(f"  Will be skipped: {selected_cycle is not None and not has_completed_target_cycle}")
                
                # If cycle filter is active and student hasn't completed that cycle, skip them
                if selected_cycle is not None and not has_completed_target_cycle:
                    app.logger.info(f"[Staff Overview] Skipping {student_name} - no data for cycle {target_cycle}")
                    continue
                
                # For display purposes, student has completed if they have target cycle scores
                has_completed = has_completed_target_cycle
                
                # Get student response for target cycle (fields 2302, 2303, 2304)
                response_text = ''
                if target_cycle == 1:
                    response_text = record.get('field_2302', '') or record.get('field_2302_raw', '')
                elif target_cycle == 2:
                    response_text = record.get('field_2303', '') or record.get('field_2303_raw', '')
                elif target_cycle == 3:
                    response_text = record.get('field_2304', '') or record.get('field_2304_raw', '')
                
                # Strip HTML from response text
                if response_text:
                    import re
                    # Convert <br> and </p> to newlines, then strip all HTML
                    response_text = response_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                    response_text = response_text.replace('</p>', '\n\n')
                    response_text = re.sub('<[^<]+?>', '', response_text)
                    response_text = response_text.strip()
                
                # Get student goals for target cycle (fields 2499, 2493, 2494)
                goals_text = ''
                if target_cycle == 1:
                    goals_text = record.get('field_2499', '') or record.get('field_2499_raw', '')
                elif target_cycle == 2:
                    goals_text = record.get('field_2493', '') or record.get('field_2493_raw', '')
                elif target_cycle == 3:
                    goals_text = record.get('field_2494', '') or record.get('field_2494_raw', '')
                
                # Strip HTML from goals text
                if goals_text:
                    import re
                    # Convert <br> and </p> to newlines, then strip all HTML
                    goals_text = goals_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                    goals_text = goals_text.replace('</p>', '\n\n')
                    goals_text = re.sub('<[^<]+?>', '', goals_text)
                    goals_text = goals_text.strip()
                
                # Get staff coaching comments for target cycle (fields 2488, 2490, 2491)
                coaching_text = ''
                if target_cycle == 1:
                    coaching_text = record.get('field_2488', '') or record.get('field_2488_raw', '')
                elif target_cycle == 2:
                    coaching_text = record.get('field_2490', '') or record.get('field_2490_raw', '')
                elif target_cycle == 3:
                    coaching_text = record.get('field_2491', '') or record.get('field_2491_raw', '')
                
                # Strip HTML from coaching text
                if coaching_text:
                    import re
                    # Convert <br> and </p> to newlines, then strip all HTML
                    coaching_text = coaching_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                    coaching_text = coaching_text.replace('</p>', '\n\n')
                    coaching_text = re.sub('<[^<]+?>', '', coaching_text)
                    coaching_text = coaching_text.strip()
                
                # Build student data object
                student_data = {
                    'id': record.get('id'),
                    'name': student_name,
                    'email': student_email,
                    'group': group,
                    'yearGroup': year_group,
                    'faculty': faculty,
                    'course': course,
                    'currentCycle': current_cycle,
                    'targetCycle': target_cycle,  # Which cycle data is being shown
                    'hasCompleted': has_completed,
                    'scores': scores if scores else {
                        'vision': None,
                        'effort': None,
                        'systems': None,
                        'practice': None,
                        'attitude': None,
                        'overall': None
                    },
                    'response': response_text,
                    'goals': goals_text,
                    'coachingComments': coaching_text,
                    'hasResponse': bool(response_text and response_text.strip()),
                    'hasGoals': bool(goals_text and goals_text.strip()),
                    'hasCoaching': bool(coaching_text and coaching_text.strip())
                }
                
                students_data.append(student_data)
                
            except Exception as e:
                app.logger.warning(f"[Staff Overview] Error processing student {record.get('id')}: {e}")
                continue
        
        # Sort students by name
        students_data.sort(key=lambda x: x.get('name', '').lower())
        
        # Convert filter sets to sorted lists
        filters_data = {
            'groups': sorted(list(filter_sets['groups'])),
            'yearGroups': sorted(list(filter_sets['yearGroups'])),
            'faculties': sorted(list(filter_sets['faculties'])),
            'courses': sorted(list(filter_sets['courses'])),
            'cycles': sorted(list(filter_sets['cycles']))
        }
        
        app.logger.info(f"[Staff Overview] Returning {len(students_data)} students")
        
        # Build response
        return jsonify({
            'success': True,
            'staffMember': staff_info,
            'students': students_data,
            'filters': filters_data
        })
        
    except Exception as e:
        app.logger.error(f"[Staff Overview] Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ===== END VESPA STAFF OVERVIEW ENDPOINT =====

# ===== VESPA REPORT SAVE ENDPOINTS =====

@app.route('/api/vespa/report/save-response', methods=['POST'])
def save_student_response():
    """
    Save student response/reflection (dual-write to Supabase + Knack)
    """
    try:
        data = request.json
        student_email = data.get('studentEmail')
        cycle = data.get('cycle')
        response_text = data.get('responseText', '')
        knack_record_id = data.get('knackRecordId')
        
        if not student_email or not cycle:
            return jsonify({'error': 'studentEmail and cycle are required'}), 400
        
        app.logger.info(f"[Save Response] Saving response for {student_email}, cycle {cycle}")
        
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get student record
        student_records = supabase_client.table('students')\
            .select('id, knack_id, academic_year')\
            .eq('email', student_email)\
            .execute()
        
        if not student_records.data:
            return jsonify({'error': 'Student not found'}), 404
        
        # Use first matching student (or prioritize one with scores if multiple)
        student_data = student_records.data[0]
        student_id = student_data['id']
        academic_year = student_data['academic_year']
        knack_record_id = knack_record_id or student_data['knack_id']
        
        # 1. Write to Supabase
        response_data = {
            'student_id': student_id,
            'cycle': cycle,
            'academic_year': academic_year,
            'response_text': response_text,
            'updated_at': datetime.now().isoformat()
        }
        
        sb_result = supabase_client.table('student_responses').upsert(
            response_data,
            on_conflict='student_id,cycle,academic_year'
        ).execute()
        
        app.logger.info(f"[Save Response] Supabase write successful")
        
        # 2. Dual-write to Knack Object_10
        knack_success = False
        knack_error = None
        
        # Map cycle to Knack field
        field_mapping = {
            1: 'field_2302',
            2: 'field_2303',
            3: 'field_2304'
        }
        
        if cycle in field_mapping:
            try:
                headers = {
                    'X-Knack-Application-Id': KNACK_APP_ID,
                    'X-Knack-REST-API-Key': KNACK_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                knack_payload = {
                    field_mapping[cycle]: response_text
                }
                
                knack_response = requests.put(
                    f"https://api.knack.com/v1/objects/object_10/records/{knack_record_id}",
                    headers=headers,
                    json=knack_payload,
                    timeout=10
                )
                
                if knack_response.ok:
                    knack_success = True
                    app.logger.info(f"[Save Response] Knack write successful")
                else:
                    knack_error = f"Knack API returned {knack_response.status_code}"
                    app.logger.warning(f"[Save Response] Knack write failed: {knack_error}")
                    
            except Exception as e:
                knack_error = str(e)
                app.logger.error(f"[Save Response] Knack write error: {e}")
        
        return jsonify({
            'success': True,
            'supabaseWritten': True,
            'knackWritten': knack_success,
            'knackError': knack_error,
            'submittedAt': sb_result.data[0].get('submitted_at') if sb_result.data else None
        })
        
    except Exception as e:
        app.logger.error(f"[Save Response] Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/vespa/report/save-goals', methods=['POST'])
def save_student_goals():
    """
    Save student goals (dual-write to Supabase + Knack)
    """
    try:
        data = request.json
        student_email = data.get('studentEmail')
        cycle = data.get('cycle')
        goal_text = data.get('goalText', '')
        goal_set_date = data.get('goalSetDate')
        goal_due_date = data.get('goalDueDate')
        knack_record_id = data.get('knackRecordId')
        
        if not student_email or not cycle:
            return jsonify({'error': 'studentEmail and cycle are required'}), 400
        
        app.logger.info(f"[Save Goals] Saving goals for {student_email}, cycle {cycle}")
        
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get student record
        student_records = supabase_client.table('students')\
            .select('id, knack_id, academic_year')\
            .eq('email', student_email)\
            .execute()
        
        if not student_records.data:
            return jsonify({'error': 'Student not found'}), 404
        
        student_data = student_records.data[0]
        student_id = student_data['id']
        academic_year = student_data['academic_year']
        knack_record_id = knack_record_id or student_data['knack_id']
        
        # 1. Write to Supabase
        goals_data = {
            'student_id': student_id,
            'cycle': cycle,
            'academic_year': academic_year,
            'goal_text': goal_text,
            'goal_set_date': goal_set_date,
            'goal_due_date': goal_due_date,
            'updated_at': datetime.now().isoformat()
        }
        
        sb_result = supabase_client.table('student_goals').upsert(
            goals_data,
            on_conflict='student_id,cycle,academic_year'
        ).execute()
        
        app.logger.info(f"[Save Goals] Supabase write successful")
        
        # 2. Dual-write to Knack Object_10
        knack_success = False
        knack_error = None
        
        # Map cycle to Knack fields
        field_mapping = {
            1: {'text': 'field_2499', 'set': 'field_2321', 'due': 'field_2500'},
            2: {'text': 'field_2493', 'set': 'field_2496', 'due': 'field_2497'},
            3: {'text': 'field_2494', 'set': 'field_2497', 'due': 'field_2498'}
        }
        
        if cycle in field_mapping:
            try:
                headers = {
                    'X-Knack-Application-Id': KNACK_APP_ID,
                    'X-Knack-REST-API-Key': KNACK_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                # Convert dates to Knack format (DD/MM/YYYY)
                knack_payload = {
                    field_mapping[cycle]['text']: goal_text
                }
                
                if goal_set_date:
                    # Convert YYYY-MM-DD to DD/MM/YYYY
                    try:
                        date_obj = datetime.strptime(goal_set_date, '%Y-%m-%d')
                        knack_payload[field_mapping[cycle]['set']] = date_obj.strftime('%d/%m/%Y')
                    except:
                        pass
                
                if goal_due_date:
                    try:
                        date_obj = datetime.strptime(goal_due_date, '%Y-%m-%d')
                        knack_payload[field_mapping[cycle]['due']] = date_obj.strftime('%d/%m/%Y')
                    except:
                        pass
                
                knack_response = requests.put(
                    f"https://api.knack.com/v1/objects/object_10/records/{knack_record_id}",
                    headers=headers,
                    json=knack_payload,
                    timeout=10
                )
                
                if knack_response.ok:
                    knack_success = True
                    app.logger.info(f"[Save Goals] Knack write successful")
                else:
                    knack_error = f"Knack API returned {knack_response.status_code}"
                    app.logger.warning(f"[Save Goals] Knack write failed: {knack_error}")
                    
            except Exception as e:
                knack_error = str(e)
                app.logger.error(f"[Save Goals] Knack write error: {e}")
        
        return jsonify({
            'success': True,
            'supabaseWritten': True,
            'knackWritten': knack_success,
            'knackError': knack_error
        })
        
    except Exception as e:
        app.logger.error(f"[Save Goals] Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/vespa/report/save-coaching', methods=['POST'])
def save_staff_coaching():
    """
    Save staff coaching notes (dual-write to Supabase + Knack)
    """
    try:
        data = request.json
        student_email = data.get('studentEmail')
        staff_email = data.get('staffEmail')
        cycle = data.get('cycle')
        coaching_text = data.get('coachingText', '')
        coaching_date = data.get('coachingDate')
        knack_record_id = data.get('knackRecordId')
        
        if not student_email or not cycle:
            return jsonify({'error': 'studentEmail and cycle are required'}), 400
        
        app.logger.info(f"[Save Coaching] Saving coaching for {student_email}, cycle {cycle}")
        
        if not supabase_client:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get student record
        student_records = supabase_client.table('students')\
            .select('id, knack_id, academic_year')\
            .eq('email', student_email)\
            .execute()
        
        if not student_records.data:
            return jsonify({'error': 'Student not found'}), 404
        
        student_data = student_records.data[0]
        student_id = student_data['id']
        academic_year = student_data['academic_year']
        knack_record_id = knack_record_id or student_data['knack_id']
        
        # Get staff_id if staff_email provided
        staff_id = None
        if staff_email:
            staff_records = supabase_client.table('staff_admins')\
                .select('id')\
                .eq('email', staff_email)\
                .execute()
            if staff_records.data:
                staff_id = staff_records.data[0]['id']
        
        # 1. Write to Supabase
        coaching_data = {
            'student_id': student_id,
            'staff_id': staff_id,
            'cycle': cycle,
            'academic_year': academic_year,
            'coaching_text': coaching_text,
            'coaching_date': coaching_date,
            'updated_at': datetime.now().isoformat()
        }
        
        sb_result = supabase_client.table('staff_coaching_notes').upsert(
            coaching_data,
            on_conflict='student_id,cycle,academic_year'
        ).execute()
        
        app.logger.info(f"[Save Coaching] Supabase write successful")
        
        # 2. Dual-write to Knack Object_10
        knack_success = False
        knack_error = None
        
        # Map cycle to Knack fields
        field_mapping = {
            1: {'text': 'field_2488', 'date': 'field_2485'},
            2: {'text': 'field_2490', 'date': 'field_2486'},
            3: {'text': 'field_2491', 'date': 'field_2487'}
        }
        
        if cycle in field_mapping:
            try:
                headers = {
                    'X-Knack-Application-Id': KNACK_APP_ID,
                    'X-Knack-REST-API-Key': KNACK_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                knack_payload = {
                    field_mapping[cycle]['text']: coaching_text
                }
                
                if coaching_date:
                    # Convert YYYY-MM-DD to DD/MM/YYYY
                    try:
                        date_obj = datetime.strptime(coaching_date, '%Y-%m-%d')
                        knack_payload[field_mapping[cycle]['date']] = date_obj.strftime('%d/%m/%Y')
                    except:
                        pass
                
                knack_response = requests.put(
                    f"https://api.knack.com/v1/objects/object_10/records/{knack_record_id}",
                    headers=headers,
                    json=knack_payload,
                    timeout=10
                )
                
                if knack_response.ok:
                    knack_success = True
                    app.logger.info(f"[Save Coaching] Knack write successful")
                else:
                    knack_error = f"Knack API returned {knack_response.status_code}"
                    app.logger.warning(f"[Save Coaching] Knack write failed: {knack_error}")
                    
            except Exception as e:
                knack_error = str(e)
                app.logger.error(f"[Save Coaching] Knack write error: {e}")
        
        return jsonify({
            'success': True,
            'supabaseWritten': True,
            'knackWritten': knack_success,
            'knackError': knack_error
        })
        
    except Exception as e:
        app.logger.error(f"[Save Coaching] Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ===== END VESPA REPORT SAVE ENDPOINTS =====


# ============================================
# ACADEMIC PROFILE ENDPOINTS V2
# Added: November 10, 2025
# Dual-write to Supabase + Knack (Object_112/113)
# ============================================

def get_profile_from_supabase(email, academic_year=None):
    """Query Supabase for academic profile"""
    try:
        app.logger.info(f"[Academic Profile] Querying Supabase for {email}, year: {academic_year}")

        # Helper: coerce json-ish values into clean strings for UI
        def coerce_text(v):
            if v is None:
                return None
            try:
                # Lists: take first element
                if isinstance(v, list):
                    return coerce_text(v[0]) if len(v) > 0 else None
                # Dicts: prefer common display keys
                if isinstance(v, dict):
                    for k in ['identifier', 'name', 'text', 'label', 'value']:
                        if k in v and v[k]:
                            return str(v[k]).strip()
                    # Fallback: stringify dict
                    return json.dumps(v)
                # Everything else
                s = str(v).strip()
                # Treat common placeholders / JS object stringification as missing
                if s in ['', 'N/A', 'n/a', 'NA', 'na', '[object Object]', 'undefined', 'null']:
                    return None
                return s
            except Exception:
                return str(v)
        
        query = supabase_client.table('academic_profiles').select('*').eq('student_email', email)
        
        if academic_year:
            query = query.eq('academic_year', academic_year)
        
        profile_response = query.order('created_at', desc=True).limit(1).execute()
        
        if not profile_response.data:
            app.logger.info(f"[Academic Profile] No Supabase profile found for {email}")
            return None
        
        profile = profile_response.data[0]
        profile_id = profile['id']
        
        app.logger.info(f"[Academic Profile] Found Supabase profile: {profile_id}")

        # Enrich missing fields from students table (source of truth for school/year/tutor group in other parts of app)
        student_row = None
        try:
            student_resp = supabase_client.table('students')\
                .select('name, email, establishment_id, year_group, group, created_at')\
                .eq('email', email)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            if student_resp and student_resp.data:
                student_row = student_resp.data[0]
        except Exception as e:
            app.logger.warning(f"[Academic Profile] Students enrichment lookup failed (non-fatal): {e}")
        
        subjects_response = supabase_client.table('student_subjects')\
            .select('*')\
            .eq('profile_id', profile_id)\
            .order('subject_position')\
            .execute()
        
        app.logger.info(f"[Academic Profile] Found {len(subjects_response.data)} subjects")

        # Resolve school / establishment id
        establishment_id = profile.get('establishment_id') or (student_row.get('establishment_id') if student_row else None)
        school_name = profile.get('establishment_name')
        if not school_name and establishment_id:
            try:
                est_resp = supabase_client.table('establishments')\
                    .select('name')\
                    .eq('id', establishment_id)\
                    .limit(1)\
                    .execute()
                if est_resp and est_resp.data:
                    school_name = est_resp.data[0].get('name')
            except Exception as e:
                app.logger.warning(f"[Academic Profile] Establishment name lookup failed (non-fatal): {e}")

        # Tutor group & year group (avoid [object Object] in UI)
        tutor_group = coerce_text(profile.get('tutor_group')) or coerce_text(student_row.get('group') if student_row else None)
        year_group = coerce_text(profile.get('year_group')) or coerce_text(student_row.get('year_group') if student_row else None)
        student_name = coerce_text(profile.get('student_name')) or coerce_text(student_row.get('name') if student_row else None)

        # School-wide Academic Profile UI defaults (source of truth is staff admin / account manager)
        # These primarily control STUDENT visibility: show/hide MEG & STG (students do not get toggles).
        ui_defaults = {
            'studentsShowMeg': True,
            'studentsShowStg': False,
            'defaultPopulateTargetFromStg': False,
            'updatedAt': None,
            'updatedByEmail': None
        }
        if establishment_id:
            try:
                settings_resp = supabase_client.table('academic_profile_school_settings')\
                    .select('students_show_meg, students_show_stg, default_populate_target_from_stg, updated_at, updated_by_email')\
                    .eq('establishment_id', establishment_id)\
                    .limit(1)\
                    .execute()
                if settings_resp and settings_resp.data:
                    s = settings_resp.data[0]
                    ui_defaults = {
                        'studentsShowMeg': bool(s.get('students_show_meg')) if s.get('students_show_meg') is not None else True,
                        'studentsShowStg': bool(s.get('students_show_stg')) if s.get('students_show_stg') is not None else False,
                        'defaultPopulateTargetFromStg': bool(s.get('default_populate_target_from_stg')) if s.get('default_populate_target_from_stg') is not None else False,
                        'updatedAt': coerce_text(s.get('updated_at')),
                        'updatedByEmail': coerce_text(s.get('updated_by_email'))
                    }
            except Exception as e:
                app.logger.warning(f"[Academic Profile] School settings lookup failed (non-fatal): {e}")
        
        # University offers (optional JSONB column on academic_profiles)
        university_offers = []
        try:
            raw_offers = profile.get('university_offers')
            if isinstance(raw_offers, list):
                university_offers = raw_offers
            elif isinstance(raw_offers, dict):
                # tolerate accidental dict storage
                university_offers = [raw_offers]
            else:
                university_offers = []
        except Exception:
            university_offers = []

        return {
            'student': {
                'email': profile.get('student_email'),
                'name': student_name,
                'yearGroup': year_group,
                'tutorGroup': tutor_group,
                'attendance': profile.get('attendance'),
                'priorAttainment': profile.get('prior_attainment'),
                'centreNumber': profile.get('centre_number'),
                'school': coerce_text(school_name),
                'establishmentId': establishment_id,
                'universityOffers': university_offers
            },
            # For UI: show when this profile was last changed (snapshots touch academic_profiles.updated_at)
            'updatedAt': coerce_text(profile.get('updated_at') or profile.get('created_at')),
            'academicYear': coerce_text(profile.get('academic_year')),
            'uiDefaults': ui_defaults,
            'subjects': [
                {
                    'id': subj.get('id'),
                    'subjectName': subj.get('subject_name'),
                    'examType': subj.get('exam_type'),
                    'examBoard': subj.get('exam_board'),
                    'currentGrade': subj.get('current_grade'),
                    'targetGrade': subj.get('target_grade'),
                    'minimumExpectedGrade': subj.get('minimum_expected_grade'),
                    'subjectTargetGrade': subj.get('subject_target_grade'),
                    'effortGrade': subj.get('effort_grade'),
                    'behaviourGrade': subj.get('behaviour_grade'),
                    'subjectAttendance': subj.get('subject_attendance'),
                    'position': subj.get('subject_position'),
                    'originalRecordId': subj.get('original_record_id')
                }
                for subj in subjects_response.data
            ],
            'profileId': profile_id,
            'academicYear': profile.get('academic_year'),
            'knackRecordId': profile.get('knack_record_id'),
            'updatedAt': profile.get('updated_at'),
            'dataSource': 'supabase'
        }
        
    except Exception as e:
        app.logger.error(f"[Academic Profile] Error querying Supabase: {e}")
        app.logger.error(traceback.format_exc())
        return None


def parse_knack_subject_json(json_string):
    """Parse subject JSON from Knack Object_112 sub1-sub15 fields"""
    if not json_string:
        return None
    
    try:
        if isinstance(json_string, dict):
            return json_string
        
        subject = json.loads(json_string)
        
        if not subject.get('subject'):
            return None
        
        return subject
        
    except json.JSONDecodeError as e:
        app.logger.warning(f"[Academic Profile] Failed to parse subject JSON: {e}")
        return None


def get_profile_from_knack(email):
    """Fallback: Query Knack Object_112 for academic profile"""
    try:
        app.logger.info(f"[Academic Profile] Querying Knack Object_112 for {email}")
        
        # STEP 1: Get account ID from Object_3 (user account)
        # field_3070 is a connection to Object_3, so we need to query Object_3 first
        obj3_filters = json.dumps({
            'match': 'and',
            'rules': [
                {'field': 'field_70', 'operator': 'is', 'value': email}
            ]
        })
        
        obj3_response = requests.get(
            'https://api.knack.com/v1/objects/object_3/records',
            headers={
                'X-Knack-Application-Id': KNACK_APP_ID,
                'X-Knack-REST-API-Key': KNACK_API_KEY
            },
            params={'filters': obj3_filters, 'format': 'raw'},
            timeout=30
        )
        
        if obj3_response.status_code != 200:
            app.logger.warning(f"[Academic Profile] Object_3 query failed: {obj3_response.status_code}")
            return None
        
        obj3_data = obj3_response.json()
        
        if not obj3_data.get('records'):
            app.logger.info(f"[Academic Profile] No Object_3 account found for {email}")
            return None
        
        account_id = obj3_data['records'][0]['id']
        app.logger.info(f"[Academic Profile] Found account ID: {account_id}")
        
        # STEP 2: Query Object_112 by account ID (field_3064 = UserId)
        filters = json.dumps({
            'match': 'and',
            'rules': [
                {'field': 'field_3064', 'operator': 'is', 'value': account_id}
            ]
        })
        
        response = requests.get(
            'https://api.knack.com/v1/objects/object_112/records',
            headers={
                'X-Knack-Application-Id': KNACK_APP_ID,
                'X-Knack-REST-API-Key': KNACK_API_KEY
            },
            params={'filters': filters, 'format': 'raw'},
            timeout=30
        )
        
        if response.status_code != 200:
            app.logger.warning(f"[Academic Profile] Knack API returned {response.status_code}")
            return None
        
        data = response.json()
        
        if not data.get('records'):
            app.logger.info(f"[Academic Profile] No Knack profile found for {email}")
            return None
        
        record = data['records'][0]
        app.logger.info(f"[Academic Profile] Found Knack profile: {record.get('id')}")
        
        subjects = []
        for i in range(1, 16):
            field_key = f'field_{3079 + i}'
            
            if field_key in record:
                subject = parse_knack_subject_json(record[field_key])
                if subject:
                    subjects.append({
                        'id': None,
                        'subjectName': subject.get('subject'),
                        'examType': subject.get('examType'),
                        'examBoard': subject.get('examBoard'),
                        'currentGrade': subject.get('currentGrade'),
                        'targetGrade': subject.get('targetGrade'),
                        'minimumExpectedGrade': subject.get('minimumExpectedGrade'),
                        'subjectTargetGrade': subject.get('subjectTargetGrade'),
                        'effortGrade': subject.get('effortGrade'),
                        'behaviourGrade': subject.get('behaviourGrade'),
                        'subjectAttendance': subject.get('subjectAttendance'),
                        'position': i,
                        'originalRecordId': subject.get('originalRecordId')
                    })
        
        school_name = 'Unknown School'
        establishment_id = None
        
        vespa_customer = record.get('field_3069')
        if vespa_customer:
            if isinstance(vespa_customer, dict):
                school_name = vespa_customer.get('identifier', vespa_customer.get('name', 'Unknown School'))
                establishment_id = vespa_customer.get('id')
            elif isinstance(vespa_customer, list) and len(vespa_customer) > 0:
                school_name = vespa_customer[0].get('identifier', 'Unknown School')
                establishment_id = vespa_customer[0].get('id')
        
        # Parse attendance - field_3076 is text like "93%"
        attendance_raw = record.get('field_3076', '')
        attendance_float = None
        if attendance_raw:
            try:
                # Remove % sign and convert to float
                attendance_str = str(attendance_raw).replace('%', '').strip()
                attendance_float = float(attendance_str) / 100 if attendance_str else None
            except (ValueError, TypeError):
                app.logger.warning(f"[Academic Profile] Could not parse attendance: {attendance_raw}")
        
        return {
            'student': {
                'email': email,
                'name': record.get('field_3066'),
                'yearGroup': record.get('field_3078'),
                'tutorGroup': record.get('field_3077'),
                'attendance': attendance_float,  # Now as 0.93 instead of "93%"
                'priorAttainment': record.get('field_3272'),
                'upn': record.get('field_3137'),
                'uci': record.get('field_3136'),
                'centreNumber': record.get('field_3138'),
                'school': school_name,
                'establishmentId': establishment_id
            },
            'subjects': subjects,
            'knackRecordId': record.get('id'),
            'academicYear': None,
            'dataSource': 'knack'
        }
        
    except Exception as e:
        app.logger.error(f"[Academic Profile] Error querying Knack: {e}")
        app.logger.error(traceback.format_exc())
        return None


def sync_subject_to_knack(subject_data, object_112_record_id, position):
    """Update subject in Knack Object_112 + Object_113"""
    try:
        subject_json = {
            'subject': subject_data.get('subjectName'),
            'examType': subject_data.get('examType'),
            'examBoard': subject_data.get('examBoard'),
            'currentGrade': subject_data.get('currentGrade'),
            'targetGrade': subject_data.get('targetGrade'),
            'minimumExpectedGrade': subject_data.get('minimumExpectedGrade'),
            'subjectTargetGrade': subject_data.get('subjectTargetGrade'),
            'effortGrade': subject_data.get('effortGrade'),
            'behaviourGrade': subject_data.get('behaviourGrade'),
            'subjectAttendance': subject_data.get('subjectAttendance'),
            'originalRecordId': subject_data.get('originalRecordId')
        }
        
        field_id = f'field_{3079 + position}'
        
        update_data = {
            field_id: json.dumps(subject_json)
        }
        
        response = requests.put(
            f'{KNACK_API_URL}/objects/object_112/records/{object_112_record_id}',
            headers={
                'X-Knack-Application-Id': KNACK_APP_ID,
                'X-Knack-REST-API-Key': KNACK_API_KEY,
                'Content-Type': 'application/json'
            },
            json=update_data
        )
        
        if response.status_code not in [200, 201]:
            app.logger.warning(f"[Academic Profile] Knack Object_112 update failed: {response.status_code}")
            return False
        
        if subject_data.get('originalRecordId'):
            object_113_update = {
                'field_3132': subject_data.get('currentGrade', ''),
                'field_3135': subject_data.get('targetGrade', ''),
                'field_3133': subject_data.get('effortGrade', ''),
                'field_3134': subject_data.get('behaviourGrade', ''),
                'field_3186': subject_data.get('subjectAttendance', '')
            }
            
            obj_113_response = requests.put(
                f'{KNACK_API_URL}/objects/object_113/records/{subject_data["originalRecordId"]}',
                headers={
                    'X-Knack-Application-Id': KNACK_APP_ID,
                    'X-Knack-REST-API-Key': KNACK_API_KEY,
                    'Content-Type': 'application/json'
                },
                json=object_113_update
            )
            
            if obj_113_response.status_code not in [200, 201]:
                app.logger.warning(f"[Academic Profile] Knack Object_113 update failed: {obj_113_response.status_code}")
        
        return True
        
    except Exception as e:
        app.logger.error(f"[Academic Profile] Error syncing subject to Knack: {e}")
        return False


@app.route('/api/academic-profile/<email>', methods=['GET'])
def get_academic_profile(email):
    """Get student academic profile with subjects"""
    try:
        source = request.args.get('source', 'supabase')
        academic_year = request.args.get('academic_year')
        
        app.logger.info(f"[Academic Profile] GET request for {email}, source: {source}")
        
        cache_key = f'academic_profile:{email}:{academic_year or "current"}'
        
        if CACHE_ENABLED:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    app.logger.info(f"[Academic Profile] Cache hit for {email}")
                    return jsonify(pickle.loads(cached))
            except Exception as cache_error:
                app.logger.warning(f"[Academic Profile] Cache error: {cache_error}")
        
        profile_data = None
        
        if SUPABASE_ENABLED and source == 'supabase':
            profile_data = get_profile_from_supabase(email, academic_year)
        
        if not profile_data:
            app.logger.info(f"[Academic Profile] Falling back to Knack for {email}")
            profile_data = get_profile_from_knack(email)
        
        if not profile_data:
            return jsonify({
                'success': False,
                'error': 'Profile not found',
                'message': 'No academic profile found for this student'
            }), 404
        
        response_data = {
            'success': True,
            'student': profile_data['student'],
            'subjects': profile_data['subjects'],
            'dataSource': profile_data.get('dataSource', 'unknown'),
            # Keep legacy key but also include updatedAt (frontend expects it)
            'lastUpdated': profile_data.get('updatedAt'),
            'updatedAt': profile_data.get('updatedAt'),
            'academicYear': profile_data.get('academicYear')
        }
        
        if CACHE_ENABLED:
            try:
                redis_client.setex(
                    cache_key,
                    CACHE_TTL.get('academic_profile', 300),
                    pickle.dumps(response_data)
                )
            except Exception as cache_error:
                app.logger.warning(f"[Academic Profile] Cache write error: {cache_error}")
        
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"[Academic Profile] Error in get_academic_profile: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/academic-profile/<email>/university-offers', methods=['PUT'])
def update_academic_profile_university_offers(email):
    """Update university offers (JSON) on academic_profiles.
    
    Body:
      {
        "academicYear": "2025/2026" (optional),
        "offers": [
          { universityName, courseTitle, offer, ucasPoints, ranking }
        ]
      }
    """
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year')
        offers_in = payload.get('offers') or payload.get('universityOffers') or []

        if offers_in is None:
            offers_in = []
        if not isinstance(offers_in, list):
            return jsonify({'success': False, 'error': 'offers must be an array'}), 400

        # Normalize + validate
        normalized = []
        for o in offers_in:
            if not isinstance(o, dict):
                continue
            uni = str(o.get('universityName') or o.get('university_name') or '').strip()
            course = str(o.get('courseTitle') or o.get('course_title') or '').strip()
            course_link = str(o.get('courseLink') or o.get('course_link') or '').strip()
            offer_txt = str(o.get('offer') or o.get('offerText') or '').strip()
            ucas_raw = o.get('ucasPoints') if 'ucasPoints' in o else o.get('ucas_points')
            ranking_raw = o.get('ranking') if 'ranking' in o else o.get('rank')

            if not uni and not course and not course_link and not offer_txt and (ucas_raw is None or str(ucas_raw).strip() == '') and (ranking_raw is None or str(ranking_raw).strip() == ''):
                continue

            ucas_points = None
            if ucas_raw is not None and str(ucas_raw).strip() != '':
                try:
                    ucas_points = int(float(str(ucas_raw).strip()))
                except Exception:
                    return jsonify({'success': False, 'error': f'Invalid UCAS points value: {ucas_raw}'}), 400

            ranking = None
            if ranking_raw is not None and str(ranking_raw).strip() != '':
                try:
                    ranking = int(float(str(ranking_raw).strip()))
                except Exception:
                    return jsonify({'success': False, 'error': f'Invalid ranking value: {ranking_raw}'}), 400
                if ranking < 1 or ranking > 5:
                    return jsonify({'success': False, 'error': 'Ranking must be between 1 and 5'}), 400

            normalized.append({
                'universityName': uni,
                'courseTitle': course,
                'courseLink': course_link,
                'offer': offer_txt,
                'ucasPoints': ucas_points,
                'ranking': ranking
            })

        if len(normalized) > 5:
            return jsonify({'success': False, 'error': 'Maximum 5 university offers allowed'}), 400

        # Assign missing rankings (first available 1..5)
        used = set([o.get('ranking') for o in normalized if o.get('ranking') is not None])
        for o in normalized:
            if o.get('ranking') is None:
                for r in [1, 2, 3, 4, 5]:
                    if r not in used:
                        o['ranking'] = r
                        used.add(r)
                        break

        # Ensure unique rankings if any duplicates remain
        ranks = [o.get('ranking') for o in normalized if o.get('ranking') is not None]
        if len(ranks) != len(set(ranks)):
            return jsonify({'success': False, 'error': 'Each offer must have a unique ranking (1-5).'}), 400

        # Locate target profile row
        q = supabase_client.table('academic_profiles').select('id').eq('student_email', email)
        if academic_year:
            q = q.eq('academic_year', academic_year)
        profile_resp = q.order('created_at', desc=True).limit(1).execute()
        if not profile_resp or not profile_resp.data:
            return jsonify({'success': False, 'error': 'Academic profile not found'}), 404

        profile_id = profile_resp.data[0]['id']

        # Persist (requires column academic_profiles.university_offers JSONB)
        update_resp = supabase_client.table('academic_profiles')\
            .update({
                'university_offers': normalized,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', profile_id)\
            .execute()

        if not update_resp:
            return jsonify({'success': False, 'error': 'Update failed'}), 500

        # Clear cache for this student
        if CACHE_ENABLED:
            try:
                cache_pattern = f'academic_profile:{email}:*'
                for key in redis_client.scan_iter(match=cache_pattern):
                    redis_client.delete(key)
            except Exception as cache_error:
                app.logger.warning(f"[Academic Profile] Cache clear error (offers): {cache_error}")

        return jsonify({'success': True, 'profileId': str(profile_id), 'offers': normalized})

    except Exception as e:
        app.logger.error(f"[Academic Profile] Error in update_academic_profile_university_offers: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/academic-profile/<email>/ucas-application', methods=['GET'])
def get_ucas_application(email):
    """
    Fetch UCAS Application (Supabase only)
    Query string:
      - academic_year (optional)
    Returns:
      { success: true, data: { answers, selectedCourseKey, requirementsByCourse, staffComments } | null }
    """
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        academic_year = request.args.get('academic_year') or 'current'
        cache_key = f'ucas_application:{email}:{academic_year}'

        if CACHE_ENABLED:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return jsonify(pickle.loads(cached))
            except Exception as cache_error:
                app.logger.warning(f"[UCAS Application] Cache error: {cache_error}")

        resp = supabase_client.table('ucas_applications')\
            .select('*')\
            .eq('student_email', email)\
            .eq('academic_year', academic_year)\
            .order('updated_at', desc=True)\
            .limit(1)\
            .execute()

        if not resp or not resp.data:
            data_out = {'success': True, 'data': None}
        else:
            row = resp.data[0]
            data_out = {
                'success': True,
                'data': {
                    'answers': row.get('answers') or {},
                    'selectedCourseKey': row.get('selected_course_key'),
                    'requirementsByCourse': row.get('requirements_by_course') or {},
                    'staffComments': row.get('staff_comments') or [],
                    'statementCompletedAt': row.get('statement_completed_at') or None
                }
            }

        if CACHE_ENABLED:
            try:
                redis_client.setex(cache_key, CACHE_TTL.get('academic_profile', 300), pickle.dumps(data_out))
            except Exception as cache_error:
                app.logger.warning(f"[UCAS Application] Cache write error: {cache_error}")

        return jsonify(data_out)

    except Exception as e:
        app.logger.error(f"[UCAS Application] Error in get_ucas_application: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/academic-profile/<email>/ucas-application', methods=['PUT'])
def save_ucas_application(email):
    """
    Save UCAS Application (student-only writes)
    Body:
      {
        academicYear?: "2025/2026",
        selectedCourseKey?: string|null,
        answers: { q1, q2, q3 },
        requirementsByCourse?: object
      }
    Validation:
      - total chars across q1+q2+q3: 350..4000 (inclusive)
    """
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        role_hint = (request.headers.get('X-User-Role') or request.headers.get('x-user-role') or '').strip().lower()
        is_student_hint = role_hint in ['student', 'pupil', 'learner']
        if not is_student_hint:
            return jsonify({'success': False, 'error': 'Only students can edit the UCAS Application'}), 403

        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year') or 'current'
        selected_course_key = payload.get('selectedCourseKey')
        answers = payload.get('answers') or {}
        requirements = payload.get('requirementsByCourse') or payload.get('requirements_by_course') or {}

        if not isinstance(answers, dict):
            return jsonify({'success': False, 'error': 'answers must be an object'}), 400
        if requirements is None:
            requirements = {}
        if not isinstance(requirements, dict):
            return jsonify({'success': False, 'error': 'requirementsByCourse must be an object'}), 400

        q1 = str(answers.get('q1') or '')
        q2 = str(answers.get('q2') or '')
        q3 = str(answers.get('q3') or '')
        total = len(q1) + len(q2) + len(q3)
        if total < 350:
            return jsonify({'success': False, 'error': 'Minimum 350 characters total required'}), 400
        if total > 4000:
            return jsonify({'success': False, 'error': 'Maximum 4000 characters total exceeded'}), 400

        record = {
            'student_email': email,
            'academic_year': academic_year,
            'answers': {'q1': q1, 'q2': q2, 'q3': q3},
            'selected_course_key': selected_course_key,
            'requirements_by_course': requirements,
            'updated_at': datetime.utcnow().isoformat()
        }

        existing = supabase_client.table('ucas_applications')\
            .select('id, staff_comments')\
            .eq('student_email', email)\
            .eq('academic_year', academic_year)\
            .order('updated_at', desc=True)\
            .limit(1)\
            .execute()

        if existing and existing.data:
            row_id = existing.data[0]['id']
            # Preserve comments
            record['staff_comments'] = existing.data[0].get('staff_comments') or []
            supabase_client.table('ucas_applications').update(record).eq('id', row_id).execute()
        else:
            supabase_client.table('ucas_applications').insert(record).execute()

        # Clear cache
        if CACHE_ENABLED:
            try:
                cache_key = f'ucas_application:{email}:{academic_year}'
                redis_client.delete(cache_key)
            except Exception as cache_error:
                app.logger.warning(f"[UCAS Application] Cache clear error: {cache_error}")

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"[UCAS Application] Error in save_ucas_application: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/academic-profile/<email>/ucas-application/mark-complete', methods=['POST'])
def mark_ucas_statement_complete(email):
    """
    Student marks their UCAS personal statement complete.
    This is separate from the teacher reference workflow.
    Best-effort: triggers email notification to UCAS admins for the establishment.
    """
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500
        if not _is_student_request():
            return jsonify({'success': False, 'error': 'Only students can mark complete'}), 403

        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year') or 'current'
        now_iso = datetime.utcnow().isoformat()

        # Upsert UCAS application row (in case student marks complete before first save)
        wrote_db = True
        try:
            existing = supabase_client.table('ucas_applications')\
                .select('id')\
                .eq('student_email', email)\
                .eq('academic_year', academic_year)\
                .order('updated_at', desc=True)\
                .limit(1)\
                .execute()

            if existing and existing.data:
                row_id = existing.data[0]['id']
                supabase_client.table('ucas_applications').update({
                    'statement_completed_at': now_iso,
                    'statement_completed_by': email,
                    'updated_at': now_iso
                }).eq('id', row_id).execute()
            else:
                supabase_client.table('ucas_applications').insert({
                    'student_email': email,
                    'academic_year': academic_year,
                    'answers': {},
                    'requirements_by_course': {},
                    'staff_comments': [],
                    'statement_completed_at': now_iso,
                    'statement_completed_by': email,
                    'updated_at': now_iso
                }).execute()
        except Exception as write_err:
            wrote_db = False
            app.logger.warning(f"[UCAS Application] Could not persist statement completion (schema missing?): {write_err}")

        # Clear cache
        if CACHE_ENABLED:
            try:
                cache_key = f'ucas_application:{email}:{academic_year}'
                redis_client.delete(cache_key)
            except Exception as cache_error:
                app.logger.warning(f"[UCAS Application] Cache clear error (mark-complete): {cache_error}")

        # Best-effort notifications (admins configured per establishment)
        try:
            est_id = _get_establishment_id_for_student(email, academic_year)
            admin_emails = []
            if est_id:
                s = supabase_client.table('establishment_settings').select('ucas_reference_admin_emails').eq('establishment_id', est_id).limit(1).execute()
                if s and s.data:
                    admin_emails = s.data[0].get('ucas_reference_admin_emails') or []
                    if isinstance(admin_emails, str):
                        admin_emails = []
            for a in (admin_emails or []):
                _send_email_sendgrid(
                    str(a).strip(),
                    f"UCAS personal statement marked complete: {email}",
                    f"The student has marked their UCAS personal statement complete.\nStudent: {email}\nAcademic year: {academic_year}"
                )
        except Exception as notify_err:
            app.logger.info(f"[UCAS Application] Notify skipped: {notify_err}")

        out = {'success': True, 'data': {'statementCompletedAt': now_iso}}
        if not wrote_db:
            out['warning'] = 'Could not persist completion flag (missing DB columns?).'
        return jsonify(out)
    except Exception as e:
        app.logger.error(f"[UCAS Application] mark-complete error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/academic-profile/<email>/ucas-application/comment', methods=['POST'])
def add_ucas_application_comment(email):
    """
    Add a staff comment (staff-only)
    Body:
      { academicYear?: "...", staffEmail?: "...", comment: "..." }
    Returns updated staffComments array.
    """
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        role_hint = (request.headers.get('X-User-Role') or request.headers.get('x-user-role') or '').strip().lower()
        is_student_hint = role_hint in ['student', 'pupil', 'learner']
        if is_student_hint:
            return jsonify({'success': False, 'error': 'Students cannot add comments'}), 403

        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year') or 'current'
        staff_email = (payload.get('staffEmail') or '').strip()
        comment = (payload.get('comment') or '').strip()
        if not comment:
            return jsonify({'success': False, 'error': 'comment is required'}), 400
        if len(comment) > 2000:
            return jsonify({'success': False, 'error': 'comment is too long (max 2000 chars)'}), 400

        existing = supabase_client.table('ucas_applications')\
            .select('*')\
            .eq('student_email', email)\
            .eq('academic_year', academic_year)\
            .order('updated_at', desc=True)\
            .limit(1)\
            .execute()

        if existing and existing.data:
            row = existing.data[0]
            row_id = row['id']
            staff_comments = row.get('staff_comments') or []
        else:
            row_id = None
            staff_comments = []

        new_comment = {
            'id': str(uuid.uuid4()),
            'staffEmail': staff_email or None,
            'comment': comment,
            'createdAt': datetime.utcnow().isoformat()
        }
        staff_comments = staff_comments + [new_comment]

        if row_id:
            supabase_client.table('ucas_applications').update({
                'staff_comments': staff_comments,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', row_id).execute()
        else:
            supabase_client.table('ucas_applications').insert({
                'student_email': email,
                'academic_year': academic_year,
                'answers': {},
                'selected_course_key': None,
                'requirements_by_course': {},
                'staff_comments': staff_comments,
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

        if CACHE_ENABLED:
            try:
                cache_key = f'ucas_application:{email}:{academic_year}'
                redis_client.delete(cache_key)
            except Exception as cache_error:
                app.logger.warning(f"[UCAS Application] Cache clear error (comment): {cache_error}")

        return jsonify({'success': True, 'data': {'staffComments': staff_comments}})

    except Exception as e:
        app.logger.error(f"[UCAS Application] Error in add_ucas_application_comment: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


UCAS_VIRTUAL_TUTOR_NAME = "Virtual Tutor"

UCAS_COACH_PROMPT = """You are UCAS Coach, a drafting guide for students completing the UCAS personal statement (3-question format).
Your job is to help the student think, choose evidence, and improve clarity — NOT to write the statement for them.

IMPORTANT (product requirement): Do NOT mention "AI", "model", "ChatGPT", "OpenAI", "prompt", or anything similar. Just act like a supportive tutor.

CORE RULES (non-negotiable)
1) Do NOT write the student’s UCAS answers for them. Do NOT produce a complete answer to any UCAS question.
2) You may NOT generate more than:
   - 6 bullet points of content ideas per UCAS question, OR
   - a short outline (max 8 bullets total), OR
   - micro-examples: up to 2 sample sentences maximum, clearly labelled as “example phrasing” and generic enough that the student must rewrite them.
3) If the student asks you to “write it for me”, “finish it”, “make it perfect”, or gives too little content, refuse politely and switch to coaching:
   - Ask 3–6 targeted questions
   - Offer a structure and what evidence to include
   - Provide feedback on what they have (if they share a draft)
4) Keep the student’s voice. Don’t add achievements they didn’t mention. Don’t invent facts.
5) Encourage specificity and evidence. Prefer “show, not tell” (what they did, what they learned, how it links to the course).
6) Never use over-confident claims (“always”, “best”, “perfect”). Keep it realistic and grounded.
7) If the student provides a draft, you may:
   - critique it using clear, plain language (Course-fit, Evidence, Reflection, Specificity, Structure, Style)
   - suggest edits as “Replace X with something like Y”, but do not rewrite the whole paragraph
   - propose a “next sentence” prompt (a sentence starter), not the sentence itself
8) Always end with an action the student must do next (e.g., “Add one specific example of…”, “Rewrite this line to include…”).

CHARACTER GUIDANCE (app rules)
- Total limit is 4,000 characters across all answers combined.
- Minimum is 350 characters total across all answers combined.

OUTPUT FORMAT (keep it short and practical)
- Do NOT use markdown headings like "###" or "####".
- Do NOT use the word "rubric".
- Use plain headings exactly like:
  Overall
  Q1: Why this course?
  Q2: How studies prepared you
  Q3: Outside education
  Next steps
- Under each heading, use short bullet points (•), max 4 bullets per section.
- If there is no draft, ask 3–6 thoughtful questions and give a tiny outline (max 8 bullets total).
"""

def _is_student_request():
    role_hint = (request.headers.get('X-User-Role') or request.headers.get('x-user-role') or '').strip().lower()
    return role_hint in ['student', 'pupil', 'learner']

def _build_ucas_feedback_user_prompt(payload):
    payload = payload or {}
    answers = payload.get('answers') or {}
    q1 = str(answers.get('q1') or '')
    q2 = str(answers.get('q2') or '')
    q3 = str(answers.get('q3') or '')
    total_chars = len(q1) + len(q2) + len(q3)

    course = payload.get('course') or {}
    course_bits = []
    if isinstance(course, dict):
        uni = str(course.get('universityName') or '').strip()
        title = str(course.get('courseTitle') or '').strip()
        offer = str(course.get('offer') or '').strip()
        pts = course.get('ucasPoints')
        if uni or title:
            course_bits.append(f"Course: {uni} — {title}".strip(' —'))
        if offer:
            course_bits.append(f"Offer requirement (grade): {offer}")
        if pts is not None and str(pts).strip() != '':
            course_bits.append(f"Offer requirement (UCAS points): {pts}")

    if total_chars == 0:
        return "\n".join([
            "The student has not written any draft yet.",
            *(course_bits or []),
            "Task: Ask thoughtful questions to help them start (do NOT write answers).",
            "Ask 3–6 questions and give a tiny outline (max 8 bullets total)."
        ])

    return "\n".join([
        "Please give tutoring-style feedback to improve this UCAS 3-question statement draft.",
        *(course_bits or []),
        f"Total characters (all answers combined): {total_chars} (limit 4000; minimum 350).",
        "",
        "Draft Q1:",
        q1 or "[empty]",
        "",
        "Draft Q2:",
        q2 or "[empty]",
        "",
        "Draft Q3:",
        q3 or "[empty]",
        "",
        "Remember: Do NOT write the statement. Provide structure, targeted questions, and specific improvement suggestions."
    ])

def _call_openai_for_ucas_feedback(user_prompt):
    if not OPENAI_API_KEY:
        raise ApiError("OPENAI_API_KEY not configured", 503)
    try:
        import openai
        openai.api_key = OPENAI_API_KEY

        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": UCAS_COACH_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4,
            max_tokens=750
        )
        text = (resp.choices[0].message.get('content') or '').strip()
        return text
    except ApiError:
        raise
    except Exception as e:
        app.logger.error(f"[UCAS Feedback] OpenAI call failed: {e}")
        app.logger.error(traceback.format_exc())
        raise ApiError("Feedback generation failed", 500)

@app.route('/api/academic-profile/<email>/ucas-application/feedback', methods=['POST'])
def generate_ucas_feedback(email):
    """
    Generate tutoring-style feedback for the UCAS application draft.
    Student-only (uses X-User-Role header as a best-effort permission hint).
    """
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        if not _is_student_request():
            return jsonify({'success': False, 'error': 'Only students can request feedback'}), 403

        payload = request.get_json() or {}
        # academicYear is optional; we keep it for future-proofing even if unused here
        _ = payload.get('academicYear') or request.args.get('academic_year') or 'current'

        user_prompt = _build_ucas_feedback_user_prompt(payload)
        feedback = _call_openai_for_ucas_feedback(user_prompt)

        # Safety: ensure we return something usable and not huge, and keep formatting plain.
        feedback = (feedback or '').strip()
        # Strip markdown-style heading markers defensively
        try:
            import re
            feedback = re.sub(r'(?m)^\s*#{1,6}\s*', '', feedback)
            feedback = feedback.replace('Rubric:', 'Quick check:')
        except Exception:
            pass
        if len(feedback) > 6000:
            feedback = feedback[:6000].rstrip() + "…"

        return jsonify({'success': True, 'data': {'feedback': feedback}})
    except ApiError as ae:
        return jsonify({'success': False, 'error': str(ae)}), ae.status_code
    except Exception as e:
        app.logger.error(f"[UCAS Feedback] Error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/academic-profile/<email>/ucas-application/virtual-tutor-comment', methods=['POST'])
def add_virtual_tutor_comment(email):
    """
    Add generated feedback as a tutor comment under "Virtual Tutor" (student-initiated).
    """
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        if not _is_student_request():
            return jsonify({'success': False, 'error': 'Only students can add Virtual Tutor comments'}), 403

        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year') or 'current'
        comment = (payload.get('comment') or payload.get('feedback') or '').strip()
        if not comment:
            return jsonify({'success': False, 'error': 'comment is required'}), 400
        # Virtual Tutor feedback can be longer than staff comments; keep it readable but allow more room.
        if len(comment) > 6000:
            return jsonify({'success': False, 'error': 'comment is too long (max 6000 chars)'}), 400

        existing = supabase_client.table('ucas_applications')\
            .select('*')\
            .eq('student_email', email)\
            .eq('academic_year', academic_year)\
            .order('updated_at', desc=True)\
            .limit(1)\
            .execute()

        if existing and existing.data:
            row = existing.data[0]
            row_id = row['id']
            staff_comments = row.get('staff_comments') or []
        else:
            row_id = None
            staff_comments = []

        new_comment = {
            'id': str(uuid.uuid4()),
            'staffEmail': UCAS_VIRTUAL_TUTOR_NAME,
            'comment': comment,
            'createdAt': datetime.utcnow().isoformat(),
            'source': 'virtual_tutor'
        }
        staff_comments = staff_comments + [new_comment]

        if row_id:
            supabase_client.table('ucas_applications').update({
                'staff_comments': staff_comments,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', row_id).execute()
        else:
            supabase_client.table('ucas_applications').insert({
                'student_email': email,
                'academic_year': academic_year,
                'answers': {},
                'selected_course_key': None,
                'requirements_by_course': {},
                'staff_comments': staff_comments,
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

        if CACHE_ENABLED:
            try:
                cache_key = f'ucas_application:{email}:{academic_year}'
                redis_client.delete(cache_key)
            except Exception as cache_error:
                app.logger.warning(f"[UCAS Application] Cache clear error (virtual tutor): {cache_error}")

        return jsonify({'success': True, 'data': {'staffComments': staff_comments}})
    except ApiError as ae:
        return jsonify({'success': False, 'error': str(ae)}), ae.status_code
    except Exception as e:
        app.logger.error(f"[UCAS Virtual Tutor] Error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# UCAS Teacher Reference (3 sections) - Supabase source of truth
# - Staff in Knack: uses existing portal auth; backend uses role hint headers.
# - External teachers: token invite links (no Knack auth).
# =============================================================================

REFERENCE_TOKEN_DEFAULT_TTL_DAYS = int(os.getenv('REFERENCE_TOKEN_TTL_DAYS') or 14)
REFERENCE_INVITE_BASE_URL = (os.getenv('REFERENCE_INVITE_BASE_URL') or '').strip()  # e.g. jsDelivr URL to Vite app
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL')

def _is_staff_request():
    # Best-effort: anything not explicitly student is treated as staff for these endpoints.
    role_hint = (request.headers.get('X-User-Role') or request.headers.get('x-user-role') or '').strip().lower()
    return role_hint not in ['student', 'pupil', 'learner']

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def _now_iso():
    return datetime.utcnow().isoformat()

def _get_establishment_id_for_student(student_email: str, academic_year: str):
    try:
        q = supabase_client.table('academic_profiles').select('establishment_id').eq('student_email', student_email)
        if academic_year:
            q = q.eq('academic_year', academic_year)
        resp = q.order('updated_at', desc=True).limit(1).execute()
        if resp and resp.data:
            return resp.data[0].get('establishment_id')
    except Exception as e:
        app.logger.warning(f"[UCAS Reference] Could not infer establishment_id: {e}")
    return None

def _get_or_create_student_reference(student_email: str, academic_year: str):
    existing = supabase_client.table('student_references')\
        .select('*')\
        .eq('student_email', student_email)\
        .eq('academic_year', academic_year)\
        .limit(1)\
        .execute()
    if existing and existing.data:
        return existing.data[0]

    est_id = _get_establishment_id_for_student(student_email, academic_year)
    ins = supabase_client.table('student_references').insert({
        'student_email': student_email,
        'academic_year': academic_year,
        'establishment_id': est_id,
        'status': 'not_started',
        'updated_at': _now_iso()
    }).execute()
    if ins and ins.data:
        return ins.data[0]
    # Fall back to refetch
    existing = supabase_client.table('student_references')\
        .select('*')\
        .eq('student_email', student_email)\
        .eq('academic_year', academic_year)\
        .limit(1)\
        .execute()
    return (existing.data[0] if existing and existing.data else None)

def _send_email_sendgrid(to_email: str, subject: str, body_text: str):
    """Best-effort SendGrid email helper (returns True/False)."""
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        app.logger.info(f"[UCAS Reference] Email not configured; would send to={to_email} subject={subject}")
        return False

    try:
        url = 'https://api.sendgrid.com/v3/mail/send'
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": SENDGRID_FROM_EMAIL},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body_text}],
        }
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        if r.status_code in (200, 202):
            return True
        app.logger.warning(f"[UCAS Reference] SendGrid failed status={r.status_code} body={r.text[:200]}")
        return False
    except Exception as e:
        app.logger.warning(f"[UCAS Reference] SendGrid error: {e}")
        return False

@app.route('/reference-contribution', methods=['GET'])
def reference_contribution_page():
    """
    Serve the external teacher contribution page with correct Content-Type.

    NOTE: JSDelivr serves .html as text/plain; serving HTML from Heroku ensures browsers execute it.
    The JS/CSS assets are still loaded from JSDelivr.
    """
    try:
        # Use @main for simplicity; JSDelivr will serve JS/CSS with correct MIME types.
        asset_base = "https://cdn.jsdelivr.net/gh/4Sighteducation/VESPA-report-v2@main/reference-contribution/dist"
        html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Reference Contribution</title>
    <link rel="stylesheet" href="{asset_base}/reference-contribution1a-index.css" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" crossorigin src="{asset_base}/reference-contribution1a.js"></script>
  </body>
</html>"""
        return Response(html, status=200, mimetype='text/html')
    except Exception as e:
        app.logger.error(f"[UCAS Reference] reference_contribution_page error: {e}")
        return Response("Error loading page", status=500, mimetype='text/plain')

@app.route('/api/academic-profile/<email>/reference/status', methods=['GET'])
def get_reference_status(email):
    """Student-safe status endpoint (no reference text)."""
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        academic_year = request.args.get('academic_year') or request.args.get('academicYear') or 'current'
        ref = _get_or_create_student_reference(email, academic_year)
        if not ref:
            return jsonify({'success': False, 'error': 'Could not create reference'}), 500

        invites = supabase_client.table('reference_invites')\
            .select('id, teacher_email, teacher_name, subject_key, allowed_sections, expires_at, used_at, revoked_at, created_at')\
            .eq('reference_id', ref['id'])\
            .order('created_at', desc=True)\
            .execute()

        invite_rows = invites.data if invites and invites.data else []
        out_invites = []
        for inv in invite_rows:
            out_invites.append({
                'id': inv.get('id'),
                'teacherEmail': inv.get('teacher_email'),
                'teacherName': inv.get('teacher_name'),
                'subjectKey': inv.get('subject_key'),
                'allowedSections': inv.get('allowed_sections') or [3],
                'expiresAt': inv.get('expires_at'),
                'usedAt': inv.get('used_at'),
                'revokedAt': inv.get('revoked_at'),
                'status': 'submitted' if inv.get('used_at') else ('revoked' if inv.get('revoked_at') else 'pending')
            })

        # Derive progress: not_started -> in_progress when any contribution exists or any invite exists
        status = ref.get('status') or 'not_started'
        if status == 'not_started' and (invite_rows or (ref.get('student_marked_complete_at') is not None)):
            status = 'in_progress'

        return jsonify({
            'success': True,
            'data': {
                'referenceId': ref.get('id'),
                'academicYear': academic_year,
                'status': status,
                'studentMarkedCompleteAt': ref.get('student_marked_complete_at'),
                'finalisedAt': ref.get('finalised_at'),
                'invites': out_invites,
                'updatedAt': ref.get('updated_at')
            }
        })
    except Exception as e:
        app.logger.error(f"[UCAS Reference] Status error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/academic-profile/<email>/reference/full', methods=['GET'])
def get_reference_full(email):
    """Staff-only: fetch full teacher reference (including section text + contributions)."""
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500
        if not _is_staff_request():
            return jsonify({'success': False, 'error': 'Only staff can view full reference'}), 403

        academic_year = request.args.get('academic_year') or request.args.get('academicYear') or 'current'
        ref = _get_or_create_student_reference(email, academic_year)
        if not ref:
            return jsonify({'success': False, 'error': 'Could not create reference'}), 500

        # Invites (same shape as status endpoint)
        invites = supabase_client.table('reference_invites')\
            .select('id, teacher_email, teacher_name, subject_key, allowed_sections, expires_at, used_at, revoked_at, created_at')\
            .eq('reference_id', ref['id'])\
            .order('created_at', desc=True)\
            .execute()
        invite_rows = invites.data if invites and invites.data else []
        out_invites = []
        for inv in invite_rows:
            out_invites.append({
                'id': inv.get('id'),
                'teacherEmail': inv.get('teacher_email'),
                'teacherName': inv.get('teacher_name'),
                'subjectKey': inv.get('subject_key'),
                'allowedSections': inv.get('allowed_sections') or [3],
                'expiresAt': inv.get('expires_at'),
                'usedAt': inv.get('used_at'),
                'revokedAt': inv.get('revoked_at'),
                'status': 'submitted' if inv.get('used_at') else ('revoked' if inv.get('revoked_at') else 'pending')
            })

        # Centre template (Section 1)
        section1_text = ''
        try:
            est_id = ref.get('establishment_id')
            if est_id:
                tmpl = supabase_client.table('reference_center_templates')\
                    .select('section1_text, updated_at')\
                    .eq('establishment_id', est_id)\
                    .eq('academic_year', academic_year)\
                    .limit(1)\
                    .execute()
                if tmpl and tmpl.data:
                    section1_text = tmpl.data[0].get('section1_text') or ''
        except Exception:
            pass

        # Contributions (Section 2/3)
        contribs = supabase_client.table('reference_contributions')\
            .select('id, section, subject_key, author_email, author_name, author_type, text, created_at, updated_at')\
            .eq('reference_id', ref['id'])\
            .order('updated_at', desc=True)\
            .execute()
        contrib_rows = contribs.data if contribs and contribs.data else []
        sec2 = []
        sec3 = []
        for c in contrib_rows:
            out = {
                'id': c.get('id'),
                'section': c.get('section'),
                'subjectKey': c.get('subject_key'),
                'authorEmail': c.get('author_email'),
                'authorName': c.get('author_name'),
                'authorType': c.get('author_type'),
                'text': c.get('text') or '',
                'createdAt': c.get('created_at'),
                'updatedAt': c.get('updated_at')
            }
            if int(c.get('section') or 0) == 2:
                sec2.append(out)
            elif int(c.get('section') or 0) == 3:
                sec3.append(out)

        status = ref.get('status') or 'not_started'
        if status == 'not_started' and (invite_rows or contrib_rows or (ref.get('student_marked_complete_at') is not None)):
            status = 'in_progress'

        return jsonify({
            'success': True,
            'data': {
                'referenceId': ref.get('id'),
                'academicYear': academic_year,
                'status': status,
                'studentMarkedCompleteAt': ref.get('student_marked_complete_at'),
                'finalisedAt': ref.get('finalised_at'),
                'section1Text': section1_text,
                'section2': sec2,
                'section3': sec3,
                'invites': out_invites,
                'updatedAt': ref.get('updated_at')
            }
        })
    except Exception as e:
        app.logger.error(f"[UCAS Reference] Full fetch error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/academic-profile/<email>/reference/contribution', methods=['POST'])
def save_reference_contribution(email):
    """Staff-only: create/update a single contribution for Section 2 or 3."""
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500
        if not _is_staff_request():
            return jsonify({'success': False, 'error': 'Only staff can add reference contributions'}), 403

        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year') or 'current'

        section = payload.get('section')
        try:
            section = int(section)
        except Exception:
            section = None
        if section not in (2, 3):
            return jsonify({'success': False, 'error': 'section must be 2 or 3'}), 400

        staff_email = (payload.get('staffEmail') or payload.get('authorEmail') or '').strip().lower()
        if not staff_email or '@' not in staff_email:
            return jsonify({'success': False, 'error': 'staffEmail required'}), 400

        author_name = (payload.get('authorName') or '').strip() or None
        subject_key = (payload.get('subjectKey') or '').strip() or None
        text = (payload.get('text') or '').strip()
        if not text:
            return jsonify({'success': False, 'error': 'text is required'}), 400
        if len(text) > 4000:
            return jsonify({'success': False, 'error': 'text is too long (max 4000 chars)'}), 400

        ref = _get_or_create_student_reference(email, academic_year)
        if not ref:
            return jsonify({'success': False, 'error': 'Could not create reference'}), 500

        # Find existing contribution by (reference_id, section, author_email, subject_key)
        try:
            q = supabase_client.table('reference_contributions')\
                .select('id, subject_key')\
                .eq('reference_id', ref['id'])\
                .eq('section', section)\
                .eq('author_email', staff_email)\
                .eq('author_type', 'staff')\
                .execute()
            existing_rows = q.data if q and q.data else []
        except Exception:
            existing_rows = []

        match_id = None
        for r in existing_rows:
            sk = (r.get('subject_key') or '') if r else ''
            if (sk or None) == (subject_key or None):
                match_id = r.get('id')
                break

        now_iso = _now_iso()
        record = {
            'reference_id': ref['id'],
            'section': section,
            'subject_key': subject_key,
            'author_email': staff_email,
            'author_name': author_name,
            'author_type': 'staff',
            'text': text,
            'updated_at': now_iso
        }

        if match_id:
            supabase_client.table('reference_contributions').update(record).eq('id', match_id).execute()
        else:
            supabase_client.table('reference_contributions').insert(record).execute()

        # Ensure reference status is at least in_progress once staff contribute
        try:
            if (ref.get('status') or 'not_started') == 'not_started':
                supabase_client.table('student_references').update({'status': 'in_progress', 'updated_at': now_iso}).eq('id', ref['id']).execute()
        except Exception:
            pass

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"[UCAS Reference] save contribution error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/academic-profile/<email>/reference/mark-complete', methods=['POST'])
def mark_reference_complete(email):
    """Staff marks teacher reference complete (admin workflow; students cannot)."""
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500
        if not _is_staff_request():
            return jsonify({'success': False, 'error': 'Only staff can mark reference complete'}), 403

        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year') or 'current'

        ref = _get_or_create_student_reference(email, academic_year)
        if not ref:
            return jsonify({'success': False, 'error': 'Could not create reference'}), 500

        supabase_client.table('student_references').update({
            'status': 'completed',
            'student_marked_complete_at': datetime.utcnow().isoformat(),
            'updated_at': _now_iso()
        }).eq('id', ref['id']).execute()

        # Optional notifications: email UCAS admins + invited teachers (best-effort)
        try:
            est_id = ref.get('establishment_id')
            admin_emails = []
            if est_id:
                s = supabase_client.table('establishment_settings').select('ucas_reference_admin_emails').eq('establishment_id', est_id).limit(1).execute()
                if s and s.data:
                    admin_emails = s.data[0].get('ucas_reference_admin_emails') or []
                    if isinstance(admin_emails, str):
                        admin_emails = []
            # notify admins
            for a in (admin_emails or []):
                _send_email_sendgrid(str(a).strip(), f"UCAS reference ready: {email}", f"The student has marked their UCAS application complete.\nStudent: {email}\nAcademic year: {academic_year}")
        except Exception as notify_err:
            app.logger.info(f"[UCAS Reference] Notify skipped: {notify_err}")

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"[UCAS Reference] mark-complete error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/academic-profile/<email>/reference/invite', methods=['POST'])
def create_reference_invite(email):
    """Student (or staff) invites a teacher by email. Returns a token URL."""
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500

        # Students can create invites; staff can too (rare case).
        payload = request.get_json() or {}
        academic_year = payload.get('academicYear') or request.args.get('academic_year') or 'current'
        teacher_email = (payload.get('teacherEmail') or '').strip().lower()
        teacher_name = (payload.get('teacherName') or '').strip() or None
        subject_key = (payload.get('subjectKey') or '').strip() or None
        allowed_sections = payload.get('allowedSections') or [3]
        if not isinstance(allowed_sections, list) or not allowed_sections:
            allowed_sections = [3]
        allowed_sections = [int(x) for x in allowed_sections if str(x).isdigit()]
        allowed_sections = [x for x in allowed_sections if x in (2, 3)]
        if not allowed_sections:
            allowed_sections = [3]

        if not teacher_email or '@' not in teacher_email:
            return jsonify({'success': False, 'error': 'Valid teacherEmail required'}), 400

        ref = _get_or_create_student_reference(email, academic_year)
        if not ref:
            return jsonify({'success': False, 'error': 'Could not create reference'}), 500

        raw_token = secrets.token_urlsafe(32)
        token_hash = _sha256_hex(raw_token)
        expires_at = (datetime.utcnow() + timedelta(days=REFERENCE_TOKEN_DEFAULT_TTL_DAYS)).isoformat()

        ins = supabase_client.table('reference_invites').insert({
            'reference_id': ref['id'],
            'teacher_email': teacher_email,
            'teacher_name': teacher_name,
            'subject_key': subject_key,
            'allowed_sections': allowed_sections,
            'token_hash': token_hash,
            'expires_at': expires_at,
            'created_by': (payload.get('createdBy') or None),
        }).execute()

        invite_id = (ins.data[0]['id'] if ins and ins.data else None)

        # Prefer a real HTML page served from Heroku (JSDelivr serves .html as text/plain).
        base = REFERENCE_INVITE_BASE_URL or (request.host_url.rstrip('/') + '/reference-contribution')
        invite_url = f"{base}?token={raw_token}"

        # Optional email send (best-effort)
        _send_email_sendgrid(
            teacher_email,
            "UCAS reference request",
            f"You have been invited to add a UCAS reference contribution.\n\nStudent: {email}\nAcademic year: {academic_year}\n\nOpen link:\n{invite_url}\n\nThis link expires in {REFERENCE_TOKEN_DEFAULT_TTL_DAYS} days."
        )

        return jsonify({'success': True, 'data': {'inviteId': invite_id, 'inviteUrl': invite_url, 'expiresAt': expires_at}})
    except Exception as e:
        app.logger.error(f"[UCAS Reference] Invite error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reference/invite/<token>', methods=['GET'])
def get_reference_invite(token):
    """External teacher validates invite token (no Knack auth)."""
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500
        if not token:
            return jsonify({'success': False, 'error': 'token required'}), 400
        token_hash = _sha256_hex(token)
        inv = supabase_client.table('reference_invites').select('*').eq('token_hash', token_hash).limit(1).execute()
        if not inv or not inv.data:
            return jsonify({'success': False, 'error': 'Invite not found'}), 404
        row = inv.data[0]
        if row.get('revoked_at'):
            return jsonify({'success': False, 'error': 'Invite revoked'}), 410
        exp = row.get('expires_at')
        if exp:
            try:
                if datetime.fromisoformat(exp.replace('Z', '+00:00')) < datetime.utcnow().replace(tzinfo=None):
                    return jsonify({'success': False, 'error': 'Invite expired'}), 410
            except Exception:
                pass

        # Pull a little student context for UX
        student_email = None
        academic_year = None
        ref = None
        try:
            ref_id = row.get('reference_id')
            ref_resp = supabase_client.table('student_references').select('*').eq('id', ref_id).limit(1).execute()
            if ref_resp and ref_resp.data:
                ref = ref_resp.data[0]
                student_email = ref.get('student_email')
                academic_year = ref.get('academic_year')
        except Exception:
            pass

        student_name = None
        try:
            if student_email:
                q = supabase_client.table('academic_profiles').select('student_name').eq('student_email', student_email)
                if academic_year:
                    q = q.eq('academic_year', academic_year)
                pr = q.order('updated_at', desc=True).limit(1).execute()
                if pr and pr.data:
                    student_name = pr.data[0].get('student_name')
        except Exception:
            pass

        return jsonify({'success': True, 'data': {
            'inviteId': row.get('id'),
            'teacherEmail': row.get('teacher_email'),
            'teacherName': row.get('teacher_name'),
            'subjectKey': row.get('subject_key'),
            'allowedSections': row.get('allowed_sections') or [3],
            'expiresAt': row.get('expires_at'),
            'usedAt': row.get('used_at'),
            'referenceId': row.get('reference_id'),
            'studentEmail': student_email,
            'studentName': student_name,
            'academicYear': academic_year
        }})
    except Exception as e:
        app.logger.error(f"[UCAS Reference] Invite GET error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reference/invite/<token>/submit', methods=['POST'])
def submit_reference_invite(token):
    """External teacher submits contribution via invite token (no Knack auth)."""
    try:
        if not SUPABASE_ENABLED:
            return jsonify({'success': False, 'error': 'Supabase is not enabled'}), 500
        if not token:
            return jsonify({'success': False, 'error': 'token required'}), 400

        token_hash = _sha256_hex(token)
        inv = supabase_client.table('reference_invites').select('*').eq('token_hash', token_hash).limit(1).execute()
        if not inv or not inv.data:
            return jsonify({'success': False, 'error': 'Invite not found'}), 404
        row = inv.data[0]
        if row.get('revoked_at'):
            return jsonify({'success': False, 'error': 'Invite revoked'}), 410

        payload = request.get_json() or {}
        section = payload.get('section')
        try:
            section = int(section)
        except Exception:
            section = None
        if section not in (2, 3):
            return jsonify({'success': False, 'error': 'section must be 2 or 3'}), 400

        allowed = row.get('allowed_sections') or [3]
        if isinstance(allowed, list) and section not in [int(x) for x in allowed if str(x).isdigit()]:
            return jsonify({'success': False, 'error': 'section not allowed for this invite'}), 403

        text = (payload.get('text') or payload.get('comment') or '').strip()
        if not text:
            return jsonify({'success': False, 'error': 'text is required'}), 400
        if len(text) > 4000:
            return jsonify({'success': False, 'error': 'text is too long (max 4000 chars)'}), 400

        teacher_email = (row.get('teacher_email') or '').strip().lower()
        teacher_name = (payload.get('authorName') or payload.get('teacherName') or row.get('teacher_name') or '').strip() or None
        subject_key = row.get('subject_key')
        ref_id = row.get('reference_id')

        # Upsert by (reference_id, section, subject_key, author_email, author_type)
        q = supabase_client.table('reference_contributions')\
            .select('id')\
            .eq('reference_id', ref_id)\
            .eq('section', section)\
            .eq('author_email', teacher_email)\
            .eq('author_type', 'invited_teacher')
        # If the invite is tied to a subject, avoid overwriting other-subject contributions by same teacher.
        if subject_key:
            q = q.eq('subject_key', subject_key)
        existing = q.execute()
        if existing and existing.data:
            cid = existing.data[0]['id']
            supabase_client.table('reference_contributions').update({
                'text': text,
                'author_name': teacher_name,
                'subject_key': subject_key,
                'updated_at': _now_iso()
            }).eq('id', cid).execute()
        else:
            supabase_client.table('reference_contributions').insert({
                'reference_id': ref_id,
                'section': section,
                'subject_key': subject_key,
                'author_email': teacher_email,
                'author_name': teacher_name,
                'author_type': 'invited_teacher',
                'text': text,
                'updated_at': _now_iso()
            }).execute()

        # Mark invite used and bump reference status
        supabase_client.table('reference_invites').update({'used_at': _now_iso()}).eq('id', row.get('id')).execute()
        try:
            supabase_client.table('student_references').update({'status': 'in_progress', 'updated_at': _now_iso()}).eq('id', ref_id).execute()
        except Exception:
            pass

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"[UCAS Reference] Invite submit error: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/academic-profile/sync', methods=['POST'])
def sync_academic_profile():
    """Sync academic profile to both Supabase and Knack (dual-write)"""
    try:
        data = request.get_json()
        
        student_email = data.get('studentEmail')
        student_name = data.get('studentName')
        profile_data = data.get('profile', {})
        subjects_data = data.get('subjects', [])
        academic_year = data.get('academicYear')
        knack_record_id = data.get('knackRecordId')
        
        app.logger.info(f"[Academic Profile] Syncing profile for {student_email}, {len(subjects_data)} subjects")
        
        if not student_email:
            return jsonify({'success': False, 'error': 'studentEmail required'}), 400
        
        supabase_written = False
        knack_written = False
        profile_id = None
        
        if SUPABASE_ENABLED:
            try:
                existing = supabase_client.table('academic_profiles')\
                    .select('id')\
                    .eq('student_email', student_email)\
                    .eq('academic_year', academic_year)\
                    .execute()
                
                profile_record = {
                    'student_email': student_email,
                    'student_name': student_name,
                    'year_group': profile_data.get('yearGroup'),
                    'tutor_group': profile_data.get('tutorGroup'),
                    'attendance': profile_data.get('attendance'),
                    'prior_attainment': profile_data.get('priorAttainment'),
                    'upn': profile_data.get('upn'),
                    'uci': profile_data.get('uci'),
                    'centre_number': profile_data.get('centreNumber'),
                    'establishment_name': profile_data.get('school'),
                    'establishment_id': profile_data.get('establishmentId'),
                    'academic_year': academic_year,
                    'knack_record_id': knack_record_id,
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                if existing.data:
                    profile_id = existing.data[0]['id']
                    app.logger.info(f"[Academic Profile] Updating existing Supabase profile: {profile_id}")
                    
                    supabase_client.table('academic_profiles')\
                        .update(profile_record)\
                        .eq('id', profile_id)\
                        .execute()
                else:
                    app.logger.info(f"[Academic Profile] Creating new Supabase profile for {student_email}")
                    
                    result = supabase_client.table('academic_profiles')\
                        .insert(profile_record)\
                        .execute()
                    
                    profile_id = result.data[0]['id']
                
                supabase_client.table('student_subjects')\
                    .delete()\
                    .eq('profile_id', profile_id)\
                    .execute()
                
                if subjects_data:
                    subjects_to_insert = [
                        {
                            'profile_id': profile_id,
                            'student_email': student_email,
                            'subject_name': subj.get('subjectName'),
                            'exam_type': subj.get('examType'),
                            'exam_board': subj.get('examBoard'),
                            'current_grade': subj.get('currentGrade'),
                            'target_grade': subj.get('targetGrade'),
                            'minimum_expected_grade': subj.get('minimumExpectedGrade'),
                            'subject_target_grade': subj.get('subjectTargetGrade'),
                            'effort_grade': subj.get('effortGrade'),
                            'behaviour_grade': subj.get('behaviourGrade'),
                            'subject_attendance': subj.get('subjectAttendance'),
                            'original_record_id': subj.get('originalRecordId'),
                            'subject_position': subj.get('position', idx + 1)
                        }
                        for idx, subj in enumerate(subjects_data)
                    ]
                    
                    supabase_client.table('student_subjects')\
                        .insert(subjects_to_insert)\
                        .execute()
                    
                    app.logger.info(f"[Academic Profile] Inserted {len(subjects_to_insert)} subjects to Supabase")
                
                supabase_written = True
                
            except Exception as sb_error:
                app.logger.error(f"[Academic Profile] Supabase write failed: {sb_error}")
                app.logger.error(traceback.format_exc())
                supabase_written = False
        
        if knack_record_id:
            try:
                for idx, subject in enumerate(subjects_data):
                    position = subject.get('position', idx + 1)
                    sync_subject_to_knack(subject, knack_record_id, position)
                
                profile_update = {
                    'field_3066': student_name,
                    'field_3078': profile_data.get('yearGroup'),
                    'field_3077': profile_data.get('tutorGroup'),
                    'field_3076': profile_data.get('attendance'),
                    'field_3272': profile_data.get('priorAttainment'),
                    'field_3137': profile_data.get('upn'),
                    'field_3136': profile_data.get('uci'),
                    'field_3138': profile_data.get('centreNumber')
                }
                
                profile_update = {k: v for k, v in profile_update.items() if v is not None}
                
                if profile_update:
                    response = requests.put(
                        f'{KNACK_API_URL}/objects/object_112/records/{knack_record_id}',
                        headers={
                            'X-Knack-Application-Id': KNACK_APP_ID,
                            'X-Knack-REST-API-Key': KNACK_API_KEY,
                            'Content-Type': 'application/json'
                        },
                        json=profile_update
                    )
                    
                    knack_written = response.status_code in [200, 201]
                    
                    if not knack_written:
                        app.logger.warning(f"[Academic Profile] Knack profile update failed: {response.status_code}")
                else:
                    knack_written = True
                
            except Exception as knack_error:
                app.logger.error(f"[Academic Profile] Knack write failed: {knack_error}")
                knack_written = False
        else:
            app.logger.warning(f"[Academic Profile] No Knack record ID provided, skipping Knack sync")
            knack_written = False
        
        if CACHE_ENABLED:
            try:
                cache_key = f'academic_profile:{student_email}:*'
                for key in redis_client.scan_iter(match=cache_key):
                    redis_client.delete(key)
            except Exception as cache_error:
                app.logger.warning(f"[Academic Profile] Cache clear error: {cache_error}")
        
        return jsonify({
            'success': True,
            'supabaseWritten': supabase_written,
            'knackWritten': knack_written,
            'profileId': str(profile_id) if profile_id else None,
            'message': 'Profile synced successfully'
        })
        
    except Exception as e:
        app.logger.error(f"[Academic Profile] Error in sync_academic_profile: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/academic-profile/subject/<subject_id>', methods=['PUT'])
def update_subject_grade(subject_id):
    """Update individual subject grades (staff editing)"""
    try:
        updates = request.get_json()
        
        app.logger.info(f"[Academic Profile] Updating subject {subject_id}")

        # Role hint from frontend (best-effort). If Student, only allow target_grade updates.
        role_hint = (request.headers.get('X-User-Role') or request.headers.get('x-user-role') or '').strip().lower()
        is_student_hint = role_hint in ['student', 'pupil', 'learner']
        
        supabase_updated = False
        knack_updated = False
        
        if SUPABASE_ENABLED:
            try:
                subject_response = supabase_client.table('student_subjects')\
                    .select('*, academic_profiles!inner(student_email, knack_record_id)')\
                    .eq('id', subject_id)\
                    .execute()
                
                if not subject_response.data:
                    return jsonify({'success': False, 'error': 'Subject not found'}), 404
                
                subject = subject_response.data[0]
                student_email = subject['academic_profiles']['student_email']
                knack_record_id = subject['academic_profiles']['knack_record_id']
                original_record_id = subject.get('original_record_id')
                subject_position = subject.get('subject_position')
                
                update_data = {
                    'updated_at': datetime.utcnow().isoformat()
                }

                # If the caller is a Student, only allow Target updates.
                if is_student_hint:
                    allowed_keys = set(['targetGrade', 'target_grade'])
                    incoming_keys = set([k for k in (updates or {}).keys() if k is not None])
                    forbidden = [k for k in incoming_keys if k not in allowed_keys]
                    if forbidden:
                        return jsonify({'success': False, 'error': 'Students can only update Target grade.'}), 403
                    if not (('targetGrade' in updates) or ('target_grade' in updates)):
                        return jsonify({'success': False, 'error': 'Missing targetGrade'}), 400
                    update_data['target_grade'] = updates.get('targetGrade', updates.get('target_grade'))
                else:
                
                    # Accept both camelCase (frontend) and snake_case (direct API calls)
                    if 'currentGrade' in updates or 'current_grade' in updates:
                        update_data['current_grade'] = updates.get('currentGrade', updates.get('current_grade'))
                    if 'targetGrade' in updates or 'target_grade' in updates:
                        update_data['target_grade'] = updates.get('targetGrade', updates.get('target_grade'))
                    if 'effortGrade' in updates or 'effort_grade' in updates:
                        update_data['effort_grade'] = updates.get('effortGrade', updates.get('effort_grade'))
                    if 'behaviourGrade' in updates or 'behaviour_grade' in updates:
                        update_data['behaviour_grade'] = updates.get('behaviourGrade', updates.get('behaviour_grade'))
                    if 'subjectAttendance' in updates or 'subject_attendance' in updates:
                        update_data['subject_attendance'] = updates.get('subjectAttendance', updates.get('subject_attendance'))
                    if 'minimumExpectedGrade' in updates or 'minimum_expected_grade' in updates:
                        update_data['minimum_expected_grade'] = updates.get('minimumExpectedGrade', updates.get('minimum_expected_grade'))
                    if 'subjectTargetGrade' in updates or 'subject_target_grade' in updates:
                        update_data['subject_target_grade'] = updates.get('subjectTargetGrade', updates.get('subject_target_grade'))
                    if 'subjectName' in updates or 'subject_name' in updates:
                        update_data['subject_name'] = updates.get('subjectName', updates.get('subject_name'))
                    if 'examType' in updates or 'exam_type' in updates:
                        update_data['exam_type'] = updates.get('examType', updates.get('exam_type'))
                    if 'examBoard' in updates or 'exam_board' in updates:
                        update_data['exam_board'] = updates.get('examBoard', updates.get('exam_board'))
                
                # Perform update and VERIFY it persisted by reading back the row.
                update_resp = supabase_client.table('student_subjects')\
                    .update(update_data)\
                    .eq('id', subject_id)\
                    .execute()

                # Some PostgREST configurations may return minimal; verify via a follow-up select
                verify_resp = supabase_client.table('student_subjects')\
                    .select('*')\
                    .eq('id', subject_id)\
                    .limit(1)\
                    .execute()

                if not verify_resp.data:
                    raise Exception("Supabase update verification failed: subject row not returned")

                verified = verify_resp.data[0]
                # Determine whether requested fields now match
                def matches(field_key, incoming):
                    if incoming is None:
                        return True
                    return str(verified.get(field_key) or '') == str(incoming or '')

                ok = True
                if 'current_grade' in update_data:
                    ok = ok and matches('current_grade', update_data.get('current_grade'))
                if 'target_grade' in update_data:
                    ok = ok and matches('target_grade', update_data.get('target_grade'))
                if 'effort_grade' in update_data:
                    ok = ok and matches('effort_grade', update_data.get('effort_grade'))
                if 'behaviour_grade' in update_data:
                    ok = ok and matches('behaviour_grade', update_data.get('behaviour_grade'))
                if 'subject_attendance' in update_data:
                    ok = ok and matches('subject_attendance', update_data.get('subject_attendance'))
                if 'minimum_expected_grade' in update_data:
                    ok = ok and matches('minimum_expected_grade', update_data.get('minimum_expected_grade'))
                if 'subject_target_grade' in update_data:
                    ok = ok and matches('subject_target_grade', update_data.get('subject_target_grade'))
                if 'subject_name' in update_data:
                    ok = ok and matches('subject_name', update_data.get('subject_name'))
                if 'exam_type' in update_data:
                    ok = ok and matches('exam_type', update_data.get('exam_type'))
                if 'exam_board' in update_data:
                    ok = ok and matches('exam_board', update_data.get('exam_board'))

                if not ok:
                    # Most commonly caused by RLS / using anon key
                    raise Exception("Supabase update did not persist (possible RLS/permissions issue)")

                app.logger.info(f"[Academic Profile] Supabase update persisted")
                supabase_updated = True
                
                # Best-effort Knack sync: NEVER fail the request if Supabase updated.
                try:
                    if original_record_id and KNACK_APP_ID and KNACK_API_KEY:
                        knack_subject_update = {}
                        
                        if 'currentGrade' in updates or 'current_grade' in updates:
                            knack_subject_update['field_3132'] = updates.get('currentGrade', updates.get('current_grade'))
                        if 'targetGrade' in updates or 'target_grade' in updates:
                            knack_subject_update['field_3135'] = updates.get('targetGrade', updates.get('target_grade'))
                        if 'effortGrade' in updates or 'effort_grade' in updates:
                            knack_subject_update['field_3133'] = updates.get('effortGrade', updates.get('effort_grade'))
                        if 'behaviourGrade' in updates or 'behaviour_grade' in updates:
                            knack_subject_update['field_3134'] = updates.get('behaviourGrade', updates.get('behaviour_grade'))
                        if 'subjectAttendance' in updates or 'subject_attendance' in updates:
                            knack_subject_update['field_3186'] = updates.get('subjectAttendance', updates.get('subject_attendance'))
                        
                        if knack_subject_update:
                            obj_113_response = requests.put(
                                f'{KNACK_API_URL}/objects/object_113/records/{original_record_id}',
                                headers={
                                    'X-Knack-Application-Id': KNACK_APP_ID,
                                    'X-Knack-REST-API-Key': KNACK_API_KEY,
                                    'Content-Type': 'application/json'
                                },
                                json=knack_subject_update,
                                timeout=15
                            )
                            
                            knack_updated = obj_113_response.status_code in [200, 201]
                    
                    if knack_record_id and subject_position:
                        full_subject = supabase_client.table('student_subjects')\
                            .select('*')\
                            .eq('id', subject_id)\
                            .execute()
                        
                        if full_subject.data:
                            subj = full_subject.data[0]
                            updated_subject_data = {
                                'subjectName': subj.get('subject_name'),
                                'examType': subj.get('exam_type'),
                                'examBoard': subj.get('exam_board'),
                                'currentGrade': subj.get('current_grade'),
                                'targetGrade': subj.get('target_grade'),
                                'minimumExpectedGrade': subj.get('minimum_expected_grade'),
                                'subjectTargetGrade': subj.get('subject_target_grade'),
                                'effortGrade': subj.get('effort_grade'),
                                'behaviourGrade': subj.get('behaviour_grade'),
                                'subjectAttendance': subj.get('subject_attendance'),
                                'originalRecordId': subj.get('original_record_id')
                            }
                            
                            sync_subject_to_knack(updated_subject_data, knack_record_id, subject_position)
                except Exception as knack_err:
                    app.logger.warning(f"[Academic Profile] Knack sync failed (non-fatal): {knack_err}")
                    app.logger.warning(traceback.format_exc())
                
                if CACHE_ENABLED:
                    cache_pattern = f'academic_profile:{student_email}:*'
                    for key in redis_client.scan_iter(match=cache_pattern):
                        redis_client.delete(key)
                
            except Exception as sb_error:
                app.logger.error(f"[Academic Profile] Supabase update failed: {sb_error}")
                app.logger.error(traceback.format_exc())
                supabase_updated = False
        
        if not supabase_updated:
            return jsonify({
                'success': False,
                'error': 'Supabase update failed (not persisted)',
                'updated': { 'supabase': False, 'knack': knack_updated }
            }), 500

        # Return the updated subject row so the UI can reflect the persisted values immediately
        try:
            updated_row = supabase_client.table('student_subjects').select('*').eq('id', subject_id).limit(1).execute()
            subject_data = updated_row.data[0] if updated_row and updated_row.data else None
        except Exception:
            subject_data = None

        return jsonify({
            'success': True,
            'updated': { 'supabase': True, 'knack': knack_updated },
            'subject': subject_data
        })
        
    except Exception as e:
        app.logger.error(f"[Academic Profile] Error in update_subject_grade: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/academic-profile/health', methods=['GET'])
def academic_profile_health():
    """Health check for academic profile system"""
    try:
        health = {
            'supabaseConnected': SUPABASE_ENABLED,
            'tablesExist': False,
            'sampleData': None
        }
        
        if SUPABASE_ENABLED:
            test_query = supabase_client.table('academic_profiles')\
                .select('id', count='exact')\
                .limit(1)\
                .execute()
            
            health['tablesExist'] = True
            health['sampleData'] = {
                'profileCount': test_query.count if hasattr(test_query, 'count') else 0
            }
        
        return jsonify({
            'success': True,
            'health': health
        })
        
    except Exception as e:
        app.logger.error(f"[Academic Profile] Health check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {
                'supabaseConnected': False,
                'tablesExist': False
            }
        }), 500

# ===== END ACADEMIC PROFILE ENDPOINTS =====

# ===== VESPA ACTIVITIES V3 API ENDPOINTS =====
# Import and register activities API routes
try:
    app.logger.info(f"[Activities API] Attempting to import activities_api module...")
    app.logger.info(f"[Activities API] SUPABASE_ENABLED = {SUPABASE_ENABLED}")
    app.logger.info(f"[Activities API] supabase_client exists = {supabase_client is not None}")
    
    from activities_api import register_activities_routes
    app.logger.info("[Activities API] Successfully imported register_activities_routes")
    
    if SUPABASE_ENABLED and supabase_client:
        app.logger.info("[Activities API] Registering routes...")
        register_activities_routes(app, supabase_client)
        app.logger.info("✅ VESPA Activities V3 API routes registered successfully")
    else:
        app.logger.warning(f"⚠️ VESPA Activities V3 API routes not registered - SUPABASE_ENABLED={SUPABASE_ENABLED}, supabase_client={supabase_client is not None}")
except ImportError as e:
    app.logger.error(f"❌ Could not import activities_api: {e}")
    import traceback
    app.logger.error(traceback.format_exc())
except Exception as e:
    app.logger.error(f"❌ Error registering activities API routes: {e}")
    import traceback
    app.logger.error(traceback.format_exc())
# ===== END VESPA ACTIVITIES V3 API ENDPOINTS =====


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv('PORT', 5001)) # Use port 5001 for local dev if 5000 is common 