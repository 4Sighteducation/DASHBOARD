"""
Backfill Student Points and Activity Counts
Calculates points for students who completed activities before the gamification system was implemented.

Points Calculation:
- Level 2 activities = 10 points
- Level 3 activities = 15 points
"""

from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Service key for admin access
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def backfill_points():
    """
    Recalculate and update points for all students based on completed activities
    """
    print("🚀 Starting points backfill...\n")
    
    # Get all completed activities with activity details
    completed_activities = supabase.table('activity_responses').select('''
        student_email,
        activity_id,
        status,
        activities:activity_id (
            id,
            name,
            level
        )
    ''').eq('status', 'completed').execute()
    
    if not completed_activities.data:
        print("❌ No completed activities found")
        return
    
    print(f"✅ Found {len(completed_activities.data)} completed activities\n")
    
    # Group by student
    student_activities = {}
    for response in completed_activities.data:
        email = response['student_email']
        activity = response['activities']
        
        if not activity:
            continue
            
        if email not in student_activities:
            student_activities[email] = []
        
        student_activities[email].append(activity)
    
    print(f"📊 Processing {len(student_activities)} students...\n")
    
    # Calculate points for each student
    updates_made = 0
    for email, activities in student_activities.items():
        total_points = 0
        total_completed = len(activities)
        
        for activity in activities:
            level = activity.get('level', 'Level 2')
            points = 15 if level == 'Level 3' else 10
            total_points += points
        
        # Get current values from database
        current_student = supabase.table('vespa_students').select(
            'total_points, total_activities_completed'
        ).eq('email', email).maybe_single().execute()
        
        current_points = current_student.data.get('total_points', 0) if current_student.data else 0
        current_count = current_student.data.get('total_activities_completed', 0) if current_student.data else 0
        
        # Only update if different
        if current_points != total_points or current_count != total_completed:
            print(f"📝 {email}:")
            print(f"   Completed: {current_count} → {total_completed}")
            print(f"   Points: {current_points} → {total_points}")
            
            supabase.table('vespa_students').update({
                'total_points': total_points,
                'total_activities_completed': total_completed
            }).eq('email', email).execute()
            
            updates_made += 1
            print(f"   ✅ Updated\n")
        else:
            print(f"✓ {email}: Already correct (count={total_completed}, points={total_points})")
    
    print(f"\n🎉 Backfill complete! Updated {updates_made} students.")

if __name__ == '__main__':
    try:
        backfill_points()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

