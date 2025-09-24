# National Averages Investigation Report

## 🔍 Current State Analysis

### 1. Data Flow Discovery

#### Object_120 in Knack
- **Purpose**: Stores calculated national averages from `calculate_national_averages.py`
- **Updates**: Should run regularly via Heroku scheduler
- **Last Update**: August 1st, 2025 (for 2025/2026 academic year)
- **Content**: Contains averages for each VESPA component by cycle

#### Key Fields in Object_120
```javascript
// From FieldMappings in frontend
nationalBenchmarks: {
    cycle1: {
        v: 'field_3309',  // Vision average
        e: 'field_3310',  // Effort average
        s: 'field_3311',  // Systems average
        p: 'field_3312',  // Practice average
        a: 'field_3313',  // Attitude average
        o: 'field_3314'   // Overall average
    },
    cycle2: {
        v: 'field_3315',
        e: 'field_3316',
        s: 'field_3317',
        p: 'field_3318',
        a: 'field_3319',
        o: 'field_3320'
    },
    cycle3: {
        v: 'field_3321',
        e: 'field_3322',
        s: 'field_3323',
        p: 'field_3324',
        a: 'field_3325',
        o: 'field_3326'
    }
}
```

### 2. Data Synchronization Issues

#### Problem 1: Object_120 NOT Synced to Supabase
- The `sync_knack_to_supabase.py` script does NOT sync Object_120
- Instead, it calculates its own national statistics in `calculate_national_statistics()`
- This creates a **disconnect** between Knack Object_120 and Supabase `national_statistics`

#### Problem 2: Multiple Data Sources
The system currently has **THREE different sources** for national averages:

1. **Object_120 in Knack** (updated by `calculate_national_averages.py`)
2. **Supabase `national_statistics` table** (calculated by sync script)
3. **Direct API calls to Object_120** (used by some endpoints)

#### Problem 3: No Academic Year Filtering
- Object_120 fetches always get the **latest record** regardless of academic year
- The query uses `sort_field='field_3307'` (DateTime) but no year filter
- This means **all years show the same national data**

### 3. Current Implementation Paths

#### Path A: Dashboard Initial Load
```
Dashboard → /api/dashboard-initial-data → make_knack_request('object_120')
                                         ↓
                                   Latest record only (no year filter)
```

#### Path B: Supabase Statistics
```
Dashboard → /api/statistics → Supabase national_statistics table
                             ↓
                       Has academic_year field but may not match Object_120
```

#### Path C: Direct Object_120 Fetch
```
Dashboard → /api/knack-data?objectKey=object_120 → Latest record only
```

---

## ⚠️ Issues Identified

### 1. Scheduler May Have Stopped
- Last calculation: August 1st, 2025
- Expected: Should run regularly (daily/weekly)
- **Action Required**: Check Heroku scheduler

### 2. Academic Year Not Considered
- Object_120 stores a single set of averages
- No filtering by academic year when fetching
- All years see the same national data

### 3. Data Consistency
- Supabase calculates its own averages
- May not match Object_120 values
- Creates confusion about source of truth

### 4. Missing Historical Data
- Only latest Object_120 record is used
- No way to get 2024/2025 national averages
- Historical comparisons impossible

---

## 🛠️ Solutions

### Immediate Fix: Check Heroku Scheduler

```bash
# Check if scheduler is running
heroku logs --app vespa-dashboard-9a1f84ee5341 --tail | grep "calculate_national"

# Check scheduler configuration
heroku addons:open scheduler --app vespa-dashboard-9a1f84ee5341

# Manual run to test
heroku run python calculate_national_averages.py --app vespa-dashboard-9a1f84ee5341
```

### Short-term Fix: Sync Object_120 to Supabase

Create a sync function for Object_120:

```python
def sync_national_benchmarks_from_knack():
    """Sync Object_120 national benchmarks to Supabase"""
    
    # Get all Object_120 records (not just latest)
    knack_data = make_knack_request(
        'object_120',
        filters=[],
        rows_per_page=100,
        sort_field='field_3307',
        sort_order='desc'
    )
    
    for record in knack_data.get('records', []):
        # Extract academic year from record
        academic_year = record.get('field_3497_raw')  # Academic year field
        
        if not academic_year:
            # Try to parse from name field
            name = record.get('field_3306_raw', '')
            if '2024' in name:
                academic_year = '2024/2025'
            elif '2025' in name:
                academic_year = '2025/2026'
            else:
                continue
        
        # Map cycles and components
        for cycle in [1, 2, 3]:
            cycle_fields = {
                1: {'v': 'field_3309', 'e': 'field_3310', 's': 'field_3311', 
                    'p': 'field_3312', 'a': 'field_3313', 'o': 'field_3314'},
                2: {'v': 'field_3315', 'e': 'field_3316', 's': 'field_3317',
                    'p': 'field_3318', 'a': 'field_3319', 'o': 'field_3320'},
                3: {'v': 'field_3321', 'e': 'field_3322', 's': 'field_3323',
                    'p': 'field_3324', 'a': 'field_3325', 'o': 'field_3326'}
            }
            
            if cycle not in cycle_fields:
                continue
                
            fields = cycle_fields[cycle]
            
            # Insert each component
            for component, field_id in fields.items():
                if component == 'o':
                    continue  # Skip overall for now
                    
                element_name = {
                    'v': 'vision',
                    'e': 'effort', 
                    's': 'systems',
                    'p': 'practice',
                    'a': 'attitude'
                }.get(component)
                
                value = record.get(f'{field_id}_raw')
                if value:
                    # Upsert to national_statistics
                    supabase.table('national_statistics').upsert({
                        'academic_year': academic_year,
                        'cycle': cycle,
                        'element': element_name,
                        'mean': float(value),
                        'source': 'object_120',
                        'last_updated': record.get('field_3307_raw')
                    }).execute()
```

### Long-term Fix: Modify Object_120 Structure

1. **Store Academic Year in Object_120**
   - Add academic_year field to Object_120 records
   - Create separate records for each academic year
   - Filter by academic year when fetching

2. **Update calculate_national_averages.py**
   ```python
   # In main() function
   payload_for_target_object = {
       TARGET_FIELDS_STRUCTURE["name_base"]: dynamic_target_record_name,
       TARGET_FIELDS_STRUCTURE["academic_year"]: academic_year_str,
       "field_3497": academic_year_str  # Store academic year explicitly
   }
   ```

3. **Update API to Filter by Academic Year**
   ```python
   @app.route('/api/dashboard-initial-data', methods=['POST'])
   def get_dashboard_initial_data():
       # ...
       academic_year = data.get('academicYear', get_current_academic_year())
       
       # Fetch Object_120 with academic year filter
       national_data = make_knack_request(
           'object_120',
           filters=[{
               'field': 'field_3497',  # Academic year field
               'operator': 'is',
               'value': academic_year
           }],
           rows_per_page=1,
           sort_field='field_3307',
           sort_order='desc'
       )
   ```

---

## 📊 Current Data Status

### What's Working
- Object_120 has data for 2024/2025 (from your calculation script)
- Supabase has some national statistics (self-calculated)
- API endpoints can fetch Object_120 data

### What's Broken
- No academic year filtering = all years see same data
- Scheduler may have stopped (last run August 1st)
- Data inconsistency between Object_120 and Supabase

### Missing Pieces
- Historical Object_120 records for different academic years
- Proper sync between Object_120 and Supabase
- Academic year awareness in national benchmark queries

---

## 🚀 Action Plan

### 1. Immediate (Today)
- [ ] Check Heroku scheduler status
- [ ] Run manual calculation if needed
- [ ] Verify Object_120 has current data

### 2. This Week
- [ ] Add Object_120 sync to sync_knack_to_supabase.py
- [ ] Update API to filter Object_120 by academic year
- [ ] Create historical records in Object_120 if missing

### 3. Next Week
- [ ] Modify calculate_national_averages.py to store academic year
- [ ] Update dashboard to request year-specific national data
- [ ] Test with multiple academic years

---

## 🔑 Key Findings

1. **Object_120 is the source of truth** for national averages
2. **It's NOT being synced** to Supabase properly
3. **No academic year filtering** causes all years to see same data
4. **Scheduler may have stopped** (needs investigation)
5. **Multiple data paths** create confusion and inconsistency

The solution requires:
- Fixing the scheduler
- Syncing Object_120 to Supabase with academic year
- Updating API to filter by academic year
- Ensuring historical data is preserved
