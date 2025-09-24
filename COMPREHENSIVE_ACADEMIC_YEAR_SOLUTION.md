# Comprehensive Academic Year Solution
## A Complete Architectural Approach

---

## 📊 Current Situation Analysis

### Problems Identified
1. **Piecemeal fixes** causing confusion and potential conflicts
2. **Two different renewal workflows** not properly handled:
   - Workflow A: Delete & re-upload (same email, new Knack ID)
   - Workflow B: Clean existing data (same Knack ID, new completion date)
3. **National benchmark data** not showing for historical years (2024/2025)
4. **Missing historical data** for graduated students
5. **Frontend inconsistencies** with academic year filtering

---

## 🎯 Strategic Solution Overview

### Phase 1: Archive Foundation (Days 1-3)
**Wait for Knack data dumps of Object_10 and Object_29**
- This will be our source of truth for 2024/2025
- Will contain ALL students and their VESPA data from last year
- Includes graduated Year 13s who were deleted

### Phase 2: Data Architecture (Days 3-5)
**Build robust data model supporting both workflows**
- Master student records (by email)
- Academic year snapshots
- Completion-date-based year detection
- Knack ID change tracking

### Phase 3: National Data Fix (Day 4)
**Implement academic-year-specific national benchmarks**
- Store national averages by academic year
- Historical national data preservation
- Dynamic comparison based on selected year

### Phase 4: Frontend Integration (Days 5-6)
**Update all endpoints and queries**
- Consistent academic year filtering
- Historical data access
- Performance optimization

---

## 📁 Data Architecture Design

### Core Tables Structure

```sql
-- 1. Master Student Table (One record per email)
students_master (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE,
    current_name VARCHAR,
    current_establishment_id UUID,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

-- 2. Student Academic Year Snapshots
student_academic_years (
    id UUID PRIMARY KEY,
    student_master_id UUID REFERENCES students_master(id),
    academic_year VARCHAR(10),
    knack_id VARCHAR(50),  -- Can change between years
    knack_object_10_id VARCHAR(50),  -- Original Object_10 ID
    establishment_id UUID,
    year_group VARCHAR,
    course VARCHAR,
    faculty VARCHAR,
    group VARCHAR,
    snapshot_date DATE,  -- When this snapshot was taken
    is_archived BOOLEAN DEFAULT FALSE,  -- From Knack dump
    UNIQUE(student_master_id, academic_year)
)

-- 3. VESPA Scores (Enhanced)
vespa_scores_enhanced (
    -- Existing fields plus:
    completion_date DATE,  -- Actual completion date
    academic_year_calculated VARCHAR(10),  -- Based on completion date
    academic_year_original VARCHAR(10),  -- What was set at time of creation
    knack_object_29_id VARCHAR(50),  -- Original Object_29 ID
    is_archived BOOLEAN DEFAULT FALSE
)

-- 4. National Benchmarks by Year
national_benchmarks (
    id UUID PRIMARY KEY,
    academic_year VARCHAR(10),
    cycle INTEGER,
    vespa_component VARCHAR(20),  -- 'vision', 'effort', 'systems', etc.
    mean_score DECIMAL(3,2),
    median_score DECIMAL(3,2),
    sample_size INTEGER,
    last_calculated TIMESTAMP,
    UNIQUE(academic_year, cycle, vespa_component)
)
```

---

## 🔄 Workflow Handlers

### Workflow A: Delete & Re-upload
```python
def handle_delete_reupload(student_data):
    """
    Handles: Same email, different Knack ID
    """
    # 1. Find master record by email
    master = find_or_create_master(email=student_data['email'])
    
    # 2. Check if Knack ID changed
    last_snapshot = get_latest_snapshot(master.id)
    if last_snapshot and last_snapshot.knack_id != student_data['knack_id']:
        # New academic year detected via ID change
        create_new_academic_snapshot(master.id, student_data)
    else:
        # Update existing snapshot
        update_snapshot(last_snapshot, student_data)
```

### Workflow B: Data Cleaning (Same Record)
```python
def handle_data_cleaning(vespa_data):
    """
    Handles: Same Knack ID, new completion date
    """
    # 1. Calculate academic year from completion date
    calculated_year = calculate_academic_year(vespa_data['completion_date'])
    
    # 2. Update or create VESPA record with calculated year
    vespa_data['academic_year_calculated'] = calculated_year
    upsert_vespa_score(vespa_data)
```

### Academic Year Calculator
```python
def calculate_academic_year(date):
    """
    UK Academic Year: September 1st to August 31st
    """
    if date.month >= 9:  # September onwards
        return f"{date.year}/{date.year + 1}"
    else:  # January to August
        return f"{date.year - 1}/{date.year}"
```

---

## 📈 National Benchmarks Solution

### Problem
National data showing for 2025/2026 but not 2024/2025

### Solution
```sql
-- Create historical national benchmarks
INSERT INTO national_benchmarks (academic_year, cycle, vespa_component, mean_score, sample_size)
VALUES 
-- 2024/2025 National Data
('2024/2025', 1, 'vision', 6.5, 15000),
('2024/2025', 1, 'effort', 6.2, 15000),
('2024/2025', 1, 'systems', 5.7, 15000),
('2024/2025', 1, 'practice', 6.0, 15000),
('2024/2025', 1, 'attitude', 6.1, 15000),
-- 2025/2026 National Data (current)
('2025/2026', 1, 'vision', 6.6, 5000),
('2025/2026', 1, 'effort', 6.1, 5000),
('2025/2026', 1, 'systems', 5.5, 5000);

-- Function to get national data for specific year
CREATE OR REPLACE FUNCTION get_national_benchmarks(
    p_academic_year VARCHAR,
    p_cycle INTEGER
) RETURNS TABLE (
    component VARCHAR,
    mean_score DECIMAL,
    sample_size INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vespa_component,
        mean_score,
        sample_size
    FROM national_benchmarks
    WHERE academic_year = p_academic_year
    AND cycle = p_cycle;
END;
$$ LANGUAGE plpgsql;
```

### API Update for National Data
```python
@app.route('/api/national-benchmarks', methods=['GET'])
def get_national_benchmarks():
    academic_year = request.args.get('academic_year', get_current_academic_year())
    cycle = request.args.get('cycle', 1, type=int)
    
    # Get year-specific national data
    benchmarks = supabase_client.rpc('get_national_benchmarks', {
        'p_academic_year': academic_year,
        'p_cycle': cycle
    }).execute()
    
    if not benchmarks.data:
        # Fallback to most recent if historical not available
        benchmarks = get_most_recent_benchmarks(cycle)
    
    return jsonify(benchmarks.data)
```

---

## 📋 Implementation Steps

### Immediate Actions (Before Knack Dump)

#### 1. Create National Benchmarks Table
```sql
-- Run this NOW to fix national data issue
CREATE TABLE IF NOT EXISTS national_benchmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    academic_year VARCHAR(10) NOT NULL,
    cycle INTEGER NOT NULL,
    vespa_component VARCHAR(20) NOT NULL,
    mean_score DECIMAL(3,2),
    median_score DECIMAL(3,2),
    std_dev DECIMAL(3,2),
    sample_size INTEGER,
    schools_count INTEGER,
    last_calculated TIMESTAMP DEFAULT NOW(),
    UNIQUE(academic_year, cycle, vespa_component)
);

-- Insert historical data (you'll need to get these values)
INSERT INTO national_benchmarks (academic_year, cycle, vespa_component, mean_score, sample_size)
VALUES 
('2024/2025', 1, 'vision', 6.5, 15000),
('2024/2025', 1, 'effort', 6.2, 15000),
('2024/2025', 1, 'systems', 5.7, 15000),
('2024/2025', 1, 'practice', 6.0, 15000),
('2024/2025', 1, 'attitude', 6.1, 15000),
('2024/2025', 1, 'resilience', 6.2, 15000);
```

#### 2. Update API to Use Academic Year Benchmarks
```python
# In app.py - update the national comparison logic
def get_national_comparison(academic_year, cycle):
    """Get national benchmarks for specific academic year"""
    result = supabase_client.table('national_benchmarks')\
        .select('*')\
        .eq('academic_year', academic_year)\
        .eq('cycle', cycle)\
        .execute()
    
    return result.data if result.data else None
```

### After Knack Dump Arrives

#### 3. Import Historical Data
```python
# import_knack_dump.py
import pandas as pd
import json

def import_knack_historical_data(object_10_dump, object_29_dump):
    """
    Import historical data from Knack dumps
    """
    # Parse Object_10 (Students)
    students_df = pd.read_json(object_10_dump)
    
    for _, student in students_df.iterrows():
        # Create master record
        master_id = create_or_get_master(student['field_122'])  # email
        
        # Create 2024/2025 snapshot
        create_academic_snapshot({
            'student_master_id': master_id,
            'academic_year': '2024/2025',
            'knack_id': student['id'],
            'knack_object_10_id': student['id'],
            'year_group': student['field_809'],
            'is_archived': True
        })
    
    # Parse Object_29 (VESPA Scores)
    vespa_df = pd.read_json(object_29_dump)
    
    for _, score in vespa_df.iterrows():
        import_vespa_score({
            'knack_object_29_id': score['id'],
            'completion_date': score['field_created'],
            'academic_year_calculated': calculate_academic_year(score['field_created']),
            'is_archived': True
            # ... other fields
        })
```

#### 4. Create Unified Query Functions
```sql
-- Master function for dashboard queries
CREATE OR REPLACE FUNCTION get_dashboard_students(
    p_establishment_id UUID,
    p_academic_year VARCHAR
) RETURNS TABLE (
    student_id UUID,
    email VARCHAR,
    name VARCHAR,
    year_group VARCHAR,
    vespa_count INTEGER,
    is_archived BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sm.id,
        sm.email,
        sm.current_name,
        say.year_group,
        COUNT(vs.id)::INTEGER as vespa_count,
        say.is_archived
    FROM students_master sm
    INNER JOIN student_academic_years say ON sm.id = say.student_master_id
    LEFT JOIN vespa_scores_enhanced vs ON sm.id = vs.student_id 
        AND vs.academic_year_calculated = p_academic_year
    WHERE say.establishment_id = p_establishment_id
    AND say.academic_year = p_academic_year
    GROUP BY sm.id, sm.email, sm.current_name, say.year_group, say.is_archived;
END;
$$ LANGUAGE plpgsql;
```

---

## 🧪 Testing Plan

### Test Scenarios

#### 1. Delete & Re-upload Test
```sql
-- Student with same email, different Knack IDs across years
-- Should show in both 2024/2025 and 2025/2026
SELECT * FROM student_academic_years 
WHERE student_master_id = (
    SELECT id FROM students_master WHERE email = 'test@school.com'
);
```

#### 2. Same Record, New Completion Test  
```sql
-- VESPA scores with different completion dates
-- Should be assigned to correct academic year
SELECT 
    academic_year_calculated,
    COUNT(*) as scores
FROM vespa_scores_enhanced
WHERE student_id = 'xxx'
GROUP BY academic_year_calculated;
```

#### 3. National Data Test
```sql
-- Should return different values for each year
SELECT * FROM get_national_benchmarks('2024/2025', 1);
SELECT * FROM get_national_benchmarks('2025/2026', 1);
```

---

## 📊 Frontend Updates Required

### 1. Dashboard Component
```javascript
// Update to use academic year in all API calls
const fetchDashboardData = async (academicYear) => {
    const [students, national] = await Promise.all([
        fetch(`/api/dashboard-data?academic_year=${academicYear}`),
        fetch(`/api/national-benchmarks?academic_year=${academicYear}`)
    ]);
    // ...
};
```

### 2. National Comparison Display
```javascript
// Ensure national data updates with year selection
const NationalComparison = ({ academicYear, schoolScore }) => {
    const [nationalData, setNationalData] = useState(null);
    
    useEffect(() => {
        fetchNationalBenchmarks(academicYear)
            .then(setNationalData);
    }, [academicYear]);  // Re-fetch when year changes
    
    // ...
};
```

---

## 📅 Timeline

### Day 1-2 (Now)
- [ ] Create national_benchmarks table
- [ ] Fix API to use year-specific national data
- [ ] Document all current issues

### Day 3-4 (When Knack Dump Arrives)
- [ ] Import Object_10 dump → student_academic_years
- [ ] Import Object_29 dump → vespa_scores_enhanced  
- [ ] Verify historical data integrity

### Day 5
- [ ] Update sync process for both workflows
- [ ] Test with sample data
- [ ] Update all API endpoints

### Day 6
- [ ] Frontend integration
- [ ] Full system testing
- [ ] Documentation

---

## ✅ Success Criteria

1. **Historical Accuracy**: 2024/2025 shows ~440 students for Whitchurch
2. **Current Accuracy**: 2025/2026 shows 207 students for Whitchurch
3. **National Data**: Shows year-appropriate benchmarks
4. **Workflow Support**: Both delete/re-upload AND data cleaning work
5. **Performance**: Dashboard loads within 2 seconds
6. **Data Integrity**: No data loss during transitions

---

## 🚨 Critical Notes

### About Current Fixes
- Keep the API changes we made today (checking VESPA data)
- The enrollment history table can be adapted to this new structure
- Current fixes are compatible with this comprehensive solution

### About Knack Dumps
- Request dumps in JSON format if possible
- Include all fields, especially dates and IDs
- Keep original Knack IDs for reference

### About Academic Year Detection
Priority order for determining academic year:
1. Completion date (most accurate)
2. Creation date (fallback)
3. Manual assignment (last resort)

---

This comprehensive solution will permanently resolve all academic year issues and provide a robust foundation for years to come.
