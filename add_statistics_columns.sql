-- Add additional statistical columns to national_statistics table if they don't exist
-- These store the rich statistical data from Knack Object_120 JSON fields

-- Check and add min column
ALTER TABLE national_statistics 
ADD COLUMN IF NOT EXISTS min_value NUMERIC(6,2);

-- Check and add max column  
ALTER TABLE national_statistics
ADD COLUMN IF NOT EXISTS max_value NUMERIC(6,2);

-- Check and add confidence interval columns
ALTER TABLE national_statistics
ADD COLUMN IF NOT EXISTS confidence_interval_lower NUMERIC(6,2);

ALTER TABLE national_statistics  
ADD COLUMN IF NOT EXISTS confidence_interval_upper NUMERIC(6,2);

-- Check and add skewness column
ALTER TABLE national_statistics
ADD COLUMN IF NOT EXISTS skewness NUMERIC(6,3);

-- Add a metadata column for any additional statistics
ALTER TABLE national_statistics
ADD COLUMN IF NOT EXISTS additional_stats JSONB;

-- Update column comments for documentation
COMMENT ON COLUMN national_statistics.min_value IS 'Minimum value from the distribution';
COMMENT ON COLUMN national_statistics.max_value IS 'Maximum value from the distribution';
COMMENT ON COLUMN national_statistics.confidence_interval_lower IS 'Lower bound of 95% confidence interval';
COMMENT ON COLUMN national_statistics.confidence_interval_upper IS 'Upper bound of 95% confidence interval';
COMMENT ON COLUMN national_statistics.skewness IS 'Statistical skewness of the distribution';
COMMENT ON COLUMN national_statistics.additional_stats IS 'JSON field for any additional statistical metrics';

-- Verify the table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'national_statistics'
ORDER BY ordinal_position;
