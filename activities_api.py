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
import os

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
            # Also read year group so we can derive Level 2/3 correctly.
            vespa_student_result = supabase.table('vespa_students').select('latest_vespa_scores, current_level, current_year_group')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            def derive_level_from_year_group(year_group_value: str | None) -> str | None:
                """
                Business rule:
                - Year group < 12 => Level 2
                - Year 12/13 or 'Ugrad' => Level 3
                Returns None if cannot determine.
                """
                if not year_group_value:
                    return None
                yg = str(year_group_value).strip()
                yg_l = yg.lower()
                if 'ugrad' in yg_l or 'undergrad' in yg_l or 'undergraduate' in yg_l:
                    return 'Level 3'
                # Extract digits from strings like "Year 13"
                digits = ''.join(ch for ch in yg if ch.isdigit())
                if digits:
                    try:
                        n = int(digits)
                        return 'Level 3' if n >= 12 else 'Level 2'
                    except Exception:
                        return None
                return None

            scores = None
            # Fallback level: derive from year group first; if still unknown, Level 2.
            level = 'Level 2'
            actual_cycle = cycle  # Track the actual cycle from cache
            
            if vespa_student_result.data:
                cached_scores = vespa_student_result.data.get('latest_vespa_scores')
                year_group = vespa_student_result.data.get('current_year_group')
                derived = derive_level_from_year_group(year_group)
                level = vespa_student_result.data.get('current_level') or derived or 'Level 2'
                
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
            
            # Fetch student's activities from activity_responses (source of truth!)
            # student_activities table can be out of sync - activity_responses is authoritative
            responses_result = supabase.table('activity_responses').select('*')\
                .eq('student_email', student_email)\
                .eq('cycle_number', cycle)\
                .neq('status', 'removed')\
                .order('started_at', desc=True)\
                .execute()
            
            # Use responses as assignments
            assigned_result = responses_result
            
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
            
            # Build clean response (avoid circular references!)
            assignments = []
            for resp in assigned_result.data:
                activity_id = resp['activity_id']
                activity_details = activities_map.get(activity_id)
                
                assignments.append({
                    'activity_id': activity_id,
                    'student_email': resp.get('student_email'),
                    'student_id': resp.get('student_id'),
                    'cycle_number': resp.get('cycle_number'),
                    'status': resp.get('status'),
                    'started_at': resp.get('started_at'),
                    'completed_at': resp.get('completed_at'),
                    'assigned_by': resp.get('assigned_by'),
                    'activities': activity_details,
                    'progress': {
                        'status': resp.get('status'),
                        'started_at': resp.get('started_at'),
                        'completed_at': resp.get('completed_at'),
                        'responses': resp.get('responses'),
                        'word_count': resp.get('word_count'),
                        'time_spent_seconds': resp.get('time_spent_seconds')
                    }
                })
            
            return jsonify({"assignments": assignments})
            
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
            
            logger.info(f"[Start Activity] 📥 Request: email={student_email}, activity={activity_id}, cycle={cycle}, via={selected_via}")
            
            if not student_email or not activity_id:
                logger.error(f"[Start Activity] ❌ Missing required fields")
                return jsonify({"error": "studentEmail and activityId required", "success": False}), 400
            
            # Ensure student exists
            ensure_vespa_student_exists(supabase, student_email)
            
            # Get current academic year from student record
            student_record = supabase.table('vespa_students').select('current_academic_year')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            academic_year = student_record.data.get('current_academic_year', '2025/2026') if student_record.data else '2025/2026'
            
            # Check if record already exists - get full record including responses
            existing = supabase.table('activity_responses').select('*')\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Record already exists, return full record with responses
                logger.info(f"[Start Activity] ✅ Record already exists: {existing.data[0]['id']}, responses: {len(existing.data[0].get('responses', {}) or {})}")
                return jsonify({"success": True, "response": existing.data[0], "existed": True})
            
            # Create new response record
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
            
            result = supabase.table('activity_responses').insert(response_data).execute()
            
            logger.info(f"[Start Activity] ✅ Created new record for {student_email}, activity {activity_id}")
            
            # Also create student_activities record if not exists
            existing_sa = supabase.table('student_activities').select('id')\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            if not existing_sa.data or len(existing_sa.data) == 0:
                supabase.table('student_activities').insert({
                    "student_email": student_email,
                    "activity_id": activity_id,
                    "cycle_number": cycle,
                    "assigned_by": selected_via if selected_via != 'student_choice' else 'auto',
                    "status": "started",
                    "assigned_at": datetime.utcnow().isoformat()
                }).execute()
            
            # Log history
            try:
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
            except Exception as history_err:
                logger.warning(f"[Start Activity] History log failed: {history_err}")
            
            return jsonify({"success": True, "response": result.data[0] if result.data else {}, "existed": False})
            
        except Exception as e:
            logger.error(f"[Start Activity] ❌ Error: {str(e)}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e), "success": False}), 500
    
    
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
            
            logger.info(f"[Save Progress] 📥 Received save request: email={student_email}, activity={activity_id}, cycle={cycle}, responses_count={len(responses)}")
            
            if not student_email or not activity_id:
                logger.error(f"[Save Progress] ❌ Missing required fields: email={student_email}, activity={activity_id}")
                return jsonify({"error": "studentEmail and activityId required", "success": False}), 400
            
            # Concatenate text responses for search
            responses_text = ' '.join([
                str(v) for v in responses.values() if isinstance(v, str)
            ])
            
            # Get academic year
            student_record = supabase.table('vespa_students').select('current_academic_year')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            academic_year = student_record.data.get('current_academic_year', '2025/2026') if student_record.data else '2025/2026'
            
            # First, check if a record exists for this activity
            existing = supabase.table('activity_responses').select('id, status')\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            logger.info(f"[Save Progress] 🔍 Existing record check: found {len(existing.data) if existing.data else 0} records")
            
            if existing.data and len(existing.data) > 0:
                # UPDATE existing record
                record_id = existing.data[0]['id']
                existing_status = existing.data[0]['status']
                logger.info(f"[Save Progress] 📝 Updating existing record {record_id}, current status: {existing_status}")
                
                # DON'T overwrite 'completed' status with 'in_progress'!
                # If activity is completed, keep it completed (allow response edits but preserve status)
                new_status = existing_status if existing_status == 'completed' else 'in_progress'
                
                update_data = {
                    "responses": responses,
                    "responses_text": responses_text if responses_text else '',
                    "time_spent_minutes": time_minutes,
                    "status": new_status,  # Preserve completed status!
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                result = supabase.table('activity_responses').update(update_data)\
                    .eq('id', record_id)\
                    .execute()
                
                logger.info(f"[Save Progress] ✅ Updated record {record_id}, status kept as: {new_status}")
            else:
                # INSERT new record
                logger.info(f"[Save Progress] 📝 Creating new record for {student_email}, activity {activity_id}")
                
                insert_data = {
                    "student_email": student_email,
                    "activity_id": activity_id,
                    "cycle_number": cycle,
                    "academic_year": academic_year,
                    "responses": responses,
                    "responses_text": responses_text if responses_text else '',
                    "time_spent_minutes": time_minutes,
                    "status": "in_progress",
                    "started_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                result = supabase.table('activity_responses').insert(insert_data).execute()
                
                logger.info(f"[Save Progress] ✅ Inserted new record for {student_email}, activity {activity_id}")
            
            return jsonify({"success": True, "saved": True})
            
        except Exception as e:
            logger.error(f"[Save Progress] ❌ Error: {str(e)}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e), "success": False}), 500
    
    
    @app.route('/api/students/welcome-status', methods=['GET'])
    def get_welcome_modal_status():
        """
        Check if student has seen welcome modal for a specific cycle
        Query params: email, cycle
        Returns: { has_seen: true/false, cycle: X }
        """
        try:
            student_email = request.args.get('email')
            cycle = int(request.args.get('cycle', 1))
            
            if not student_email:
                return jsonify({"error": "email parameter required"}), 400
            
            # Query vespa_students for has_seen_welcome_cycle_X
            field_name = f'has_seen_welcome_cycle_{cycle}'
            result = supabase.table('vespa_students').select(field_name)\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            has_seen = False
            if result.data and field_name in result.data:
                has_seen = result.data[field_name] or False
            
            logger.info(f"[Welcome Status] {student_email} Cycle {cycle}: {has_seen}")
            
            return jsonify({
                "has_seen": has_seen,
                "cycle": cycle,
                "email": student_email
            })
            
        except Exception as e:
            logger.error(f"Error in get_welcome_modal_status: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/students/welcome-seen', methods=['POST'])
    def mark_welcome_modal_seen():
        """
        Mark that student has seen welcome modal for a specific cycle
        Body: { email, cycle }
        """
        try:
            data = request.json
            student_email = data.get('email')
            cycle = int(data.get('cycle', 1))
            
            if not student_email:
                return jsonify({"error": "email required"}), 400
            
            # Update has_seen_welcome_cycle_X field
            field_name = f'has_seen_welcome_cycle_{cycle}'
            update_data = {field_name: True}
            
            result = supabase.table('vespa_students').update(update_data)\
                .eq('email', student_email)\
                .execute()
            
            logger.info(f"[Welcome Seen] {student_email} Cycle {cycle} marked as seen")
            
            return jsonify({
                "success": True,
                "cycle": cycle,
                "email": student_email
            })
            
        except Exception as e:
            logger.error(f"Error in mark_welcome_modal_seen: {str(e)}", exc_info=True)
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
            
            logger.info(f"[Complete Activity] 📤 Request for {activity_id}, student: {student_email}, cycle: {cycle}")
            
            # CRITICAL: Check if activity is ALREADY completed - prevent duplicate points!
            existing_response = supabase.table('activity_responses').select('id, status')\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .maybe_single()\
                .execute()
            
            was_already_completed = existing_response.data and existing_response.data.get('status') == 'completed'
            
            if was_already_completed:
                logger.info(f"[Complete Activity] ⚠️ Activity already completed - will update responses but NOT award points")
            
            # Get academic year
            student_record = supabase.table('vespa_students').select('current_academic_year')\
                .eq('email', student_email)\
                .single()\
                .execute()
            
            academic_year = student_record.data.get('current_academic_year', '2025/2026') if student_record.data else '2025/2026'
            
            # Update response to completed
            # NOTE: points_earned column may not exist in activity_responses table
            # Points are tracked in vespa_students.total_points instead
            update_data = {
                "status": "completed",
                "responses": responses,
                "responses_text": reflection or ' '.join([str(v) for v in responses.values() if isinstance(v, str)]),
                "time_spent_minutes": time_minutes,
                "word_count": word_count,
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"[Complete Activity] 📝 Attempting to update activity_responses to 'completed'")
            logger.info(f"[Complete Activity] 🔍 Query: student_email={student_email}, activity_id={activity_id}, cycle={cycle}")
            
            result = supabase.table('activity_responses').update(update_data)\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"[Complete Activity] ✅ Updated {len(result.data)} record(s) to completed")
                logger.info(f"[Complete Activity] 📊 Updated record status: {result.data[0].get('status')}")
            else:
                logger.error(f"[Complete Activity] ❌ NO RECORDS UPDATED! Check if record exists")
                logger.error(f"[Complete Activity] 🔍 Result: {result}")
            
            # Update student_activities
            supabase.table('student_activities').update({"status": "completed"})\
                .eq('student_email', student_email)\
                .eq('activity_id', activity_id)\
                .eq('cycle_number', cycle)\
                .execute()
            
            # Update student totals (increment completed count AND add points)
            # ONLY award points if this is the FIRST time completing this activity in this cycle
            if not was_already_completed:
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
            else:
                # Still update last_activity_at for re-submissions
                supabase.table('vespa_students').update({
                    "last_activity_at": datetime.utcnow().isoformat()
                }).eq('email', student_email).execute()
                
                logger.info(f"[Complete Activity] 📝 Re-submission saved (no new points - already completed)")
            
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
            
            # Notify staff who assigned the activity
            try:
                # Get who assigned this activity
                assignment = supabase.table('student_activities')\
                    .select('assigned_by')\
                    .eq('student_email', student_email)\
                    .eq('activity_id', activity_id)\
                    .eq('cycle_number', cycle)\
                    .single()\
                    .execute()
                
                if assignment.data and assignment.data.get('assigned_by'):
                    staff_email = assignment.data['assigned_by']
                    activity_name = get_activity_name(supabase, activity_id)
                    
                    # Get student name
                    student_data = supabase.table('vespa_students')\
                        .select('full_name, first_name')\
                        .eq('email', student_email)\
                        .single()\
                        .execute()
                    
                    student_name = student_data.data.get('first_name') or student_data.data.get('full_name', student_email) if student_data.data else student_email
                    
                    create_notification(
                        supabase,
                        staff_email,
                        'staff_note',  # Use valid notification type
                        '✅ Activity Completed!',
                        f"{student_name} completed: {activity_name}",
                        action_url=f"#activity-dashboard?student={student_email}",
                        related_activity_id=activity_id
                    )
                    logger.info(f"[Complete Activity] Notified staff {staff_email}")
            except Exception as notif_err:
                logger.warning(f"Failed to notify staff: {notif_err}")
            
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
            
            # Always exclude dismissed notifications
            query = supabase.table('notifications').select('*')\
                .eq('recipient_email', email)\
                .eq('is_dismissed', False)
            
            if unread_only:
                query = query.eq('is_read', False)
            
            result = query.order('created_at').limit(100).execute()
            
            # Sort by created_at descending (most recent first) and limit to 50
            if result.data:
                result.data = sorted(result.data, 
                    key=lambda x: x.get('created_at', ''), reverse=True)[:50]
            
            logger.info(f"[Notifications] Fetched {len(result.data or [])} for {email}")
            
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
    
    
    @app.route('/api/notifications/dismiss', methods=['POST'])
    def dismiss_notification():
        """
        Dismiss a notification
        Body: { notificationId }
        """
        try:
            data = request.json
            notification_id = data.get('notificationId')
            
            logger.info(f"[Dismiss Notification] 📥 Request to dismiss: {notification_id}")
            
            if not notification_id:
                logger.error("[Dismiss Notification] ❌ No notificationId provided")
                return jsonify({"error": "notificationId required", "success": False}), 400
            
            # Update the notification
            result = supabase.table('notifications').update({
                "is_dismissed": True
            }).eq('id', notification_id).execute()
            
            logger.info(f"[Dismiss Notification] ✅ Dismissed notification {notification_id}, result: {len(result.data) if result.data else 0} rows affected")
            
            return jsonify({"success": True, "dismissed": notification_id})
            
        except Exception as e:
            logger.error(f"[Dismiss Notification] ❌ Error: {str(e)}", exc_info=True)
            return jsonify({"error": str(e), "success": False}), 500
    
    
    @app.route('/api/notifications/create', methods=['POST'])
    def create_notification_endpoint():
        """
        Create a notification for a user (used by frontend to trigger notifications)
        Body: { recipientEmail, notificationType, title, message, relatedActivityId?, staffEmail? }
        """
        try:
            data = request.json
            recipient_email = data.get('recipientEmail')
            notification_type = data.get('notificationType')
            title = data.get('title')
            message = data.get('message')
            related_activity_id = data.get('relatedActivityId')
            staff_email = data.get('staffEmail')
            
            if not recipient_email or not notification_type or not title:
                return jsonify({"error": "recipientEmail, notificationType, and title required"}), 400
            
            # Get activity name if we have an activity ID
            if related_activity_id and message and 'new activity' in message.lower():
                activity_name = get_activity_name(supabase, related_activity_id)
                message = f"Your tutor assigned you: {activity_name}"
            
            create_notification(
                supabase,
                recipient_email,
                notification_type,
                title,
                message or f"You have a new {notification_type}",
                action_url=f"#vespa-activities?activity={related_activity_id}&action=view" if related_activity_id else None,
                related_activity_id=related_activity_id
            )
            
            return jsonify({"success": True})
            
        except Exception as e:
            logger.error(f"Error in create_notification_endpoint: {str(e)}", exc_info=True)
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
    
    
    @app.route('/api/students/gamification', methods=['GET'])
    def get_student_gamification():
        """
        Get full gamification data for student (stats, achievements, streak)
        Query params: email
        """
        try:
            student_email = request.args.get('email')
            
            if not student_email:
                return jsonify({"error": "email parameter required"}), 400
            
            # Ensure student exists
            ensure_vespa_student_exists(supabase, student_email)
            
            # Fetch stats from vespa_students table
            stats_result = supabase.table('vespa_students').select(
                'total_points, total_activities_completed, total_achievements, current_streak_days'
            ).eq('email', student_email).single().execute()
            
            stats = stats_result.data if stats_result.data else {
                'total_points': 0,
                'total_activities_completed': 0,
                'total_achievements': 0,
                'current_streak_days': 0
            }
            
            # Calculate actual streak from completed responses
            responses_result = supabase.table('activity_responses').select('completed_at')\
                .eq('student_email', student_email)\
                .eq('status', 'completed')\
                .not_.is_('completed_at', 'null')\
                .execute()
            
            current_streak = _calculate_streak(responses_result.data) if responses_result.data else 0
            
            # Update streak in vespa_students if different
            if current_streak != stats.get('current_streak_days', 0):
                supabase.table('vespa_students').update({
                    'current_streak_days': current_streak
                }).eq('email', student_email).execute()
            
            # Fetch all achievements
            achievements_result = supabase.table('student_achievements').select('*')\
                .eq('student_email', student_email)\
                .order('date_earned', desc=True)\
                .execute()
            
            return jsonify({
                "total_points": stats.get('total_points', 0),
                "total_activities_completed": stats.get('total_activities_completed', 0),
                "total_achievements": stats.get('total_achievements', 0),
                "current_streak": current_streak,
                "achievements": achievements_result.data if achievements_result.data else []
            })
            
        except Exception as e:
            logger.error(f"Error in get_student_gamification: {str(e)}", exc_info=True)
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
                       related_achievement_id: str = None, priority: str = 'normal',
                       send_email: bool = True):
    """
    Helper to create notifications and optionally send email
    
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
        send_email: Whether to send email notification
    """
    try:
        # Determine recipient type based on notification type
        # Student notifications: activity_assigned, feedback_received, achievement_earned, reminder, milestone
        # Staff notifications: activity_completed, feedback_requested
        student_notification_types = ['activity_assigned', 'feedback_received', 'achievement_earned', 
                                      'reminder', 'milestone', 'encouragement', 'staff_note']
        recipient_type = "student" if notification_type in student_notification_types else "staff"
        
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
        
        # Send email notification if enabled
        if send_email and should_send_email(supabase, recipient_email, notification_type):
            send_email_notification(recipient_email, title, message, notification_type)
            
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")


def should_send_email(supabase: Client, email: str, notification_type: str) -> bool:
    """
    Check if user has email notifications enabled for this type
    """
    try:
        result = supabase.table('vespa_students').select('notification_preferences')\
            .eq('email', email)\
            .single()\
            .execute()
        
        if result.data and result.data.get('notification_preferences'):
            prefs = result.data['notification_preferences']
            # Default to True if not set
            return prefs.get(f'email_{notification_type}', True)
        
        return True  # Default to sending emails
    except:
        return True  # Default to sending emails on error


def send_email_notification(to_email: str, subject: str, message: str, notification_type: str):
    """
    Send email notification via SendGrid
    """
    import requests
    
    try:
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@vespa.academy')
        
        if not sendgrid_api_key:
            logger.warning("SendGrid API key not configured, skipping email")
            return
        
        # Build email HTML
        html_content = build_email_html(subject, message, notification_type)
        
        # SendGrid API request
        headers = {
            'Authorization': f'Bearer {sendgrid_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'personalizations': [{'to': [{'email': to_email}]}],
            'from': {'email': from_email, 'name': 'VESPA Activities'},
            'subject': subject,
            'content': [
                {'type': 'text/plain', 'value': message},
                {'type': 'text/html', 'value': html_content}
            ]
        }
        
        response = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 202:
            logger.info(f"Email sent successfully to {to_email}")
        else:
            logger.error(f"SendGrid error: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")


def build_email_html(subject: str, message: str, notification_type: str) -> str:
    """
    Build HTML email template
    """
    icon = {
        'feedback_received': '💬',
        'activity_assigned': '📚',
        'achievement_earned': '🏆',
        'reminder': '⏰',
        'milestone': '🎯',
        'staff_note': '✉️',
        'encouragement': '⭐'
    }.get(notification_type, '🔔')
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #f5f9fc;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <tr>
                <td style="background: linear-gradient(135deg, #079baa 0%, #057a87 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">VESPA Activities</h1>
                </td>
            </tr>
            <tr>
                <td style="background: white; padding: 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <div style="text-align: center; font-size: 48px; margin-bottom: 20px;">{icon}</div>
                    <h2 style="color: #23356f; margin: 0 0 16px 0; text-align: center;">{subject}</h2>
                    <p style="color: #495057; line-height: 1.6; margin: 0 0 24px 0; text-align: center;">{message}</p>
                    <div style="text-align: center;">
                        <a href="https://vespa.knack.com" style="display: inline-block; background: #079baa; color: white; text-decoration: none; padding: 12px 32px; border-radius: 8px; font-weight: 600;">
                            View in VESPA
                        </a>
                    </div>
                </td>
            </tr>
            <tr>
                <td style="text-align: center; padding: 20px; color: #6c757d; font-size: 12px;">
                    <p style="margin: 0;">You're receiving this because you have email notifications enabled.</p>
                    <p style="margin: 8px 0 0 0;">To change your preferences, visit your VESPA dashboard settings.</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


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


def _calculate_streak(responses):
    """
    Calculate current streak (consecutive days with completions)
    
    Args:
        responses: List of completed activity responses
        
    Returns:
        Number of consecutive days with completions (ending today or yesterday)
    """
    from datetime import date, timedelta
    
    if not responses:
        return 0
    
    # Extract unique completion dates
    completed_dates = set()
    for response in responses:
        completed_at = response.get('completed_at')
        if completed_at:
            try:
                if isinstance(completed_at, str):
                    dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                else:
                    dt = completed_at
                completed_dates.add(dt.date())
            except Exception:
                pass
    
    if not completed_dates:
        return 0
    
    # Sort dates in descending order
    sorted_dates = sorted(completed_dates, reverse=True)
    
    # Check if streak includes today or yesterday
    today = date.today()
    if sorted_dates[0] < today - timedelta(days=1):
        return 0  # Streak is broken
    
    # Count consecutive days
    streak = 1
    for i in range(len(sorted_dates) - 1):
        if (sorted_dates[i] - sorted_dates[i + 1]).days == 1:
            streak += 1
        else:
            break
    
    return streak


def evaluate_achievement_criteria(responses, criteria, activities_by_category):
    """
    Evaluate if achievement criteria is met
    
    Supports two formats:
    - Simple: {"min_completed": 5} or {"category": "Vision", "min_completed": 5}
    - Complex: {"type": "activities_completed", "count": 5}
    
    Args:
        responses: List of completed activity responses
        criteria: Achievement criteria dict
        activities_by_category: Dict mapping category to list of activity IDs
        
    Returns:
        True if criteria is met, False otherwise
    """
    try:
        # Support simple format: {"min_completed": X}
        min_completed = criteria.get('min_completed')
        if min_completed is not None:
            category = criteria.get('category')
            
            if category:
                # Count completions in specific category
                category_activity_ids = activities_by_category.get(category, [])
                completed_in_category = [
                    r for r in responses 
                    if r.get('activity_id') in category_activity_ids
                ]
                return len(completed_in_category) >= min_completed
            else:
                # Count all completions
                return len(responses) >= min_completed
        
        # Support simple format: {"streak_days": X}
        streak_days = criteria.get('streak_days')
        if streak_days is not None:
            return _calculate_streak(responses) >= streak_days
        
        # Legacy type-based format
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

