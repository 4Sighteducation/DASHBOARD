"""
Knack Configuration Example File
Copy this to knack_config.py and fill in your credentials
NEVER commit the actual knack_config.py file!
"""

# Knack API Credentials - Get these from Knack settings
KNACK_APP_ID = "your-app-id-here"
KNACK_API_KEY = "your-api-key-here"  # NEVER commit this!

# Object_10 Field Mappings - Update these with your actual field IDs
OBJECT_10_FIELDS = {
    'email': 'field_197', 
    
    # Cycle 1 VESPA scores (V1-O1)
    'cycle_1': {
        'VISION': 'field_155',    
        'EFFORT': 'field_156',    
        'SYSTEMS': 'field_157',   
        'PRACTICE': 'field_158',  
        'ATTITUDE': 'field_159',  
        'OVERALL': 'field_160'    
    },
    
    # Cycle 2 VESPA scores (V2-O2)
    'cycle_2': {
        'VISION': 'field_161',    
        'EFFORT': 'field_162',    
        'SYSTEMS': 'field_163',  
        'PRACTICE': 'field_164', 
        'ATTITUDE': 'field_165',  
        'OVERALL': 'field_166'  
    },
    
    # Cycle 3 VESPA scores (V3-O3)
    'cycle_3': {
        'VISION': 'field_167',   
        'EFFORT': 'field_168',    
        'SYSTEMS': 'field_169',   
        'PRACTICE': 'field_170',  
        'ATTITUDE': 'field_171', 
        'OVERALL': 'field_172' 
    }
}

# Connected fields mapping
CONNECTED_FIELDS = {
    'field_133': 'field_1821',  # VESPA Customer
    'field_439': 'field_2069',  # Staff Admin
    'field_145': 'field_2070'   # Tutors
}

# Rate limiting settings
API_RATE_LIMIT = 0.5