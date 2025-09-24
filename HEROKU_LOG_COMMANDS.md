# Heroku Log Investigation Commands

## Quick Commands to Check the Logs

### 1. Check Today's Scheduler Run (Real-time)
```bash
# See live logs as they happen
heroku logs --app vespa-dashboard-9a1f84ee5341 --tail
```

### 2. Check Last Night's National Averages Calculation (September 24, 00:00 UTC)
```bash
# Get logs from the specific scheduler dyno
heroku logs --app vespa-dashboard-9a1f84ee5341 --dyno scheduler --num 1500 | grep -A 20 "calculate_national_averages"
```

### 3. Check for Errors in the Script
```bash
# Look for any errors in the national averages calculation
heroku logs --app vespa-dashboard-9a1f84ee5341 --num 2000 | grep -E "(ERROR|CRITICAL|Exception|Traceback)" | grep -B 5 -A 5 "national"
```

### 4. Check if Script is Completing Successfully
```bash
# Look for success messages
heroku logs --app vespa-dashboard-9a1f84ee5341 --num 2000 | grep -E "(completed successfully|National average calculation task completed|Created/Updated record)"
```

### 5. Check for Knack API Issues
```bash
# Check for API rate limits or authentication failures
heroku logs --app vespa-dashboard-9a1f84ee5341 --num 2000 | grep -E "(401|403|429|rate limit|API key|authentication)"
```

### 6. See Full Output from Last Run
```bash
# Get all logs from around midnight UTC (adjust date as needed)
heroku logs --app vespa-dashboard-9a1f84ee5341 --num 3000 | grep "2025-09-24T00:0"
```

### 7. Check What Academic Year is Being Calculated
```bash
# See what dates/years the script is processing
heroku logs --app vespa-dashboard-9a1f84ee5341 --num 1000 | grep -E "(Academic Year|2024|2025|filter_start_date|filter_end_date)"
```

## Common Issues to Look For

### Issue 1: Wrong Academic Year
The script might be calculating for the wrong academic year. Look for lines like:
```
Academic Year: 2025/2026
Processing records from [date] to [date]
```

### Issue 2: No Data to Process
The script might not find any records to process:
```
Processing 0 records...
No VESPA scores found for the period
```

### Issue 3: Object_120 Update Failing
The update to Object_120 might be failing:
```
Failed to update object_120
Error creating/updating record
```

### Issue 4: Date Range Issues  
The script uses date ranges to filter data. Check if it's using the correct dates:
```
filter_start_date: 2025-08-01
filter_end_date: 2026-07-31
```

## Understanding the Script's Behavior

The `calculate_national_averages.py` script:

1. **Runs daily at midnight UTC**
2. **Calculates averages for the CURRENT academic year**
3. **Creates/Updates a record in Object_120**

### Key Things to Check:

1. **Record Name Pattern**: Look for what it's naming the record
   ```bash
   heroku logs --app vespa-dashboard-9a1f84ee5341 --num 500 | grep "dynamic_target_record_name"
   ```

2. **Is it Finding Existing Records?**: Check if it's updating or creating
   ```bash
   heroku logs --app vespa-dashboard-9a1f84ee5341 --num 500 | grep -E "(Finding existing record|Creating new record|Updating record)"
   ```

3. **Data Volume**: How many records is it processing?
   ```bash
   heroku logs --app vespa-dashboard-9a1f84ee5341 --num 500 | grep -E "(Processing \d+ records|Total students|Valid records)"
   ```

## Manual Trigger (If Needed)

If you need to run the script manually to test:
```bash
# Run the script manually
heroku run python calculate_national_averages.py --app vespa-dashboard-9a1f84ee5341

# Or run with specific date range (edit the script first)
heroku run bash --app vespa-dashboard-9a1f84ee5341
# Then in the bash shell:
python calculate_national_averages.py
```

## What to Look for in Object_120

After the script runs, check in Knack Object_120 for:
1. **Record Name**: Should contain current academic year (e.g., "National Averages 2025-26")
2. **Last Updated**: field_3307 should show today's date
3. **Academic Year**: field_3497 (if it exists)
4. **VESPA Averages**: fields 3309-3326 should have values

## Possible Reasons for No Updates

1. **Script is calculating the same academic year** and updating the existing record (not creating new ones)
2. **Date filtering is excluding recent data** (e.g., looking for future dates)
3. **No new VESPA data** to process since last run
4. **API rate limits** preventing the update to Object_120
5. **Script is failing silently** without proper error logging

## Next Steps

1. Run command #2 above to see last night's run
2. Look for any ERROR messages
3. Check what academic year it's processing
4. Verify if it's finding records to process
5. Check if the update to Object_120 succeeds

The most likely issue is that it's updating the SAME Object_120 record each time (for 2025/2026) rather than creating historical records for different academic years.
