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
    """Verify distribution arrays are properly formatted"""
    
    # Get a sample of school statistics
    result = supabase.table('school_statistics')\
        .select('element, distribution, average, mean')\
        .limit(20)\
        .execute()
    
    print("=== DISTRIBUTION VERIFICATION ===\n")
    
    issues = []
    for record in result.data:
        element = record['element']
        dist = record['distribution']
        avg = record['average']
        mean = record['mean']
        
        expected_length = 11 if element == 'overall' else 7
        actual_length = len(dist) if dist else 0
        
        print(f"Element: {element}")
        print(f"  Distribution length: {actual_length} (expected: {expected_length})")
        print(f"  Distribution: {dist}")
        print(f"  Average: {avg}, Mean: {mean}")
        
        if actual_length != expected_length:
            issues.append(f"{element} has {actual_length} entries, expected {expected_length}")
        
        if avg is None and mean is not None:
            issues.append(f"{element} has null average but mean is {mean}")
        
        print()
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ All distributions have correct lengths!")
        print("✓ Average column is populated!")

if __name__ == "__main__":
    verify_distributions()