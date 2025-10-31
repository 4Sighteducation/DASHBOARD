import csv

with open('shireland25_all_questions.csv', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)
    
print(f"Total rows: {len(rows)}")
print(f"\nHeader ({len(rows[0])} columns):")
print(rows[0])

if len(rows) > 1:
    print(f"\nFirst student:")
    print(f"  Email: {rows[1][0]}")
    print(f"  Name: {rows[1][1]}")
    print(f"  V1-V5: {rows[1][3:8]}")
    print(f"  E1-E4: {rows[1][8:12]}")
    print(f"  VESPA: {rows[1][-5:]}")
else:
    print("\n[ERROR] No data rows!")
























