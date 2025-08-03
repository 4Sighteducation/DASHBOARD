# Critical Knack Field Mappings to Verify

## Object Mappings
These are the Knack objects that map to Supabase tables:

| Knack Object | Description | Supabase Table |
|--------------|-------------|----------------|
| object_2 | Establishments | establishments |
| object_5 | Staff Admin Roles | staff_admins |
| object_6 | Students | students |
| object_10 | VESPA Results | vespa_scores |
| object_21 | Super User Roles | super_users |
| object_29 | Questionnaire Responses | question_responses |
| object_120 | National Benchmark Data | national_statistics |

## Critical Field Mappings

### Object_5 (Staff Admin Roles) - VERIFY THESE!
```
field_85 = Name (full name)
field_86 = Email
field_110 = Establishment connection (to object_2)
field_89 = User roles/profiles
```

### Object_2 (Establishments)
```
id = Knack record ID (maps to knack_id in Supabase)
field_xxx = Name (need to verify)
field_xxx = Trust connection (need to verify)
```

### Object_10 (VESPA Results) - These are the cycle scores
```
field_166 = Student Email
field_846 = Cycle (formatted as "Cycle 1", "Cycle 2", etc.)
field_171 = Vision score (Cycle 1)
field_172 = Effort score (Cycle 1)
field_173 = Systems score (Cycle 1)
field_174 = Practice score (Cycle 1)
field_175 = Attitude score (Cycle 1)

# Cycle 2 scores (need to verify exact field numbers)
field_xxx = Vision score (Cycle 2)
field_xxx = Effort score (Cycle 2)
field_xxx = Systems score (Cycle 2)
field_xxx = Practice score (Cycle 2)
field_xxx = Attitude score (Cycle 2)

# Cycle 3 scores (need to verify exact field numbers)
field_xxx = Vision score (Cycle 3)
field_xxx = Effort score (Cycle 3)
field_xxx = Systems score (Cycle 3)
field_xxx = Practice score (Cycle 3)
field_xxx = Attitude score (Cycle 3)
```

### Object_29 (Question Responses) - Individual question scores
```
field_xxx = Student connection
field_xxx = Cycle
field_1393 through field_1442 = Individual question responses (50 questions)
```

### Object_21 (Super Users)
```
field_473 = Email
field_xxx = Name (need to verify)
```

### Object_6 (Students)
```
field_xxx = Email
field_xxx = Name
field_xxx = Establishment connection
field_xxx = Year Group
field_xxx = Faculty
field_xxx = Course
```

## How to Verify These Mappings

1. **Use Knack's API Explorer**:
   ```bash
   curl -X GET https://api.knack.com/v1/objects/object_5/fields \
     -H "X-Knack-Application-Id: YOUR_APP_ID" \
     -H "X-Knack-REST-API-KEY: YOUR_API_KEY"
   ```

2. **Check a Sample Record**:
   ```bash
   curl -X GET https://api.knack.com/v1/objects/object_5/records?rows_per_page=1 \
     -H "X-Knack-Application-Id: YOUR_APP_ID" \
     -H "X-Knack-REST-API-KEY: YOUR_API_KEY"
   ```

3. **Look in Knack Builder**:
   - Go to your Knack app builder
   - Click on the object (e.g., Staff Admin Roles)
   - View the fields and their numbers

## Fields Still Needed for Migration

Since we're moving to Supabase, the only Knack fields still needed are:

1. **Authentication**: 
   - User email to match with Supabase records
   - Used only during login to find the user

2. **Initial Sync**: 
   - All the field mappings above for the sync scripts
   - After initial sync, dashboard uses Supabase only

3. **NO Knack fields needed in the new dashboard!**
   - All data comes from Supabase
   - Pre-calculated statistics
   - No field_xxx references in frontend code

## Common Knack Field Patterns

- `field_xxx` = The actual data
- `field_xxx_raw` = Raw/unformatted version
- Connection fields often have array format: `[{id: "record_id", identifier: "Display Name"}]`
- Boolean fields: `field_xxx_raw` = true/false, `field_xxx` = "Yes"/"No"

## Next Steps

1. Verify the field numbers I marked as "xxx" above
2. Update sync scripts with correct field numbers
3. Remove ALL Knack field references from the new dashboard code
4. Dashboard should only use Supabase table/column names