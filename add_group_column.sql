-- Add group column to students table
-- This column stores field_223 from Knack Object_10

ALTER TABLE students 
ADD COLUMN IF NOT EXISTS "group" VARCHAR(100);

-- Optional: Add comment for documentation
COMMENT ON COLUMN students."group" IS 'Student group from Knack field_223';

-- Also add a unique constraint on email for future flexibility
-- (This is optional since we're using knack_id for conflicts)
-- ALTER TABLE students ADD CONSTRAINT students_email_unique UNIQUE (email);