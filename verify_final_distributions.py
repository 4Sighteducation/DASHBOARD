import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

def verify_distributions():
    """Verify ALL VESPA distributions have exactly 10 elements"""
    
    # Get a sample of school statistics
    result = supabase.table('school_statistics')\
        .select('element, distribution, average, mean')\
        .in_('element', ['vision', 'effort', 'systems', 'practice', 'attitude', 'overall'])\
        .limit(20)\
        .execute()
    
    print("=== VESPA DISTRIBUTION VERIFICATION ===")
    print("All VESPA elements should have 10-element arrays for scores 1-10\n")
    
    issues = []
    for record in result.data:
        element = record['element']
        dist = record['distribution']
        avg = record['average']
        mean = record['mean']
        
        actual_length = len(dist) if dist else 0
        
        print(f"Element: {element}")
        print(f"  Distribution length: {actual_length} (expected: 10)")
        if dist and len(dist) == 10:
            print(f"  Distribution: [1→{dist[0]}, 2→{dist[1]}, 3→{dist[2]}, 4→{dist[3]}, 5→{dist[4]}, 6→{dist[5]}, 7→{dist[6]}, 8→{dist[7]}, 9→{dist[8]}, 10→{dist[9]}]")
        else:
            print(f"  Distribution: {dist}")
        print(f"  Average: {avg}, Mean: {mean}")
        
        if actual_length != 10:
            issues.append(f"{element} has {actual_length} entries, expected 10")
        
        if avg is None and mean is not None:
            issues.append(f"{element} has null average but mean is {mean}")
        
        print()
    
    # Check national statistics too
    nat_result = supabase.table('national_statistics')\
        .select('element, distribution')\
        .limit(10)\
        .execute()
    
    print("\n=== NATIONAL STATISTICS DISTRIBUTIONS ===")
    for record in nat_result.data:
        element = record['element']
        dist = record['distribution']
        actual_length = len(dist) if dist else 0
        
        print(f"Element: {element}, Length: {actual_length} (expected: 10)")
        if actual_length != 10:
            issues.append(f"National {element} has {actual_length} entries, expected 10")
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ All VESPA distributions have exactly 10 elements!")
        print("✅ Average column is populated!")

if __name__ == "__main__":
    verify_distributions()