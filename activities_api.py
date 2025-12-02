"""
VESPA Activities V3 - Backend API Endpoints
===========================================
All API endpoints for the activities system migrated from Knack to Supabase.

This module should be imported into app.py and register_routes(app, supabase_client) called.
"""

from flask import request, jsonify
from datetime import datetime
from supabase import Client
import logging

logger = logging.getLogger(__name__)


def register_activities_routes(app, supabase: Client):
    """
    Register all activities API routes with the Flask app.
    
    Args:
        app: Flask application instance
        supabase: Supabase client instance
    """
    
    # ==========================================
    # STUDENT ENDPOINTS
    # ==========================================
    
    @app.route('/api/activities/recommended', methods=['GET'])
    def get_recommended_activities():
        """
        Calculate recommended activities based on VESPA scores
        Query params: email, cycle
        """
        try:
            logger.info(f"[Activities API] /api/activities/recommended called with email={request.args.get('email')}, cycle={request.args.get('cycle')}")
            student_email = request.args.get('email')
            cycle = int(request.args.get('cycle', 1))
            
            if not student_email:
                return jsonify({"error": "email parameter required"}), 400
            
            # Ensure student exists in vespa_students (auto-create if needed)
            ensure_vespa_student_exists(supabase, student_email)
            
            # Try to get VESPA scores from vespa_students.latest_vespa_scores first (cached)
            vespa_student_result = supabase.table('vespa_students').select('latest_vespa_scores, current_level')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            scores = None
            level = 'Level 2'
            actual_cycle = cycle  # Track the actual cycle from cache
            
            if vespa_student_result.data:
                cached_scores = vespa_student_result.data.get('latest_vespa_scores')
                level = vespa_student_result.data.get('current_level', 'Level 2')
                
                # Use cached scores if they exist (always use latest, ignore requested cycle)
                if cached_scores and isinstance(cached_scores, dict):
                    scores = cached_scores
                    actual_cycle = cached_scores.get('cycle') or cached_scores.get('cycle_number') or cycle
            
            # If no cached scores or wrong cycle, fetch from vespa_scores table (legacy)
            if not scores:
                # Note: vespa_scores uses student_id (UUID) from students table, not email
                # First, get student_id from students table
                # Get student records and sort by created_at descending
                student_result = supabase.table('students').select('id,created_at')\
                    .eq('email', student_email)\
                    .limit(10)\
                    .execute()
                
                # Sort by created_at descending and take most recent
                if student_result.data:
                    student_result.data = sorted(student_result.data, 
                        key=lambda x: x.get('created_at', ''), reverse=True)[:1]
                
                if not student_result.data:
                    return jsonify({
                        "error": "Student not found in legacy system",
                        "message": "Please ensure student has completed VESPA questionnaire"
                    }), 404
                
                student_id = student_result.data[0]['id']
                
                # Now query vespa_scores using student_id
                # Note: Get all matching records and sort in Python to avoid desc=True syntax issues
                # Note: Legacy table uses 'cycle' not 'cycle_number'
                scores_result = supabase.table('vespa_scores').select('*')\
                    .eq('student_id', student_id)\
                    .eq('cycle', cycle)\
                    .order('created_at')\
                    .limit(10)\
                    .execute()
                
                # Sort by created_at descending in Python and take first
                if scores_result.data:
                    scores_result.data = sorted(scores_result.data, key=lambda x: x.get('created_at', ''), reverse=True)[:1]
                
                if not scores_result.data:
                    return jsonify({
                        "error": "No VESPA scores found",
                        "message": "Please complete the VESPA questionnaire first"
                    }), 404
                
                scores = scores_result.data[0]
                level = scores.get('level', 'Level 2')
            
            # Calculate which activities to recommend based on scores
            recommended = []
            
            for category in ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude']:
                # Legacy vespa_scores table uses lowercase column names without '_score' suffix
                score_key = category.lower()
                score = scores.get(score_key, 5)
                
                # Fetch activities matching: category, level, score thresholds
                # Show if score_threshold_min <= score <= score_threshold_max OR threshold is NULL
                activities_query = supabase.table('activities').select('*')\
                    .eq('vespa_category', category)\
                    .eq('level', level)\
                    .eq('is_active', True)
                
                # Apply threshold filters
                # Show if: (score_threshold_min IS NULL OR score_threshold_min <= score)
                # AND (score_threshold_max IS NULL OR score_threshold_max >= score)
                activities_result = activities_query\
                    .order('display_order')\
                    .limit(3)\
                    .execute()
                
                # Filter by thresholds in Python (Supabase doesn't support complex OR with NULL easily)
                filtered_activities = []
                for activity in activities_result.data:
                    threshold_min = activity.get('score_threshold_min')
                    threshold_max = activity.get('score_threshold_max')
                    
                    # Show if thresholds are NULL or score is within range
                    show_activity = True
                    if threshold_min is not None and score < threshold_min:
                        show_activity = False
                    if threshold_max is not None and score > threshold_max:
                        show_activity = False
                    
                    if show_activity:
                        filtered_activities.append(activity)
                
                recommended.extend(filtered_activities[:3])  # Top 3 per category
            
            return jsonify({
                "recommended": recommended,
                "vespaScores": scores,
                "level": level,
                "cycle": actual_cycle  # Return the actual cycle from cache, not input parameter
            })
            
        except Exception as e:
            logger.error(f"Error in get_recommended_activities: {str(e)}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e), "type": type(e).__name__}), 500
    
    
    @app.route('/api/activities/by-problem', methods=['GET'])
    def get_activities_by_problem():
        """
        Get activities mapped to specific problems
        Query params: problem_id
        """
        try:
            problem_id = request.args.get('problem_id')
            
            if not problem_id:
                return jsonify({"error": "problem_id parameter required"}), 400
            
            # Fetch activities that have this problem_id in their problem_mappings array
            activities_result = supabase.table('activities').select('*')\
                .contains('problem_mappings', [problem_id])\
                .eq('is_active', True)\
                .order('display_order')\
                .execute()
            
            return jsonify({"activities": activities_result.data})
            
        except Exception as e:
            logger.error(f"Error in get_activities_by_problem: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/activities/assigned', methods=['GET'])
    def get_assigned_activities():
        """
        Get student's assigned/prescribed activities
        Query params: email, cycle
        """
        try:
            student_email = request.args.get('email')
            cycle = int(request.args.get('cycle', 1))
            
            if not student_email:
                return jsonify({"error": "email parameter required"}), 400
            
            # Fetch student's activities (without JOIN - Python client doesn't handle it well)
            assigned_result = supabase.table('student_activities').select('*')\
                .eq('student_email', student_email)\
                .eq('cycle_number', cycle)\
                .neq('status', 'removed')\
                .order('assigned_at')\
                .execute()
            
            # Sort assignments by assigned_at descending (most recent first)
            if assigned_result.data:
                assigned_result.data = sorted(assigned_result.data, 
                    key=lambda x: x.get('assigned_at', ''), reverse=True)
            
            # Fetch activity details separately
            activity_ids = [assignment['activity_id'] for assignment in assigned_result.data]
            
            activities_map = {}
            if activity_ids:
                activities_result = supabase.table('activities').select(
                    'id, name, vespa_category, level, time_minutes, color, difficulty, ' +
                    'do_section_html, think_section_html, learn_section_html, reflect_section_html'
                ).in_('id', activity_ids).execute()
                
                # Create map of activity_id -> activity data
                activities_map = {a['id']: a for a in activities_result.data}
            
            # Also fetch progress for each
            responses_result = supabase.table('activity_responses').select('*')\
                .eq('student_email', student_email)\
                .eq('cycle_number', cycle)\
                .execute()
            
            # Merge activity details and progress into assignments
            progress_map = {r['activity_id']: r for r in responses_result.data}
            
            for assignment in assigned_result.data:
                activity_id = assignment['activity_id']
                # Add activity details
                assignment['activities'] = activities_map.get(activity_id)
                # Add progress
                assignment['progress'] = progress_map.get(activity_id)
            
            return jsonify({"assignments": assigned_result.data})
            
        except Exception as e:
            logger.error(f"Error in get_assigned_activities: {str(e)}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e), "type": type(e).__name__}), 500
    
    
    @app.route('/api/activities/questions', methods=['GET'])
    def get_activity_questions():
        """
        Get all questions for an activity
        Query params: activity_id
        """
        try:
            activity_id = request.args.get('activity_id')
            
            if not activity_id:
                return jsonify({"error": "activity_id parameter required"}), 400
            
            questions_result = supabase.table('activity_questions').select('*')\
                .eq('activity_id', activity_id)\
                .eq('is_active', True)\
                .order('display_order')\
                .execute()
            
            return jsonify({"questions": questions_result.data})
            
        except Exception as e:
            logger.error(f"Error in get_activity_questions: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/activities/start', methods=['POST'])
    def start_activity():
        """
        Start an activity (create initial response record)
        Body: { studentEmail, activityId, cycle?, selectedVia? }
        """
        try:
            data = request.json
            student_email = data.get('studentEmail')
            activity_id = data.get('activityId')
            cycle = data.get('cycle', 1)
            selected_via = data.get('selectedVia', 'student_choice')
            
            if not student_email or not activity_id:
                return jsonify({"error": "studentEmail and activityId required"}), 400
            
            # Ensure student exists
            ensure_vespa_student_exists(supabase, student_email)
            
            # Get current academic year from student record
            student_record = supabase.table('vespa_students').select('current_academic_year')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            academic_year = student_record.data.get('current_academic_year', '2025/2026') if student_record.data else '2025/2026'
            
            # Create response record
            response_data = {
                "student_email": student_email,
                "activity_id": activity_id,
                "cycle_number": cycle,
                "academic_year": academic_year,
                "status": "in_progress",
                "selected_via": selected_via,
                "responses": {},
                "started_at": datetime.utcnow().isoformat()
            }
            
            # Use upsert to handle duplicates gracefully
            result = supabase.table('activity_responses').upsert(
                response_data,
                on_conflict='student_email,activity_id,cycle_number'
            ).execute()
            
            # Update student_activities if not already there
            supabase.table('student_activities').upsert({
                "student_email": student_email,
                "activity_id": activity_id,
                "cycle_number": cycle,
                "assigned_by": selected_via if selected_via != 'student_choice' else 'auto',
                "status": "started",
                "assigned_at": datetime.utcnow().isoformat()
            }, on_conflict='student_email,activity_id,cycle_number').execute()
            
            # Log history
            supabase.table('activity_history').insert({
                "student_email": student_email,
                "activity_id": activity_id,
                "action": "started",
                "triggered_by": "student",
                "triggered_by_email": student_email,
                "cycle_number": cycle,
                "academic_year": academic_year,
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            return jsonify({"success": True, "response": result.data[0] if result.data else {}})
            
        except Exception as e:
            logger.error(f"Error in start_activity: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/activities/save', methods=['POST'])
    def save_activity_progress():
        """
        Auto-save activity progress (called every 30 seconds)
        Body: { studentEmail, activityId, cycle?, responses, timeMinutes? }
        """
        try:
            data = request.json
            student_email = data.get('studentEmail')
            activity_id = data.get('activityId')
            cycle = data.get('cycle', 1)
            responses = data.get('responses', {})
            time_minutes = data.get('timeMinutes', 0)
            
            if not student_email or not activity_id:
                return jsonify({"error": "studentEmail and activityId required"}), 400
            
            # Update responses
            update_data = {
                "responses": responses,
                "time_spent_minutes": time_minutes,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Concatenate text responses for search
            responses_text = ' '.join([
                str(v) for v in responses.values() if isinstance(v, str)
            ])
            if responses_text:
                update_data["responses_text"] = responses_text
            
            result = supabase.table('activity_responses').update(update_data)\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            return jsonify({"success": True, "saved": True})
            
        except Exception as e:
            logger.error(f"Error in save_activity_progress: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/activities/remove', methods=['POST'])
    def remove_student_activity():
        """
        Student removes activity from their dashboard (soft delete)
        Body: { studentEmail, activityId, cycle? }
        """
        try:
            data = request.json
            student_email = data.get('studentEmail')
            activity_id = data.get('activityId')
            cycle = data.get('cycle', 1)
            
            if not student_email or not activity_id:
                return jsonify({"error": "studentEmail and activityId required"}), 400
            
            logger.info(f"[Remove Activity] Student {student_email} removing activity {activity_id} cycle {cycle}")
            
            # Update activity_responses to 'removed' status
            result = supabase.table('activity_responses').update({
                "status": "removed",
                "updated_at": datetime.utcnow().isoformat()
            })\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            # Update student_activities if exists
            supabase.table('student_activities').update({"status": "removed"})\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            # Log history
            supabase.table('activity_history').insert({
                "student_email": student_email,
                "activity_id": activity_id,
                "action": "removed",
                "triggered_by": "student",
                "triggered_by_email": student_email,
                "cycle_number": cycle,
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"[Remove Activity] ✅ Activity removed successfully")
            
            return jsonify({
                "success": True,
                "message": "Activity removed successfully"
            })
            
        except Exception as e:
            logger.error(f"Error in remove_student_activity: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/activities/complete', methods=['POST'])
    def complete_activity():
        """
        Complete an activity (final submission)
        Body: { studentEmail, activityId, cycle?, responses, reflection?, timeMinutes?, wordCount?, pointsEarned? }
        """
        try:
            data = request.json
            student_email = data.get('studentEmail')
            activity_id = data.get('activityId')
            cycle = data.get('cycle', 1)
            responses = data.get('responses', {})
            reflection = data.get('reflection', '')
            time_minutes = data.get('timeMinutes', 0)
            word_count = data.get('wordCount', 0)
            points_earned = data.get('pointsEarned', 10)  # Default 10 points (Level 2)
            
            if not student_email or not activity_id:
                return jsonify({"error": "studentEmail and activityId required"}), 400
            
            # Get academic year
            student_record = supabase.table('vespa_students').select('current_academic_year')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            academic_year = student_record.data.get('current_academic_year', '2025/2026') if student_record.data else '2025/2026'
            
            # Update response to completed
            update_data = {
                "status": "completed",
                "responses": responses,
                "responses_text": reflection or ' '.join([str(v) for v in responses.values() if isinstance(v, str)]),
                "time_spent_minutes": time_minutes,
                "word_count": word_count,
                "points_earned": points_earned,  # Save points earned for this activity
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table('activity_responses').update(update_data)\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            # Update student_activities
            supabase.table('student_activities').update({"status": "completed"})\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            # Update student totals (increment completed count AND add points)
            student_stats = supabase.table('vespa_students').select('total_activities_completed, total_points')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            current_count = student_stats.data.get('total_activities_completed', 0) if student_stats.data else 0
            current_points = student_stats.data.get('total_points', 0) if student_stats.data else 0
            
            supabase.table('vespa_students').update({
                "total_activities_completed": current_count + 1,
                "total_points": current_points + points_earned,  # Add points to total
                "last_activity_at": datetime.utcnow().isoformat()
            }).eq('email', student_email).execute()
            
            logger.info(f"[Complete Activity] ✅ Points awarded: {points_earned}, New total: {current_points + points_earned}")
            
            # Log history
            supabase.table('activity_history').insert({
                "student_email": student_email,
                "activity_id": activity_id,
                "action": "completed",
                "triggered_by": "student",
                "triggered_by_email": student_email,
                "cycle_number": cycle,
                "academic_year": academic_year,
                "metadata": {
                    "time_minutes": time_minutes,
                    "word_count": word_count
                },
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            # Check for new achievements
            achievements_earned = check_and_award_achievements(supabase, student_email)
            
            # Send notification if achievements earned
            if achievements_earned:
                achievement_names = [a.get('achievement_name', 'Achievement') for a in achievements_earned]
                create_notification(
                    supabase,
                    student_email,
                    'achievement_earned',
                    '🏆 New Achievement Unlocked!',
                    f"You earned: {', '.join(achievement_names)}",
                    related_achievement_id=achievements_earned[0].get('id') if achievements_earned else None
                )
            
            return jsonify({
                "success": True,
                "completed": True,
                "newAchievements": achievements_earned
            })
            
        except Exception as e:
            logger.error(f"Error in complete_activity: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    # ==========================================
    # STAFF ENDPOINTS
    # ==========================================
    
    @app.route('/api/staff/students', methods=['GET'])
    def get_staff_students():
        """
        Get all students connected to a staff member
        Query params: staff_email, role
        """
        try:
            staff_email = request.args.get('staff_email')
            role = request.args.get('role', 'tutor')
            
            if not staff_email:
                return jsonify({"error": "staff_email parameter required"}), 400
            
            # Fetch connections
            connections_result = supabase.table('staff_student_connections').select('''
                *,
                vespa_students:student_email (
                    email, first_name, last_name, full_name, current_year_group,
                    current_level, total_activities_completed, total_points,
                    last_activity_at
                )
            ''')\
                .eq('staff_email', staff_email)\
                .eq('staff_role', role)\
                .execute()
            
            students = []
            for conn in connections_result.data:
                student = conn.get('vespa_students')
                if not student:
                    continue
                
                # Get activity stats
                stats_result = supabase.table('activity_responses').select('status', count='exact')\
                    .eq('student_email', student['email'])\
                    .execute()
                
                completed_count = len([r for r in stats_result.data if r.get('status') == 'completed']) if stats_result.data else 0
                
                student['activity_stats'] = {
                    'total': stats_result.count if stats_result.count else 0,
                    'completed': completed_count
                }
                
                students.append(student)
            
            return jsonify({"students": students})
            
        except Exception as e:
            logger.error(f"Error in get_staff_students: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/staff/student-activities', methods=['GET'])
    def get_student_activities_for_staff():
        """
        Get detailed activity breakdown for a student
        Query params: student_email, cycle
        """
        try:
            student_email = request.args.get('student_email')
            cycle = int(request.args.get('cycle', 1))
            
            if not student_email:
                return jsonify({"error": "student_email parameter required"}), 400
            
            # Fetch all responses with activity details
            responses_result = supabase.table('activity_responses').select('''
                *,
                activities:activity_id (
                    id, name, vespa_category, level
                )
            ''')\
                .eq('student_email', student_email)\
                .eq('cycle_number', cycle)\
                .order('updated_at')\
                .execute()
            
            # Sort by updated_at descending (most recent first)
            if responses_result.data:
                responses_result.data = sorted(responses_result.data, 
                    key=lambda x: x.get('updated_at', ''), reverse=True)
            
            # Group by category
            by_category = {}
            for response in responses_result.data:
                activity = response.get('activities', {})
                category = activity.get('vespa_category', 'Unknown')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(response)
            
            return jsonify({
                "responses": responses_result.data,
                "byCategory": by_category
            })
            
        except Exception as e:
            logger.error(f"Error in get_student_activities_for_staff: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/staff/assign-activity', methods=['POST'])
    def assign_activity_to_student():
        """
        Staff assigns activity to student
        Body: { staffEmail, studentEmail, activityIds[], cycle?, reason? }
        """
        try:
            data = request.json
            staff_email = data.get('staffEmail')
            student_email = data.get('studentEmail')
            activity_ids = data.get('activityIds', [])
            cycle = data.get('cycle', 1)
            reason = data.get('reason', 'Staff recommendation')
            
            if not staff_email or not student_email or not activity_ids:
                return jsonify({"error": "staffEmail, studentEmail, and activityIds required"}), 400
            
            # Ensure student exists
            ensure_vespa_student_exists(supabase, student_email)
            
            # Get academic year
            student_record = supabase.table('vespa_students').select('current_academic_year')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            academic_year = student_record.data.get('current_academic_year', '2025/2026') if student_record.data else '2025/2026'
            
            assigned = []
            
            for activity_id in activity_ids:
                # Insert into student_activities
                assignment = {
                    "student_email": student_email,
                    "activity_id": activity_id,
                    "cycle_number": cycle,
                    "assigned_by": staff_email,
                    "assigned_reason": reason,
                    "status": "assigned",
                    "assigned_at": datetime.utcnow().isoformat()
                }
                
                result = supabase.table('student_activities').upsert(
                    assignment,
                    on_conflict='student_email,activity_id,cycle_number'
                ).execute()
                
                assigned.append(result.data[0] if result.data else assignment)
                
                # Log history
                supabase.table('activity_history').insert({
                    "student_email": student_email,
                    "activity_id": activity_id,
                    "action": "assigned",
                    "triggered_by": "staff",
                    "triggered_by_email": staff_email,
                    "cycle_number": cycle,
                    "academic_year": academic_year,
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()
                
                # Create notification for student
                activity_name = get_activity_name(supabase, activity_id)
                create_notification(
                    supabase,
                    student_email,
                    'activity_assigned',
                    '📚 New Activity Assigned',
                    f"Your tutor assigned you: {activity_name}",
                    action_url=f"#vespa-activities?activity={activity_id}&action=view",
                    related_activity_id=activity_id
                )
            
            return jsonify({
                "success": True,
                "assigned": assigned
            })
            
        except Exception as e:
            logger.error(f"Error in assign_activity_to_student: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/staff/feedback', methods=['POST'])
    def give_feedback():
        """
        Staff provides feedback on student's activity
        Body: { staffEmail, responseId, feedbackText }
        """
        try:
            data = request.json
            staff_email = data.get('staffEmail')
            response_id = data.get('responseId')
            feedback_text = data.get('feedbackText')
            
            if not staff_email or not response_id or not feedback_text:
                return jsonify({"error": "staffEmail, responseId, and feedbackText required"}), 400
            
            # Update activity_responses
            result = supabase.table('activity_responses').update({
                "staff_feedback": feedback_text,
                "staff_feedback_by": staff_email,
                "staff_feedback_at": datetime.utcnow().isoformat(),
                "feedback_read_by_student": False
            }).eq('id', response_id).execute()
            
            # Get student email for notification
            if not result.data:
                return jsonify({"error": "Response not found"}), 404
            
            response_data = result.data[0]
            student_email = response_data.get('student_email')
            activity_id = response_data.get('activity_id')
            
            # Create notification
            activity_name = get_activity_name(supabase, activity_id)
            create_notification(
                supabase,
                student_email,
                'feedback_received',
                '💬 New Feedback on Your Activity',
                f"Your tutor left feedback on: {activity_name}",
                action_url=f"#vespa-activities?activity={activity_id}&action=view-feedback",
                related_response_id=response_id,
                related_activity_id=activity_id
            )
            
            return jsonify({"success": True, "feedback_sent": True})
            
        except Exception as e:
            logger.error(f"Error in give_feedback: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/staff/remove-activity', methods=['POST'])
    def remove_activity_from_student():
        """
        Staff removes activity from student's dashboard
        Body: { staffEmail, studentEmail, activityId, cycle? }
        """
        try:
            data = request.json
            staff_email = data.get('staffEmail')
            student_email = data.get('studentEmail')
            activity_id = data.get('activityId')
            cycle = data.get('cycle', 1)
            
            if not staff_email or not student_email or not activity_id:
                return jsonify({"error": "staffEmail, studentEmail, and activityId required"}), 400
            
            # Get academic year
            student_record = supabase.table('vespa_students').select('current_academic_year')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            academic_year = student_record.data.get('current_academic_year', '2025/2026') if student_record.data else '2025/2026'
            
            # Update to removed status
            supabase.table('student_activities').update({
                "status": "removed",
                "removed_at": datetime.utcnow().isoformat()
            })\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            # Log history
            supabase.table('activity_history').insert({
                "student_email": student_email,
                "activity_id": activity_id,
                "action": "removed",
                "triggered_by": "staff",
                "triggered_by_email": staff_email,
                "cycle_number": cycle,
                "academic_year": academic_year,
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            return jsonify({"success": True})
            
        except Exception as e:
            logger.error(f"Error in remove_activity_from_student: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/staff/award-achievement', methods=['POST'])
    def award_achievement():
        """
        Staff manually awards achievement (certificate)
        Body: { staffEmail, studentEmail, achievementType?, achievementName, description?, points?, icon? }
        """
        try:
            data = request.json
            staff_email = data.get('staffEmail')
            student_email = data.get('studentEmail')
            achievement_type = data.get('achievementType', 'custom')
            achievement_name = data.get('achievementName')
            description = data.get('description', '')
            points = data.get('points', 50)
            icon = data.get('icon', '🏅')
            
            if not staff_email or not student_email or not achievement_name:
                return jsonify({"error": "staffEmail, studentEmail, and achievementName required"}), 400
            
            # Ensure student exists
            ensure_vespa_student_exists(supabase, student_email)
            
            # Create achievement
            achievement = {
                "student_email": student_email,
                "achievement_type": achievement_type,
                "achievement_name": achievement_name,
                "achievement_description": description,
                "points_value": points,
                "icon_emoji": icon,
                "issued_by_staff": staff_email,
                "date_earned": datetime.utcnow().isoformat()
            }
            
            result = supabase.table('student_achievements').insert(achievement).execute()
            
            # Update student points
            student_stats = supabase.table('vespa_students').select('total_points')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            current_points = student_stats.data.get('total_points', 0) if student_stats.data else 0
            supabase.table('vespa_students').update({
                "total_points": current_points + points
            }).eq('email', student_email).execute()
            
            # Notify student
            create_notification(
                supabase,
                student_email,
                'achievement_earned',
                f'🎉 Achievement: {achievement_name}',
                description or f"Your tutor awarded you {points} points!",
                related_achievement_id=result.data[0].get('id') if result.data else None
            )
            
            return jsonify({"success": True, "achievement": result.data[0] if result.data else achievement})
            
        except Exception as e:
            logger.error(f"Error in award_achievement: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    # ==========================================
    # NOTIFICATION ENDPOINTS
    # ==========================================
    
    @app.route('/api/notifications', methods=['GET'])
    def get_notifications():
        """
        Get notifications for a user
        Query params: email, unread_only
        """
        try:
            email = request.args.get('email')
            unread_only = request.args.get('unread_only', 'false') == 'true'
            
            if not email:
                return jsonify({"error": "email parameter required"}), 400
            
            query = supabase.table('notifications').select('*').eq('recipient_email', email)
            
            if unread_only:
                query = query.eq('is_read', False)
            
            result = query.order('created_at').limit(100).execute()
            
            # Sort by created_at descending (most recent first) and limit to 50
            if result.data:
                result.data = sorted(result.data, 
                    key=lambda x: x.get('created_at', ''), reverse=True)[:50]
            
            return jsonify({"notifications": result.data})
            
        except Exception as e:
            logger.error(f"Error in get_notifications: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/notifications/mark-read', methods=['POST'])
    def mark_notification_read():
        """
        Mark notification as read
        Body: { notificationId }
        """
        try:
            data = request.json
            notification_id = data.get('notificationId')
            
            if not notification_id:
                return jsonify({"error": "notificationId required"}), 400
            
            supabase.table('notifications').update({
                "is_read": True,
                "read_at": datetime.utcnow().isoformat()
            }).eq('id', notification_id).execute()
            
            return jsonify({"success": True})
            
        except Exception as e:
            logger.error(f"Error in mark_notification_read: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/achievements/check', methods=['GET'])
    def check_achievements():
        """
        Check if student has earned any new achievements
        Query params: email
        """
        try:
            student_email = request.args.get('email')
            
            if not student_email:
                return jsonify({"error": "email parameter required"}), 400
            
            new_achievements = check_and_award_achievements(supabase, student_email)
            
            return jsonify({"newAchievements": new_achievements})
            
        except Exception as e:
            logger.error(f"Error in check_achievements: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/students/stats', methods=['GET'])
    def get_student_stats():
        """
        Get student statistics (total_points, total_activities_completed, total_achievements)
        Query params: email
        """
        try:
            student_email = request.args.get('email')
            
            if not student_email:
                return jsonify({"error": "email parameter required"}), 400
            
            # Ensure student exists
            ensure_vespa_student_exists(supabase, student_email)
            
            # Fetch stats from vespa_students table
            result = supabase.table('vespa_students').select(
                'total_points, total_activities_completed, total_achievements'
            ).eq('email', student_email).single().execute()
            
            if result.data:
                return jsonify({
                    "total_points": result.data.get('total_points', 0),
                    "total_activities_completed": result.data.get('total_activities_completed', 0),
                    "total_achievements": result.data.get('total_achievements', 0)
                })
            else:
                # Return defaults if student doesn't exist yet
                return jsonify({
                    "total_points": 0,
                    "total_activities_completed": 0,
                    "total_achievements": 0
                })
            
        except Exception as e:
            logger.error(f"Error in get_student_stats: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def ensure_vespa_student_exists(supabase: Client, student_email: str, knack_attrs: dict = None):
    """
    Ensure a student exists in vespa_students table.
    Uses the get_or_create_vespa_student database function.
    
    Args:
        supabase: Supabase client
        student_email: Student email address
        knack_attrs: Optional Knack user attributes (from Knack.getUserAttributes())
    """
    try:
        # Call the database function
        if knack_attrs:
            # Supabase Python client handles dict -> JSONB conversion automatically
            result = supabase.rpc('get_or_create_vespa_student', {
                'student_email_param': student_email,
                'knack_attributes': knack_attrs
            }).execute()
            logger.debug(f"Called get_or_create_vespa_student for {student_email} with Knack attrs")
        else:
            # Create minimal record if no knack_attrs provided
            # Check if exists first
            existing = supabase.table('vespa_students').select('id')\
                .eq('email', student_email)\
                .execute()
            
            if not existing.data:
                # ❌ DO NOT CREATE STUDENT HERE!
                # This was creating orphaned students with NULL school_id
                # Students should be created by upload system or sync with full data
                logger.warning(
                    f"⚠️  Student {student_email} does not exist in vespa_students. "
                    f"Student should be uploaded first via upload system. "
                    f"Response will be stored but student won't be visible until uploaded."
                )
                # NOTE: We still allow the questionnaire response to be saved
                # The student will be linked when they are properly uploaded later
            else:
                logger.debug(f"vespa_student already exists for {student_email}")
    except Exception as e:
        logger.warning(f"Error ensuring vespa_student exists: {str(e)}")
        # Don't fail the request if this fails - student might still work


def create_notification(supabase: Client, recipient_email: str, notification_type: str, 
                       title: str, message: str, action_url: str = None, 
                       related_activity_id: str = None, related_response_id: str = None, 
                       related_achievement_id: str = None, priority: str = 'normal'):
    """
    Helper to create notifications
    
    Args:
        supabase: Supabase client
        recipient_email: Email of notification recipient
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        action_url: Optional deep link URL
        related_activity_id: Optional related activity ID
        related_response_id: Optional related response ID
        related_achievement_id: Optional related achievement ID
        priority: Priority level (urgent/high/normal/low)
    """
    try:
        recipient_type = "student" if "student" in notification_type else "staff"
        
        notification = {
            "recipient_email": recipient_email,
            "recipient_type": recipient_type,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "action_url": action_url,
            "related_activity_id": related_activity_id,
            "related_response_id": related_response_id,
            "related_achievement_id": related_achievement_id,
            "priority": priority,
            "is_read": False
        }
        
        supabase.table('notifications').insert(notification).execute()
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")


def check_and_award_achievements(supabase: Client, student_email: str):
    """
    Check all achievement criteria and award if met
    
    Args:
        supabase: Supabase client
        student_email: Student email address
        
    Returns:
        List of newly awarded achievements
    """
    try:
        # Fetch achievement definitions
        achievement_defs_result = supabase.table('achievement_definitions').select('*')\
            .eq('is_active', True)\
            .execute()
        
        if not achievement_defs_result.data:
            return []
        
        # Fetch student's completed responses
        responses_result = supabase.table('activity_responses').select('''
            *,
            activities:activity_id (vespa_category)
        ''')\
            .eq('student_email', student_email)\
            .eq('status', 'completed')\
            .execute()
        
        # Fetch all activities for category calculations
        all_activities_result = supabase.table('activities').select('id, vespa_category')\
            .eq('is_active', True)\
            .execute()
        
        # Count activities by category
        activities_by_category = {}
        for activity in all_activities_result.data:
            category = activity.get('vespa_category')
            if category not in activities_by_category:
                activities_by_category[category] = []
            activities_by_category[category].append(activity['id'])
        
        new_achievements = []
        
        for achievement_def in achievement_defs_result.data:
            criteria = achievement_def.get('criteria', {})
            achievement_type = achievement_def.get('achievement_type')
            
            # Check if already earned
            existing_result = supabase.table('student_achievements').select('id')\
                .eq('student_email', student_email)\
                .eq('achievement_type', achievement_type)\
                .execute()
            
            if existing_result.data:
                continue  # Already has this achievement
            
            # Evaluate criteria
            if evaluate_achievement_criteria(responses_result.data, criteria, activities_by_category):
                # Award it!
                achievement = {
                    "student_email": student_email,
                    "achievement_type": achievement_type,
                    "achievement_name": achievement_def.get('name'),
                    "achievement_description": achievement_def.get('description'),
                    "points_value": achievement_def.get('points_value', 0),
                    "icon_emoji": achievement_def.get('icon_emoji', '🏆'),
                    "criteria_met": criteria,
                    "date_earned": datetime.utcnow().isoformat()
                }
                
                result = supabase.table('student_achievements').insert(achievement).execute()
                
                if result.data:
                    new_achievements.append(result.data[0])
                    
                    # Update student points
                    student_stats = supabase.table('vespa_students').select('total_points')\
                        .eq('email', student_email)\
                        .single()\
                        .execute()
                    
                    current_points = student_stats.data.get('total_points', 0) if student_stats.data else 0
                    supabase.table('vespa_students').update({
                        "total_points": current_points + achievement_def.get('points_value', 0),
                        "total_achievements": (student_stats.data.get('total_achievements', 0) if student_stats.data else 0) + 1
                    }).eq('email', student_email).execute()
        
        return new_achievements
        
    except Exception as e:
        logger.error(f"Error checking achievements: {str(e)}", exc_info=True)
        return []


def evaluate_achievement_criteria(responses, criteria, activities_by_category):
    """
    Evaluate if achievement criteria is met
    
    Args:
        responses: List of completed activity responses
        criteria: Achievement criteria dict
        activities_by_category: Dict mapping category to list of activity IDs
        
    Returns:
        True if criteria is met, False otherwise
    """
    try:
        criteria_type = criteria.get('type')
        
        if criteria_type == 'activities_completed':
            count_required = criteria.get('count', 0)
            category = criteria.get('category')
            
            if category:
                # Count completions in specific category
                category_activity_ids = activities_by_category.get(category, [])
                completed_in_category = [
                    r for r in responses 
                    if r.get('activity_id') in category_activity_ids
                ]
                return len(completed_in_category) >= count_required
            else:
                # Count all completions
                return len(responses) >= count_required
        
        elif criteria_type == 'streak':
            # Check consecutive days
            days_required = criteria.get('days', 0)
            if not responses:
                return False
            
            # Sort by completion date
            completed_dates = []
            for response in responses:
                completed_at = response.get('completed_at')
                if completed_at:
                    try:
                        date = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                        completed_dates.append(date.date())
                    except:
                        pass
            
            if not completed_dates:
                return False
            
            completed_dates = sorted(set(completed_dates), reverse=True)
            
            # Check for consecutive days
            if not completed_dates:
                return False
            
            current_streak = 1
            for i in range(len(completed_dates) - 1):
                if (completed_dates[i] - completed_dates[i + 1]).days == 1:
                    current_streak += 1
                else:
                    break
            
            return current_streak >= days_required
        
        elif criteria_type == 'category_master':
            # Check if completed X% of category
            category = criteria.get('category')
            percentage_required = criteria.get('percentage', 0)
            
            if not category:
                return False
            
            category_activity_ids = activities_by_category.get(category, [])
            if not category_activity_ids:
                return False
            
            completed_in_category = [
                r for r in responses 
                if r.get('activity_id') in category_activity_ids
            ]
            
            completion_percentage = (len(completed_in_category) / len(category_activity_ids)) * 100
            return completion_percentage >= percentage_required
        
        elif criteria_type == 'word_count':
            # Check if any response has word count >= threshold
            word_count_required = criteria.get('word_count', 0)
            
            for response in responses:
                word_count = response.get('word_count', 0)
                if word_count >= word_count_required:
                    return True
            
            return False
        
        elif criteria_type == 'time_efficiency':
            # Check if completed under recommended time
            # Need to compare time_spent_minutes with activity's time_minutes
            # This requires joining with activities table, so we'll need to pass activity data
            # For now, return False (needs more data in responses)
            return False
        
        elif criteria_type == 'all_activities':
            # Check if completed ALL activities (VESPA Master achievement)
            # Count total active activities vs completed
            total_activities = sum(len(ids) for ids in activities_by_category.values())
            return len(responses) >= total_activities
        
        return False
        
    except Exception as e:
        logger.error(f"Error evaluating achievement criteria: {str(e)}", exc_info=True)
        return False


def get_activity_name(supabase: Client, activity_id: str):
    """
    Helper to get activity name
    
    Args:
        supabase: Supabase client
        activity_id: Activity UUID
        
    Returns:
        Activity name or "Unknown Activity"
    """
    try:
        result = supabase.table('activities').select('name').eq('id', activity_id).single().execute()
        return result.data.get('name', 'Unknown Activity') if result.data else "Unknown Activity"
    except Exception as e:
        logger.warning(f"Error getting activity name: {str(e)}")
        return "Unknown Activity"

