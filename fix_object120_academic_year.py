"""
Fix for Object_120 fetching in app.py

The problem: When fetching national benchmarks from Object_120, the API doesn't filter by academic year.
It just gets the latest record, which means everyone sees 2025-2026 data regardless of selected year.

The fix: Add academic year filter when fetching Object_120.

Key changes needed in app.py:

1. In dashboard-initial-data endpoint (around line 958 and 988):
   - Add academic year filter to Object_120 request
   
2. In get_national_eri endpoint (around line 3447):
   - Add academic year filter
   
3. In any other Object_120 fetch (around line 3869):
   - Add academic year filter

"""

# Example of the fix needed:

def get_object120_for_academic_year(academic_year=None):
    """
    Fetch Object_120 record for specific academic year.
    
    Args:
        academic_year: Academic year in format "2024/2025" or None for current
    
    Returns:
        Object_120 record for the specified academic year
    """
    
    # If no academic year specified, use current
    if not academic_year:
        academic_year = get_current_academic_year()
    
    # Convert format from 2024/2025 to 2024-2025 (Object_120 format)
    object120_year = academic_year.replace('/', '-')
    
    # Create filter for academic year (field_3308)
    filters = [{
        'field': 'field_3308',  # Academic Year field in Object_120
        'operator': 'is',
        'value': object120_year
    }]
    
    # Fetch with academic year filter
    data = make_knack_request(
        'object_120',
        filters=filters,  # Now filtering by academic year!
        rows_per_page=1,
        sort_field='field_3307',  # Still sort by date
        sort_order='desc'  # Get most recent for that year
    )
    
    records = data.get('records', [])
    if records:
        return records[0]
    return {}


# Changes needed in app.py:

# REPLACE THIS (around line 958-965):
"""
national_future = executor.submit(
    make_knack_request,
    'object_120',
    filters=[],
    rows_per_page=1,
    sort_field='field_3307',
    sort_order='desc'
)
"""

# WITH THIS:
"""
# Determine academic year from the filters
current_academic_year = get_current_academic_year()
# Convert to Object_120 format (2024-2025)
object120_year = current_academic_year.replace('/', '-')

national_future = executor.submit(
    make_knack_request,
    'object_120',
    filters=[{
        'field': 'field_3308',  # Academic Year field
        'operator': 'is',
        'value': object120_year
    }],
    rows_per_page=1,
    sort_field='field_3307',
    sort_order='desc'
)
"""
