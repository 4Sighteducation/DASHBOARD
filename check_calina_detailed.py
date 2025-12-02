from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

email = 'allenc54@hwbcymru.net'

# Find Calina
students = client.table('students').select('*').eq('email', email).execute()

if students.data:
    student = students.data[0]
    print("="*80)
    print(f"CALINA ALLEN - DETAILED SCORE COMPARISON")
    print("="*80)
    
    scores = client.table('vespa_scores')\
        .select('*')\
        .eq('student_id', student['id'])\
        .order('cycle')\
        .execute()
    
    if scores.data:
        print(f"\nFound {len(scores.data)} score records:\n")
        
        for score in scores.data:
            print(f"Cycle {score['cycle']}:")
            print(f"  V:{score['vision']} E:{score['effort']} S:{score['systems']} P:{score['practice']} A:{score['attitude']} O:{score['overall']}")
            print(f"  Completion Date: {score['completion_date']}")
            print(f"  Created: {score.get('created_at', 'N/A')}")
            print()
        
        # Check if all cycles have IDENTICAL scores
        if len(scores.data) >= 2:
            print("="*80)
            print("DUPLICATE CHECK:")
            print("="*80)
            
            c1 = scores.data[0]
            
            for idx in range(1, len(scores.data)):
                cx = scores.data[idx]
                if (c1['vision'] == cx['vision'] and 
                    c1['effort'] == cx['effort'] and
                    c1['systems'] == cx['systems'] and
                    c1['practice'] == cx['practice'] and
                    c1['attitude'] == cx['attitude'] and
                    c1['overall'] == cx['overall'] and
                    c1['completion_date'] == cx['completion_date']):
                    print(f"íº¨ Cycle {cx['cycle']} has IDENTICAL scores to Cycle 1!")
                    print(f"   This is a DUPLICATE, not a real completion!")
                else:
                    print(f"âœ… Cycle {cx['cycle']} has DIFFERENT scores - real completion")
            
            print("\n" + "="*80)
            print("CONCLUSION:")
            print("="*80)
            if all(scores.data[0]['vision'] == s['vision'] and 
                   scores.data[0]['effort'] == s['effort'] and
                   scores.data[0]['systems'] == s['systems'] and
                   scores.data[0]['completion_date'] == s['completion_date'] 
                   for s in scores.data[1:]):
                print("íº¨ ALL CYCLES ARE DUPLICATES OF CYCLE 1")
                print("   Supabase sync created duplicate records")
                print("   Student actually only completed 1 cycle")
            else:
                print("âœ… Cycles have different scores - legitimate completions")

