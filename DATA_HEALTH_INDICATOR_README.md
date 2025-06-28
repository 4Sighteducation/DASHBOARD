# Data Health Indicator - Implementation Status & Next Steps

## Overview
This document outlines the recent updates to the VESPA Dashboard backend for academic year filtering and the proposed Data Health Indicator feature.

## Problem Statement

### Data Integrity Issues
The VESPA Dashboard uses two primary data objects:
- **Object_10**: VESPA scores (student performance metrics)
- **Object_29**: Psychometric questionnaire responses

Key issues identified:
1. **Historical Data Contamination**: Both objects contained archived data from previous academic years, leading to incorrect totals and analysis
2. **Data Mismatches**: Discrepancies between Object_10 and Object_29:
   - Some students have VESPA scores but no questionnaire responses
   - Some students completed questionnaires but have no VESPA scores
3. **Cycle Filtering Issues**: Object_29 was using incorrect field for cycle filtering, showing wrong record counts per cycle

### Example Case - West Walsall Academy
- **Object_10**: 104 total student records (source of truth for enrollment)
- **Object_29**: 100 questionnaire responses (4 students didn't complete)
- **Cycle-specific issues**:
  - Cycle 1: Showing 30 records instead of correct 100
  - Cycle 2: Incorrect count (should be 75)
  - Cycle 3: Incorrect count (should be 25)

## Completed Updates

### 1. Academic Year Filtering Implementation

#### Created Helper Function
```python
def get_academic_year_filters(establishment_id=None, date_field='field_855', australian_field='field_3511')
```
- Automatically detects if school is Australian or UK-based
- UK schools: August 1 - July 31 academic year
- Australian schools: January 1 - December 31 calendar year
- Returns proper date range filters for Knack API

#### Applied to Object_10 (VESPA Results)
- Added to main dashboard data loading
- Added to paginated data loading
- Added to trust dashboard aggregation
- Added to comment analysis (word cloud, themes)
- Uses fields: `field_855` (completion date), `field_3511` (Australian indicator)

#### Applied to Object_29 (Psychometric Data)
- Fixed cycle-specific filtering:
  - Cycle 1: `field_1953` (is not blank)
  - Cycle 2: `field_1955` (is not blank)
  - Cycle 3: `field_1956` (is not blank)
- Added academic year filtering
- Uses fields: `field_856` (completion date), `field_3508` (Australian indicator)

### 2. Data Field Additions
- Added student ID field (`field_1819`) to Object_29 fetches for future reconciliation
- Added completion date fields to all relevant API calls

## Next Steps: Data Health Indicator

### Proposed Solution Design

#### Visual Indicator System
- **Location**: Dashboard header/overview section
- **Design**: Traffic light system (RAG - Red, Amber, Green)
  - 🟢 **Green**: All data synchronized, no issues
  - 🟡 **Amber**: Minor discrepancies (e.g., <5% of students affected)
  - 🔴 **Red**: Significant data issues requiring attention

#### User Interaction
- Clickable icon that opens a modal with detailed information
- Modal displays:
  - Total records in each object
  - List of mismatched students
  - Specific issues identified
  - Recommended actions

### Implementation Steps

#### 1. Create Data Reconciliation Endpoint
```python
@app.route('/api/data-health-check', methods=['POST'])
def check_data_health():
    """
    Compare Object_10 and Object_29 records to identify discrepancies
    """
    # Fetch all Object_10 student IDs for establishment/cycle
    # Fetch all Object_29 student IDs for establishment/cycle
    # Compare and categorize discrepancies
    # Calculate severity level (green/amber/red)
    # Return detailed report
```

#### 2. Implement Comparison Logic
- Fetch student IDs from both objects
- Identify:
  - Students in Object_10 but not Object_29 (missing questionnaires)
  - Students in Object_29 but not Object_10 (missing VESPA scores)
  - Any other data anomalies

#### 3. Frontend Integration
- Add health indicator component to dashboard
- Implement modal for detailed view
- Update automatically when filters change
- Cache results for performance

#### 4. Student-Level Details
Include in the response:
- Student names/IDs with issues
- Type of discrepancy for each student
- Timestamps of last data entry
- Suggested remediation steps

### Technical Considerations

1. **Performance**: 
   - Cache health check results (5-minute TTL)
   - Run checks asynchronously if needed
   - Limit detailed student lists to first 50 records

2. **Filtering Context**:
   - Health check respects all active filters
   - Updates when cycle changes
   - Works for establishment, trust, and staff admin views

3. **Data Fields Needed**:
   - Object_10: `field_187` (student name), student ID field
   - Object_29: `field_1819` (student connection), student name field

### Example Response Structure
```json
{
  "status": "amber",
  "summary": {
    "object10_count": 104,
    "object29_count": 100,
    "matched_count": 98,
    "discrepancy_rate": 5.8
  },
  "issues": {
    "missing_questionnaires": [
      {
        "student_id": "123",
        "student_name": "John Doe",
        "has_vespa_score": true,
        "last_score_date": "15/11/2024"
      }
    ],
    "missing_scores": [
      {
        "student_id": "456", 
        "student_name": "Jane Smith",
        "questionnaire_completed": "10/11/2024",
        "has_vespa_score": false
      }
    ]
  },
  "recommendations": [
    "4 students need to complete questionnaires",
    "2 students have questionnaire data but no VESPA scores recorded"
  ]
}
```

### Benefits
1. **Proactive Data Quality**: Administrators immediately see data issues
2. **Actionable Insights**: Specific student lists enable targeted follow-up
3. **Trust Building**: Transparency about data completeness
4. **Better Analysis**: Ensures QLA and other analytics use complete data

## Testing Checklist
- [ ] Verify Object_10 shows only current academic year data
- [ ] Verify Object_29 cycle filtering works correctly
- [ ] Test with UK school (August-July academic year)
- [ ] Test with Australian school (January-December)
- [ ] Verify trust mode aggregates correctly
- [ ] Check comment analysis uses current year only

## Notes for Implementation
- Consider adding a "Data Quality" section to the PDF reports
- May want to add email alerts for severe data issues
- Could extend to check for other data quality metrics (e.g., outliers, incomplete records)
- Consider historical tracking of data health over time

## Repository Status
The academic year filtering has been implemented and tested. The Data Health Indicator is ready for implementation as the next feature. 