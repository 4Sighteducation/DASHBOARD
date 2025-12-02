import os
import requests
from dotenv import load_dotenv

load_dotenv()

KNACK_APP_ID = os.getenv('KNACK_APP_ID')
KNACK_API_KEY = os.getenv('KNACK_API_KEY')

headers = {
    'X-Knack-Application-Id': KNACK_APP_ID,
    'X-Knack-REST-API-Key': KNACK_API_KEY
}

email = 'rchassels13@bedales.org.uk'

print("="*80)
print(f"CHECKING KNACK OBJECT_10 FOR: Ruairidh Chassels")
print(f"Email: {email}")
print("="*80)

response = requests.get(
    "https://api.knack.com/v1/objects/object_10/records",
    headers=headers,
    params={'filters': '{"match":"and","rules":[{"field":"field_197","operator":"is","value":"' + email + '"}]}'}
)

if response.ok:
    records = response.json().get('records', [])
    if records:
        record = records[0]
        print(f"\nOBJECT_10 RECORD FOUND:")
        print(f"  ID: {record.get('id')}")
        print(f"  Current Cycle (field_146): {record.get('field_146')} (raw: {record.get('field_146_raw')})")
        
        print(f"\n{'='*60}")
        print("CYCLE 1 DATA:")
        print(f"{'='*60}")
        print(f"  SCORES (Historical 155-160):")
        print(f"    Vision: {record.get('field_155_raw')}")
        print(f"    Effort: {record.get('field_156_raw')}")
        print(f"    Systems: {record.get('field_157_raw')}")
        print(f"    Practice: {record.get('field_158_raw')}")
        print(f"    Attitude: {record.get('field_159_raw')}")
        print(f"    Overall: {record.get('field_160_raw')}")
        
        response_c1 = record.get('field_2302', '') or record.get('field_2302_raw', '')
        print(f"\n  RESPONSE (field_2302): {response_c1[:100]}..." if len(response_c1) > 100 else f"  RESPONSE: {response_c1}")
        
        goals_c1 = record.get('field_2499', '') or record.get('field_2499_raw', '')
        print(f"  GOALS (field_2499): {goals_c1[:100]}..." if len(goals_c1) > 100 else f"  GOALS: {goals_c1}")
        
        coaching_c1 = record.get('field_2488', '') or record.get('field_2488_raw', '')
        print(f"  COACHING (field_2488): {coaching_c1[:100]}..." if len(coaching_c1) > 100 else f"  COACHING: {coaching_c1}")
        
        print(f"\n{'='*60}")
        print("CURRENT SCORES (fields 147-152):")
        print(f"{'='*60}")
        print(f"  Vision: {record.get('field_147_raw')}")
        print(f"  Effort: {record.get('field_148_raw')}")
        print(f"  Systems: {record.get('field_149_raw')}")
        print(f"  Practice: {record.get('field_150_raw')}")
        print(f"  Attitude: {record.get('field_151_raw')}")
        print(f"  Overall: {record.get('field_152_raw')}")
        
        print(f"\n{'='*60}")
        print("COMPLETION INFO:")
        print(f"{'='*60}")
        completion = record.get('field_855', '') or record.get('field_855_raw', '')
        print(f"  Completion Date (field_855): {completion}")
        cycle_unlocked = record.get('field_1679', '')
        print(f"  Cycle Unlocked (field_1679): {cycle_unlocked}")
        
    else:
        print("NO RECORDS FOUND IN KNACK")
else:
    print(f"ERROR: {response.status_code} - {response.text}")

print(f"\n{'='*80}")
print("RECOMMENDATION:")
print(f"{'='*80}")
print("If responses/goals are in Knack but NOT in Supabase:")
print("  -> Dual-write to Knack is working ✅")
print("  -> Reading from Knack (our fix) will work ✅")
print("  -> Supabase sync issue but doesn't affect users")
print(f"{'='*80}")
