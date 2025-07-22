# Knack VESPA Data Flow Explanation

## Data Flow: Object_10 → Object_29

### Step 1: Reading from Object_10

The script reads these fields from Object_10:

```
Student Email: field_email (configured in knack_config.py)

VESPA Scores (configured in knack_config.py):
- Cycle 1: V1, E1, S1, P1, A1, O1 (Overall)
- Cycle 2: V2, E2, S2, P2, A2, O2 (Overall)
- Cycle 3: V3, E3, S3, P3, A3, O3 (Overall)

Connected Fields (from Object_10):
- field_133: VESPA Customer (array of IDs)
- field_439: Staff Admin (array of IDs)
- field_145: Tutors (array of IDs)
```

**Note**: The Overall scores (O1, O2, O3) are read but NOT used for generation. They're just for verification.

### Step 2: Score Generation

For each cycle with VESPA scores, the calculator generates:
- VISION: 5 statement scores (1-5 scale)
- EFFORT: 4 statement scores
- SYSTEMS: 5 statement scores
- PRACTICE: 6 statement scores
- ATTITUDE: 9 statement scores

Total: 29 statement scores per cycle

### Step 3: Field Mapping to Object_29

The script uses `psychometric_question_output_object_120.json` to map each generated score to the correct field:

```json
{
  "questionId": "q1",
  "questionText": "I've worked out the next steps...",
  "vespaCategory": "VISION",
  "fieldIdCycle1": "field_3309",
  "fieldIdCycle2": "field_3310",
  "fieldIdCycle3": "field_3311"
}
```

### Step 4: Creating Object_29 Record

The final Object_29 record contains:

1. **Email**: field_2732 = student email
2. **Connected Fields** (copied from Object_10 as arrays):
   - field_1821 = VESPA Customer IDs (from field_133 in Object_10)
   - field_2069 = Staff Admin IDs (from field_439 in Object_10)
   - field_2070 = Tutors IDs (from field_145 in Object_10)
3. **Statement Scores** (generated):
   - For Cycle 1: field_3309, field_3312, field_3315... (29 fields)
   - For Cycle 2: field_3310, field_3313, field_3316... (29 fields)
   - For Cycle 3: field_3311, field_3314, field_3317... (29 fields)

### Example Data Flow

```
Object_10 Record:
- Email: john.doe@school.edu
- V1: 7, E1: 8, S1: 6, P1: 7, A1: 9, O1: 7.4
- field_133: [12345, 67890] (VESPA Customer IDs)
- field_439: [11111] (Staff Admin ID)
- field_145: [22222, 33333, 44444] (Tutor IDs)

↓ Process ↓

Object_29 Record Created:
- field_2732: "john.doe@school.edu"
- field_1821: [12345, 67890] (VESPA Customer connections)
- field_2069: [11111] (Staff Admin connection)
- field_2070: [22222, 33333, 44444] (Tutors connections)
- field_3309: "4" (q1 Vision statement, Cycle 1)
- field_3312: "3" (q2 Systems statement, Cycle 1)
- field_3315: "4" (q3 Vision statement, Cycle 1)
- ... (26 more Cycle 1 fields)
```

### Important Notes

1. **Existing Records**: If Object_29 already has data for a cycle, that cycle is skipped
2. **Complete Cycles Only**: A cycle must have all 5 VESPA scores (V,E,S,P,A) to be processed
3. **Score Verification**: Generated scores are verified to produce the correct VESPA scores
4. **String Values**: All scores are converted to strings for Knack compatibility 