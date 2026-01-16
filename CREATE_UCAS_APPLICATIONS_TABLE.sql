-- UCAS Application drafts + staff comments (Supabase)
-- Stores UCAS 2026 3-question statement (combined 4,000 char limit) and per-course offer requirements.

CREATE TABLE IF NOT EXISTS ucas_applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_email TEXT NOT NULL,
  academic_year TEXT NOT NULL DEFAULT 'current',

  -- Statement data (3-question format)
  answers JSONB NOT NULL DEFAULT '{}'::jsonb,                -- { q1, q2, q3 }
  selected_course_key TEXT,                                 -- stable key from offer fields
  requirements_by_course JSONB NOT NULL DEFAULT '{}'::jsonb, -- { [courseKey]: { [subjectKey]: offerText } }

  -- Staff comments
  staff_comments JSONB NOT NULL DEFAULT '[]'::jsonb,         -- [{ id, staffEmail, comment, createdAt }]

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT unique_ucas_application UNIQUE(student_email, academic_year)
);

CREATE INDEX IF NOT EXISTS idx_ucas_applications_student_year
ON ucas_applications (student_email, academic_year);

-- Optional: if you use RLS, add policies separately.

