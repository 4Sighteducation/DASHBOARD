import os
from dotenv import load_dotenv
from supabase import create_client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

def debug_national_statistics():
    """Debug why national statistics aren't being created"""
    
    # Check if we have any school statistics
    school_stats = supabase.table('school_statistics')\
        .select('*')\
        .eq('cycle', 1)\
        .eq('element', 'vision')\
        .eq('academic_year', '2024/2025')\
        .limit(5)\
        .execute()
    
    print(f"\nFound {len(school_stats.data)} school statistics for vision cycle 1")
    if school_stats.data:
        print(f"Sample record: {school_stats.data[0]}")
        print(f"Distribution: {school_stats.data[0].get('distribution')}")
    
    # Try to manually create a national statistic
    print("\nAttempting to manually insert a national statistic...")
    
    # Aggregate distributions from school stats
    all_school_stats = supabase.table('school_statistics')\
        .select('mean, count, distribution')\
        .eq('cycle', 1)\
        .eq('element', 'vision')\
        .eq('academic_year', '2024/2025')\
        .execute()
    
    print(f"Total schools with data: {len(all_school_stats.data)}")
    
    # Calculate weighted average
    total_weighted_sum = 0
    total_count = 0
    national_distribution = [0, 0, 0, 0, 0, 0, 0]  # For vision (0-6)
    
    for school in all_school_stats.data:
        if school.get('count', 0) > 0:
            total_weighted_sum += school.get('mean', 0) * school.get('count', 0)
            total_count += school.get('count', 0)
            
            # Aggregate distribution
            if school.get('distribution'):
                school_dist = school['distribution']
                if isinstance(school_dist, list):
                    for i in range(min(len(school_dist), len(national_distribution))):
                        national_distribution[i] += school_dist[i]
    
    if total_count > 0:
        national_mean = total_weighted_sum / total_count
    else:
        national_mean = 0
    
    print(f"\nCalculated national mean: {national_mean:.2f}")
    print(f"Total student count: {total_count}")
    print(f"National distribution: {national_distribution}")
    
    # Try to insert
    national_data = {
        'cycle': 1,
        'academic_year': '2024/2025',
        'element': 'vision',
        'mean': round(national_mean, 2),
        'count': total_count,
        'distribution': national_distribution
    }
    
    try:
        result = supabase.table('national_statistics').insert(national_data).execute()
        print(f"\nInsert successful! Created record: {result.data}")
    except Exception as e:
        print(f"\nInsert failed with error: {str(e)}")
        print(f"Data we tried to insert: {national_data}")

if __name__ == "__main__":
    debug_national_statistics()