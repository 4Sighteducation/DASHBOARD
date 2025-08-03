# VESPA Dashboard API v2 - Supabase Only
# Clean implementation with no Knack dependencies

from flask import Blueprint, jsonify, request, g
from functools import wraps
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import logging

# Create blueprint
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# Supabase client
supabase: Client = None

def init_supabase():
    """Initialize Supabase client"""
    global supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not configured")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

# Initialize on import
try:
    init_supabase()
except Exception as e:
    logging.error(f"Failed to initialize Supabase: {e}")

# Authentication decorator
def require_auth(f):
    """Decorator to require authentication and load user info"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user email from request header (set by your auth system)
        user_email = request.headers.get('X-User-Email')
        
        if not user_email:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Load user access info
        try:
            # Check if super user
            super_user = supabase.table('super_users').select('*').eq('email', user_email).execute()
            if super_user.data:
                g.user = {
                    'email': user_email,
                    'role': 'super_user',
                    'super_user_id': super_user.data[0]['id']
                }
            else:
                # Check if staff admin
                staff_admin = supabase.table('staff_admins').select('*').eq('email', user_email).execute()
                if staff_admin.data:
                    g.user = {
                        'email': user_email,
                        'role': 'staff_admin',
                        'staff_admin_id': staff_admin.data[0]['id'],
                        'establishment_id': staff_admin.data[0].get('establishment_id')
                    }
                else:
                    return jsonify({'error': 'User not found'}), 404
                    
        except Exception as e:
            logging.error(f"Auth check failed: {e}")
            return jsonify({'error': 'Authentication failed'}), 500
            
        return f(*args, **kwargs)
    return decorated_function

# User Access Endpoint
@api_v2.route('/user/access', methods=['GET'])
@require_auth
def get_user_access():
    """Get user's role and accessible establishments"""
    try:
        user = g.user
        
        if user['role'] == 'super_user':
            # Super users can access all establishments
            establishments = supabase.table('establishments').select('id, name, trust_id').order('name').execute()
            return jsonify({
                'role': 'super_user',
                'email': user['email'],
                'establishments': establishments.data,
                'canEmulate': True
            })
        else:
            # Staff admins can only access their establishment
            if not user.get('establishment_id'):
                return jsonify({'error': 'No establishment assigned'}), 403
                
            establishment = supabase.table('establishments').select('id, name, trust_id').eq('id', user['establishment_id']).execute()
            
            if not establishment.data:
                return jsonify({'error': 'Establishment not found'}), 404
                
            return jsonify({
                'role': 'staff_admin',
                'email': user['email'],
                'establishments': establishment.data,
                'canEmulate': False
            })
            
    except Exception as e:
        logging.error(f"Error getting user access: {e}")
        return jsonify({'error': str(e)}), 500

# Dashboard Data Endpoint
@api_v2.route('/dashboard/data', methods=['POST'])
@require_auth
def get_dashboard_data():
    """Get all dashboard data in one request"""
    try:
        data = request.json
        establishment_id = data.get('establishmentId')
        cycle = data.get('cycle', 1)
        filters = data.get('filters', {})
        
        # Verify user has access to this establishment
        user = g.user
        if user['role'] == 'staff_admin' and user.get('establishment_id') != establishment_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get school statistics (pre-calculated)
        school_stats = supabase.table('school_statistics').select('*').eq('establishment_id', establishment_id).eq('cycle', cycle).execute()
        
        # Get national statistics for comparison
        national_stats = supabase.table('national_statistics').select('*').eq('cycle', cycle).execute()
        
        # Calculate ERI (Engagement Readiness Index)
        school_eri = calculate_eri(school_stats.data)
        national_eri = calculate_eri(national_stats.data)
        
        # Get filter options
        students_query = supabase.table('students').select('year_group, faculty, course').eq('establishment_id', establishment_id)
        students = students_query.execute()
        
        # Extract unique values for filters
        year_groups = list(set([s['year_group'] for s in students.data if s['year_group']]))
        faculties = list(set([s['faculty'] for s in students.data if s['faculty']]))
        courses = list(set([s['course'] for s in students.data if s['course']]))
        
        return jsonify({
            'schoolERI': school_eri,
            'nationalERI': national_eri,
            'studentCount': len(students.data),
            'responseRate': calculate_response_rate(establishment_id, cycle),
            'filterOptions': {
                'yearGroups': sorted(year_groups),
                'faculties': sorted(faculties),
                'courses': sorted(courses)
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

# Statistics Endpoint
@api_v2.route('/statistics/<establishment_id>/<int:cycle>', methods=['GET'])
@require_auth
def get_statistics(establishment_id, cycle):
    """Get detailed statistics for establishment"""
    try:
        # Verify access
        user = g.user
        if user['role'] == 'staff_admin' and user.get('establishment_id') != establishment_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get school statistics
        school_stats = supabase.table('school_statistics').select('*').eq('establishment_id', establishment_id).eq('cycle', cycle).execute()
        
        # Get national statistics
        national_stats = supabase.table('national_statistics').select('*').eq('cycle', cycle).execute()
        
        # Organize by element
        result = {
            'school': {},
            'national': {}
        }
        
        for stat in school_stats.data:
            element = stat['element']
            result['school'][element] = {
                'mean': float(stat['mean']) if stat['mean'] else 0,
                'std_dev': float(stat['std_dev']) if stat['std_dev'] else 0,
                'count': stat['count'],
                'distribution': stat['distribution']
            }
            
        for stat in national_stats.data:
            element = stat['element']
            result['national'][element] = {
                'mean': float(stat['mean']) if stat['mean'] else 0,
                'std_dev': float(stat['std_dev']) if stat['std_dev'] else 0,
                'count': stat['count']
            }
            
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500

# QLA Analysis Endpoint
@api_v2.route('/qla/analysis', methods=['POST'])
@require_auth
def get_qla_analysis():
    """Get Question Level Analysis data"""
    try:
        data = request.json
        establishment_id = data.get('establishmentId')
        cycle = data.get('cycle', 1)
        filters = data.get('filters', {})
        
        # Verify access
        user = g.user
        if user['role'] == 'staff_admin' and user.get('establishment_id') != establishment_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get question statistics
        question_stats = supabase.table('question_statistics').select('*').eq('establishment_id', establishment_id).eq('cycle', cycle).execute()
        
        # Get question metadata
        questions = supabase.table('questions').select('*').eq('active', True).execute()
        question_map = {q['id']: q for q in questions.data}
        
        # Combine statistics with question text
        enhanced_stats = []
        for stat in question_stats.data:
            if stat['question_id'] in question_map:
                enhanced_stats.append({
                    'id': stat['question_id'],
                    'text': question_map[stat['question_id']]['text'],
                    'category': question_map[stat['question_id']]['category'],
                    'mean': float(stat['mean']) if stat['mean'] else 0,
                    'std_dev': float(stat['std_dev']) if stat['std_dev'] else 0,
                    'count': stat['count'],
                    'distribution': stat['distribution']
                })
        
        # Sort by mean score
        enhanced_stats.sort(key=lambda x: x['mean'], reverse=True)
        
        # Get top and bottom questions
        top_questions = enhanced_stats[:5]
        bottom_questions = enhanced_stats[-5:]
        
        return jsonify({
            'questions': enhanced_stats,
            'topQuestions': top_questions,
            'bottomQuestions': bottom_questions,
            'totalQuestions': len(enhanced_stats)
        })
        
    except Exception as e:
        logging.error(f"Error getting QLA data: {e}")
        return jsonify({'error': str(e)}), 500

# Insights Endpoint
@api_v2.route('/insights/<establishment_id>/<int:cycle>', methods=['GET'])
@require_auth
def get_insights(establishment_id, cycle):
    """Get AI-generated insights for establishment"""
    try:
        # Verify access
        user = g.user
        if user['role'] == 'staff_admin' and user.get('establishment_id') != establishment_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # For now, return pre-defined insights based on statistics
        # In production, this would call an AI service
        school_stats = supabase.table('school_statistics').select('*').eq('establishment_id', establishment_id).eq('cycle', cycle).execute()
        
        insights = []
        
        # Analyze each VESPA element
        for stat in school_stats.data:
            if stat['mean']:
                mean = float(stat['mean'])
                element = stat['element']
                
                if mean < 5:
                    insights.append({
                        'icon': 'exclamation-triangle',
                        'title': f'Low {element.title()} Scores',
                        'description': f'Average {element} score is {mean:.1f}, which is below the expected range.',
                        'recommendation': f'Consider targeted interventions to improve {element} skills.'
                    })
                elif mean > 8:
                    insights.append({
                        'icon': 'star',
                        'title': f'Strong {element.title()} Performance',
                        'description': f'Students are excelling in {element} with an average score of {mean:.1f}.',
                        'recommendation': f'Continue current {element} strategies and share best practices.'
                    })
        
        # Add comparative insight
        insights.append({
            'icon': 'chart-line',
            'title': 'Progress Tracking',
            'description': f'Cycle {cycle} data shows overall engagement levels.',
            'recommendation': 'Compare with previous cycles to identify trends.'
        })
        
        return jsonify(insights[:4])  # Return top 4 insights
        
    except Exception as e:
        logging.error(f"Error getting insights: {e}")
        return jsonify({'error': str(e)}), 500

# Utility Functions
def calculate_eri(statistics):
    """Calculate Engagement Readiness Index from statistics"""
    if not statistics:
        return 0
    
    total_score = 0
    count = 0
    
    for stat in statistics:
        if stat['mean'] and stat['element'] != 'overall':
            total_score += float(stat['mean'])
            count += 1
    
    if count == 0:
        return 0
        
    # Convert to percentage (assuming 10-point scale)
    return round((total_score / count) * 10, 1)

def calculate_response_rate(establishment_id, cycle):
    """Calculate response rate for establishment"""
    try:
        # Get total students
        total_students = supabase.table('students').select('count', count='exact').eq('establishment_id', establishment_id).execute()
        
        # Get students with responses
        responded_students = supabase.table('vespa_scores').select('student_id', count='exact').eq('cycle', cycle).execute()
        
        if total_students.count == 0:
            return 0
            
        return round((responded_students.count / total_students.count) * 100, 1)
        
    except Exception:
        return 0

# Error handler
@api_v2.errorhandler(Exception)
def handle_error(error):
    logging.error(f"Unhandled error: {error}")
    return jsonify({'error': 'Internal server error'}), 500