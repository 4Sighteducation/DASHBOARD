"""
Knack Configuration File Example
Copy this to knack_config.py and fill in your actual values
"""

# Knack API Credentials
KNACK_APP_ID = "your-app-id-here"
KNACK_API_KEY = "your-api-key-here"

# Object_10 Field Mappings - Update these with your actual field IDs
OBJECT_10_FIELDS = {
    'email': 'field_email',  # Email field in Object_10
    
    # Cycle 1 VESPA scores (V1-O1)
    'cycle_1': {
        'VISION': 'field_V1',
        'EFFORT': 'field_E1', 
        'SYSTEMS': 'field_S1',
        'PRACTICE': 'field_P1',
        'ATTITUDE': 'field_A1',
        'OVERALL': 'field_O1'
    },
    
    # Cycle 2 VESPA scores (V2-O2)
    'cycle_2': {
        'VISION': 'field_V2',
        'EFFORT': 'field_E2',
        'SYSTEMS': 'field_S2', 
        'PRACTICE': 'field_P2',
        'ATTITUDE': 'field_A2',
        'OVERALL': 'field_O2'
    },
    
    # Cycle 3 VESPA scores (V3-O3)
    'cycle_3': {
        'VISION': 'field_V3',
        'EFFORT': 'field_E3',
        'SYSTEMS': 'field_S3',
        'PRACTICE': 'field_P3',
        'ATTITUDE': 'field_A3',
        'OVERALL': 'field_O3'
    }
}

# Connected fields mapping from Object_10 to Object_29
# These are many-to-many connections, so they contain arrays of IDs
CONNECTED_FIELDS = {
    # Object_10 field -> Object_29 field
    'field_133': 'field_1821',  # VESPA Customer
    'field_439': 'field_2069',  # Staff Admin
    'field_145': 'field_2070'   # Tutors
}

# Rate limiting settings (in seconds between API calls)
API_RATE_LIMIT = 0.5  # Adjust based on your Knack plan 