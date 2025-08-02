# Sync Testing Handover Document

## Current Date: 2025-08-01

## Project Context
The user is setting up a scheduled process to sync data from Knack to Supabase for faster dashboard creation. After confusion with multiple AI-created files and lost fixes, they want to work ONLY with `sync_knack_to_supabase.py` and test each component systematically before scheduling the sync.

## Key Problem
The `question_responses` table was only getting 17K records instead of expected ~750K. The fix involved batch processing limits but was lost during file confusion.

## Testing Approach
USER'S EXPLICIT REQUIREMENT: Test each sync component systematically one at a time using modular testing.

## Progress So Far

### 1. ✅ Establishments Sync - COMPLETED
- **Test Status**: Successfully tested and verified
- **Results**: 160 active establishments synced correctly
- **Key Features Implemented**:
  - Filters out cancelled establishments (`field_2209 != 'Cancelled'`)
  - Marks missing establishments as cancelled in subsequent syncs
  - Added `status` column to track Active/Cancelled
- **User Confirmation**: "160 establishments that are not cancelled" is correct

### 2. 🔄 Students & VESPA Sync - IN PROGRESS
- **Initial Limited Test (3 pages)**: 
  - 2,972 students created
  - 0 VESPA scores (expected - limited test didn't include full logic)
  
- **Full Test Results**:
  - Students: 20,965 ✅ (looks correct per user)
  - VESPA scores: 8,865 ❌ (way too low - expected ~24,175)
  - Active students showing as 1,000 (Supabase query limit issue)

- **Critical Bug Found & Fixed**:
  - Race condition where VESPA scores were being skipped because student records weren't yet in database
  - Fix: Process pending student batches BEFORE processing VESPA batches
  - Added logging for skipped VESPA scores

- **Data Issue Found & Fixed**:
  - Record with `overall` score of 11,485 violating constraint
  - User identified as "database error at start of year" 
  - User manually corrected in Knack and confirmed no other such records

- **Current File State**:
  - User accidentally reverted the file to an older version
  - Assistant restored the file with all improvements:
    - Batch processing (100 students, 200 VESPA scores)
    - Status tracking (Active/Inactive)
    - Staff test account filtering (no establishment = skip)
    - Enhanced logging
    - Score validation

### 3. ⏳ Question Responses - NOT YET TESTED
- Expected: ~750K records
- Previous issue: Only 17K records
- Known fix: Related to batch processing limits

### 4. ⏳ Staff Admins - NOT YET TESTED

### 5. ⏳ Super Users - NOT YET TESTED

### 6. ⏳ Statistics Calculation - NOT YET TESTED
- Previous attempt failed in `sync_knack_to_supabase_production_fixed.py`

## Expected Record Counts (User's Calculations)

### Students (Object_10)
- 14,236 total with questionnaire after Aug 1, 2024
- Filter out staff test accounts (no establishment connection)

### VESPA Scores
- Cycle 1: 12,785 students × 6 scores = 76,710
- Cycle 2: 7,730 students × 6 scores = 46,380  
- Cycle 3: 3,660 students × 6 scores = 21,960
- **Total Expected**: 145K-180K VESPA records

### Question Responses (Object_29)
- 25,261 records with Object_10 connections
- Cycle 1: 13,331 × 31 questions = 413,261
- Cycle 2: 7,108 × 31 questions = 220,348
- Cycle 3: 3,146 × 31 questions = 97,526
- **Total Expected**: ~750K records

## Key Technical Details

### Batch Processing Sizes
```python
BATCH_SIZES = {
    'establishments': 50,
    'students': 100,
    'vespa_scores': 200,
    'question_responses': 500
}
```

### Critical Race Condition Fix
```python
# Process any pending students BEFORE VESPA batch
if student_batch:
    logging.info(f"Processing {len(student_batch)} students before VESPA batch...")
    # ... process students and update mappings
```

### Score Validation
```python
def clean_score(value, max_value=10):
    # Individual scores: max 10
    # Overall score: max 30 (sum of 5 scores)
```

## Files Created During Testing
- `test_sync_tables.py` - Modular testing script (deleted by user)
- Various SQL helper scripts (deleted by user)
- Debug scripts (deleted by user)

## Current Working File
`sync_knack_to_supabase.py` - ONLY work on this file

## Next Steps for New Context
1. **Re-test Students & VESPA Sync** with the restored file containing all fixes
2. **Test Question Responses** sync (this is the critical 750K records issue)
3. **Test Staff Admins** sync
4. **Test Super Users** sync  
5. **Test Statistics** calculation
6. Once all components verified, user will:
   - Set up scheduled execution
   - Connect the frontend

## Important Notes
- User wants systematic testing of EACH component before moving to the next
- Do NOT create multiple files - work only on `sync_knack_to_supabase.py`
- User prefers clear test results showing expected vs actual counts
- After completion, offer to commit and push to GitHub (user preference)

## Current Database State
- All tables have been cleared for fresh testing
- `vespa_scores_overall_check` constraint exists (max value 30)
- Bad data record (11,485) has been fixed in Knack

## Key Environment Variables Required
- KNACK_APP_ID
- KNACK_API_KEY  
- SUPABASE_URL
- SUPABASE_KEY