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

email = 'allenc54@hwbcymru.net'

print("="*80)
print(f"CHECKING KNACK OBJECT_10 FOR: {email}")
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
        print(f"\nCYCLE 1 SCORES (Historical fields 155-160):")
        print(f"  Vision: {record.get('field_155_raw')}")
        print(f"  Effort: {record.get('field_156_raw')}")
        print(f"  Systems: {record.get('field_157_raw')}")
        print(f"  Practice: {record.get('field_158_raw')}")
        print(f"  Attitude: {record.get('field_159_raw')}")
        print(f"  Overall: {record.get('field_160_raw')}")
        print(f"\nCYCLE 2 SCORES (Historical fields 161-166):")
        print(f"  Vision: {record.get('field_161_raw')}")
        print(f"  Effort: {record.get('field_162_raw')}")
        print(f"  Overall: {record.get('field_166_raw')}")
        print(f"\nCYCLE 3 SCORES (Historical fields 167-172):")
        print(f"  Vision: {record.get('field_167_raw')}")
        print(f"  Effort: {record.get('field_168_raw')}")
        print(f"  Overall: {record.get('field_172_raw')}")
        print(f"\nCURRENT SCORES (fields 147-152):")
        print(f"  Vision: {record.get('field_147_raw')}")
        print(f"  Effort: {record.get('field_148_raw')}")
        print(f"  Systems: {record.get('field_149_raw')}")
        print(f"  Overall: {record.get('field_152_raw')}")
    else:
        print("NO RECORDS FOUND")
else:
    print(f"ERROR: {response.status_code} - {response.text}")

print(f"\n{'='*80}")
