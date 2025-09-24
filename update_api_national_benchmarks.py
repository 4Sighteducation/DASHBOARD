#!/usr/bin/env python3
"""
Update API endpoints to use academic-year-specific national benchmarks
This fixes the issue where national comparison data doesn't show for historical years
"""

# =============================================================================
# ADD THIS TO app.py
# =============================================================================

def get_national_benchmarks_for_year(academic_year, cycle=1):
    """
    Get national benchmark data for a specific academic year and cycle.
    Returns None if no data exists for that year.
    """
    try:
        # Query the national_benchmarks table
        result = supabase_client.rpc('get_national_benchmarks_for_year', {
            'p_academic_year': academic_year,
            'p_cycle': cycle
        }).execute()
        
        if result.data:
            # Transform to the format expected by frontend
            benchmarks = {}
            for row in result.data:
                component = row['vespa_component']
                benchmarks[component] = {
                    'mean': float(row['mean_score']) if row['mean_score'] else None,
                    'median': float(row['median_score']) if row['median_score'] else None,
                    'std_dev': float(row['std_dev']) if row['std_dev'] else None,
                    'sample_size': row['sample_size'] or 0,
                    'schools_count': row['schools_count'] or 0
                }
            return benchmarks
        return None
    except Exception as e:
        app.logger.error(f"Error fetching national benchmarks: {str(e)}")
        return None


# =============================================================================
# UPDATE EXISTING ENDPOINT: /api/statistics
# =============================================================================

# In the get_school_statistics_query function, add national benchmark fetching:

@app.route('/api/statistics', methods=['GET'])
def get_school_statistics_query():
    """Get statistics for a specific school with year-specific national benchmarks"""
    try:
        establishment_id = request.args.get('establishment_id')
        cycle = request.args.get('cycle', type=int, default=1)
        academic_year = request.args.get('academic_year')
        
        # ... existing code for fetching school statistics ...
        
        # ADD THIS: Fetch national benchmarks for the selected year
        national_benchmarks = None
        if academic_year:
            # Convert format if needed (2025-26 to 2025/2026)
            academic_year_db = convert_academic_year_format(academic_year, to_database=True)
            national_benchmarks = get_national_benchmarks_for_year(academic_year_db, cycle)
        
        # If no benchmarks for that year, you could fall back to current year
        if not national_benchmarks:
            current_year = get_current_academic_year()
            national_benchmarks = get_national_benchmarks_for_year(current_year, cycle)
        
        # ... existing code ...
        
        # Include national benchmarks in response
        response_data = {
            'statistics': statistics,
            'student_count': len(student_ids),
            'national_benchmarks': national_benchmarks,  # ADD THIS
            'academic_year': academic_year
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        # ... error handling ...


# =============================================================================
# NEW ENDPOINT: /api/national-benchmarks
# =============================================================================

@app.route('/api/national-benchmarks', methods=['GET'])
def get_national_benchmarks_endpoint():
    """
    Get national benchmark data for a specific academic year and cycle.
    
    Query params:
    - academic_year: e.g., '2024/2025' or '2024-25'
    - cycle: 1, 2, or 3 (default: 1)
    """
    try:
        # Get parameters
        academic_year = request.args.get('academic_year')
        cycle = request.args.get('cycle', type=int, default=1)
        
        if not academic_year:
            # Default to current academic year
            academic_year = get_current_academic_year()
        else:
            # Convert format if needed (2024-25 to 2024/2025)
            academic_year = convert_academic_year_format(academic_year, to_database=True)
        
        # Fetch benchmarks
        benchmarks = get_national_benchmarks_for_year(academic_year, cycle)
        
        if not benchmarks:
            # Try to calculate from actual data if not pre-computed
            app.logger.info(f"No pre-computed benchmarks for {academic_year}, calculating...")
            calculate_benchmarks_result = supabase_client.rpc('calculate_national_benchmarks', {
                'p_academic_year': academic_year,
                'p_cycle': cycle
            }).execute()
            
            # Try fetching again
            benchmarks = get_national_benchmarks_for_year(academic_year, cycle)
        
        if benchmarks:
            return jsonify({
                'success': True,
                'academic_year': academic_year,
                'cycle': cycle,
                'benchmarks': benchmarks
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No national benchmark data available for {academic_year} Cycle {cycle}',
                'academic_year': academic_year,
                'cycle': cycle
            }), 404
            
    except Exception as e:
        app.logger.error(f"Error in national benchmarks endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# UPDATE DASHBOARD DATA ENDPOINTS
# =============================================================================

# In get_dashboard_initial_data and similar endpoints, ensure national data is included:

@app.route('/api/dashboard-initial-data', methods=['POST'])
def get_dashboard_initial_data():
    """Get initial dashboard data with year-specific national benchmarks"""
    data = request.get_json()
    establishment_id = data.get('establishmentId')
    cycle = data.get('cycle', 1)
    
    # Get academic year from request or use current
    academic_year = data.get('academicYear')
    if not academic_year:
        academic_year = get_current_academic_year()
    else:
        academic_year = convert_academic_year_format(academic_year, to_database=True)
    
    # ... existing code to fetch school data ...
    
    # ADD: Fetch national benchmarks
    national_benchmarks = get_national_benchmarks_for_year(academic_year, cycle)
    
    # Build response with national data
    response_data = {
        'students': students_data,
        'statistics': statistics,
        'national_benchmarks': national_benchmarks,  # ADD THIS
        'academic_year': academic_year
    }
    
    return jsonify(response_data)


# =============================================================================
# HELPER FUNCTION: Calculate benchmarks from actual data
# =============================================================================

def calculate_and_store_national_benchmarks(academic_year=None, cycle=1):
    """
    Calculate national benchmarks from actual VESPA data and store in database.
    Run this periodically or on-demand.
    """
    if not academic_year:
        academic_year = get_current_academic_year()
    
    try:
        # Get all VESPA scores for the academic year
        vespa_query = supabase_client.table('vespa_scores')\
            .select('v1, v2, v3, e1, e2, e3, s1, s2, s3, p1, p2, p3, a1, a2, a3, r1, r2, r3, student_id')\
            .eq('academic_year', academic_year)\
            .eq('cycle', cycle)\
            .execute()
        
        if not vespa_query.data:
            return None
        
        import numpy as np
        
        # Calculate statistics for each component
        components = {
            'vision': ['v1', 'v2', 'v3'],
            'effort': ['e1', 'e2', 'e3'],
            'systems': ['s1', 's2', 's3'],
            'practice': ['p1', 'p2', 'p3'],
            'attitude': ['a1', 'a2', 'a3'],
            'resilience': ['r1', 'r2', 'r3']
        }
        
        benchmarks = []
        
        for component_name, fields in components.items():
            # Get average score for this component
            scores = []
            for record in vespa_query.data:
                component_scores = [record.get(f) for f in fields if record.get(f) is not None]
                if component_scores:
                    scores.append(np.mean(component_scores))
            
            if scores:
                scores_array = np.array(scores)
                benchmark = {
                    'academic_year': academic_year,
                    'cycle': cycle,
                    'vespa_component': component_name,
                    'mean_score': float(np.mean(scores_array)),
                    'median_score': float(np.median(scores_array)),
                    'std_dev': float(np.std(scores_array)),
                    'percentile_25': float(np.percentile(scores_array, 25)),
                    'percentile_75': float(np.percentile(scores_array, 75)),
                    'sample_size': len(scores),
                    'schools_count': len(set(r['student_id'] for r in vespa_query.data))
                }
                benchmarks.append(benchmark)
        
        # Store in database
        if benchmarks:
            result = supabase_client.table('national_benchmarks').upsert(
                benchmarks,
                on_conflict='academic_year,cycle,vespa_component'
            ).execute()
            
            app.logger.info(f"Calculated and stored {len(benchmarks)} benchmarks for {academic_year} Cycle {cycle}")
            return benchmarks
            
    except Exception as e:
        app.logger.error(f"Error calculating benchmarks: {str(e)}")
        return None


# =============================================================================
# MIGRATION FUNCTION: Calculate historical benchmarks
# =============================================================================

def migrate_historical_benchmarks():
    """
    One-time function to calculate benchmarks for all historical data.
    Run this after implementing the new system.
    """
    academic_years = ['2023/2024', '2024/2025', '2025/2026']
    cycles = [1, 2, 3]
    
    for year in academic_years:
        for cycle in cycles:
            print(f"Calculating benchmarks for {year} Cycle {cycle}...")
            result = calculate_and_store_national_benchmarks(year, cycle)
            if result:
                print(f"  Stored {len(result)} components")
            else:
                print(f"  No data available")


# =============================================================================
# EXAMPLE USAGE IN FRONTEND
# =============================================================================

"""
// In your React/JavaScript frontend:

const fetchNationalBenchmarks = async (academicYear, cycle) => {
    try {
        const response = await fetch(
            `/api/national-benchmarks?academic_year=${academicYear}&cycle=${cycle}`
        );
        const data = await response.json();
        
        if (data.success) {
            return data.benchmarks;
        } else {
            console.warn('No national benchmarks available for', academicYear);
            return null;
        }
    } catch (error) {
        console.error('Error fetching national benchmarks:', error);
        return null;
    }
};

// When user changes academic year dropdown:
const handleAcademicYearChange = async (newYear) => {
    setAcademicYear(newYear);
    
    // Fetch both school data and national benchmarks for the selected year
    const [schoolData, nationalData] = await Promise.all([
        fetchSchoolData(establishmentId, newYear),
        fetchNationalBenchmarks(newYear, selectedCycle)
    ]);
    
    setSchoolStatistics(schoolData);
    setNationalBenchmarks(nationalData);
};
"""
