#!/usr/bin/env python3
"""
Updates needed in app.py to use academic_year from students table

These changes ensure the dashboard counts students based on their 
academic_year field, not just whether they have VESPA data
"""

# KEY CHANGES NEEDED:

# 1. Update student counting logic (around line 5615-5700)
"""
# OLD CODE - counts students who have VESPA data:
query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)

# NEW CODE - filter by academic_year field:
query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)

# Add academic year filter if provided
if academic_year:
    query = query.eq('academic_year', academic_year)

# This now counts ALL students in that academic year, 
# not just those with VESPA data
"""

# 2. Update the get_qla_data_query function (around line 6365)
"""
# Add this after getting parameters (around line 6383):
academic_year = request.args.get('academic_year')

# When getting students (around line 6500):
students_query = supabase_client.table('students').select('id').eq('establishment_id', establishment_uuid)

# Add academic year filter
if academic_year:
    students_query = students_query.eq('academic_year', academic_year)

# Rest of filters remain the same
if year_group:
    students_query = students_query.eq('year_group', year_group)
# etc...
"""

# 3. Update total student counting (around line 5694)
"""
# OLD CODE:
total_query = supabase_client.table('students').select('id', count='exact').eq('establishment_id', establishment_uuid)

# NEW CODE - include academic year:
total_query = supabase_client.table('students').select('id', count='exact').eq('establishment_id', establishment_uuid)
if academic_year:
    total_query = total_query.eq('academic_year', academic_year)

total_result = total_query.execute()
total_students = total_result.count if hasattr(total_result, 'count') else 0

# This gives you the EXACT count of students for that academic year
"""

# 4. Example of a new endpoint to get student counts by academic year
"""
@app.route('/api/student-counts-by-year/<establishment_id>', methods=['GET'])
def get_student_counts_by_year(establishment_id):
    '''Get student counts grouped by academic year'''
    try:
        # Convert establishment ID if needed
        establishment_uuid = convert_knack_id_to_uuid(establishment_id)
        
        # Get all academic years for this establishment
        years_result = supabase_client.table('students')\
            .select('academic_year')\
            .eq('establishment_id', establishment_uuid)\
            .execute()
        
        # Get unique years
        years = list(set([s['academic_year'] for s in years_result.data if s.get('academic_year')]))
        years.sort(reverse=True)  # Most recent first
        
        # Count students for each year
        counts = []
        for year in years:
            # Total students
            total_result = supabase_client.table('students')\
                .select('id', count='exact')\
                .eq('establishment_id', establishment_uuid)\
                .eq('academic_year', year)\
                .execute()
            
            # Students with VESPA data
            students_with_vespa = supabase_client.table('students')\
                .select('id')\
                .eq('establishment_id', establishment_uuid)\
                .eq('academic_year', year)\
                .execute()
            
            student_ids = [s['id'] for s in students_with_vespa.data]
            
            vespa_count = 0
            if student_ids:
                # Check in batches to avoid URL limits
                for i in range(0, len(student_ids), 50):
                    batch = student_ids[i:i+50]
                    vespa_result = supabase_client.table('vespa_scores')\
                        .select('student_id', count='exact')\
                        .in_('student_id', batch)\
                        .eq('academic_year', year)\
                        .execute()
                    vespa_count += vespa_result.count if hasattr(vespa_result, 'count') else 0
            
            counts.append({
                'academic_year': year,
                'total_students': total_result.count if hasattr(total_result, 'count') else 0,
                'students_with_vespa': vespa_count,
                'response_rate': (vespa_count / total_result.count * 100) if total_result.count > 0 else 0
            })
        
        return jsonify(counts)
        
    except Exception as e:
        app.logger.error(f"Failed to get student counts by year: {e}")
        raise ApiError(f"Failed to get student counts: {str(e)}", 500)
"""

# 5. Important considerations:
"""
1. When filtering by academic_year, use the field from students table, not just VESPA data
2. This ensures consistent counts across all dashboard views
3. Students without VESPA data will still be counted in totals
4. Response rates become: (students with VESPA) / (total students in academic year)
"""
