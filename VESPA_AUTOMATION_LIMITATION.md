# VESPA Automation Limitation - Critical Information

## The Problem

The VESPA automation has a fundamental design limitation that affects how cycle data is displayed in the dashboard:

### How the Automation Actually Works:
1. **Stores data in cycle-specific fields**:
   - Cycle 1: field_1953
   - Cycle 2: field_1955 (NOT field_1954 as some docs suggested)
   - Cycle 3: field_1956
2. **ALSO uses current cycle fields** (field_794 through field_821)
3. **Uses field_863** to indicate which cycle's data is CURRENTLY active
4. **DOES preserve historical cycle data** in the cycle-specific fields

### What This Means:
- Each cycle's data is preserved in its own field
- The automation populates BOTH cycle-specific fields AND current cycle fields
- You CAN filter by specific cycles using the cycle-specific fields

## Impact on the Dashboard

### Question Level Analysis (QLA):
- The "n" number shows ALL students with psychometric data, regardless of which cycle is stored
- You cannot filter to see "only Cycle 1 responses" because that historical data doesn't exist
- The data shown is whatever cycle is currently stored for each student (could be a mix of Cycle 1, 2, and 3)

### Data Health Check:
- Will show discrepancies because:
  - Object_10 preserves all cycle data (Cycle 1, 2, 3 VESPA scores)
  - Object_29 only has the current cycle's questionnaire data
  - Students who completed multiple cycles will appear as "missing" for earlier cycles

### Example with Towers School:
- 10 students completed Cycle 1 (but their data was overwritten when they did Cycle 2)
- 33 students completed Cycle 2 (but most were overwritten when they did Cycle 3)  
- 39 students completed Cycle 3 (only 2 currently have Cycle 3 as their active cycle)
- Result: QLA shows mixed data from whatever cycle each student currently has stored

## Recommendations

### Short-term Workarounds:
1. **Accept mixed-cycle data** in QLA - it shows the most recent responses for each student
2. **Ignore cycle filters** for psychometric data - they don't work as expected
3. **Focus on Object_10 data** for cycle-specific analysis (VESPA scores are preserved)

### Long-term Solutions:
1. **Modify the automation** to use cycle-specific fields (field_1953, field_1955, field_1956) instead of overwriting
2. **Create separate Object_29 records** for each cycle instead of updating the same record
3. **Add a data migration** to recover historical data if it still exists elsewhere

## Technical Details

The confusion arose because:
- The JSON mapping files (`psychometric_question_details.json`) define cycle-specific fields
- But the automation uses `currentCycleFieldId` fields instead
- The dashboard was expecting historical data that doesn't exist

This is a fundamental limitation of the current automation design, not a bug in the dashboard. 