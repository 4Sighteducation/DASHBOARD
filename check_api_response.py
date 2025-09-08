#!/usr/bin/env python3
"""
Check what the API is actually returning for insights
"""
import requests
import json

establishment_id = '60eb1efc-3982-46b6-bc5f-65e8373506a5'

# Test the API endpoint
api_url = "https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/qla"
params = {
    'establishment_id': establishment_id,
    'academic_year': '2025-26',
    'cycle': 1
}

print("=" * 80)
print("TESTING API RESPONSE")
print("=" * 80)
print(f"\nCalling: {api_url}")
print(f"Params: {params}")
print("-" * 40)

try:
    response = requests.get(api_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        # Check insights
        if 'insights' in data:
            print(f"\n✅ API returned {len(data['insights'])} insights:")
            print()
            
            for insight in data['insights']:
                print(f"Insight: {insight.get('title', 'Unknown')}")
                print(f"  ID: {insight.get('id')}")
                print(f"  Question IDs: {insight.get('questionIds', [])}")
                print(f"  Percentage: {insight.get('percentageAgreement', 0)}%")
                print(f"  Total Responses: {insight.get('totalResponses', 0)}")
                print()
        else:
            print("❌ No insights in API response")
            
        # Save full response for analysis
        with open('api_response_debug.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("Full response saved to api_response_debug.json")
            
    else:
        print(f"❌ API error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Request failed: {e}")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)
print("\nThe issue is likely one of:")
print("1. API is returning lowercase question IDs but frontend expects uppercase")
print("2. API is not calculating percentages correctly")
print("3. No statistics data exists for the insight questions")
