-- UCAS Teacher Reference system (Supabase)
-- Sections:
-- 1) Centre template (school-wide)
-- 2) Extenuating circumstances
-- 3) Supportive information (subject teacher contributions)
--
-- This schema supports:
-- - Many small contributions (multiple teachers per subject)
-- - External teachers via token invites (no Knack auth required)

CREATE TABLE IF NOT EXISTS reference_center_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  establishment_id TEXT NOT NULL,
  academic_year TEXT NOT NULL DEFAULT 'current',
  section1_text TEXT NOT NULL DEFAULT '',
  updated_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT unique_reference_center_template UNIQUE (establishment_id, academic_year)
);

CREATE TABLE IF NOT EXISTS student_references (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_email TEXT NOT NULL,
  establishment_id TEXT,
  academic_year TEXT NOT NULL DEFAULT 'current',

  status TEXT NOT NULL DEFAULT 'not_started'
    CHECK (status IN ('not_started','in_progress','completed','finalised')),

  student_marked_complete_at TIMESTAMPTZ,
  finalised_at TIMESTAMPTZ,
  finalised_by TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT unique_student_reference UNIQUE (student_email, academic_year)
);

CREATE TABLE IF NOT EXISTS reference_contributions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reference_id UUID NOT NULL REFERENCES student_references(id) ON DELETE CASCADE,
  section INT NOT NULL CHECK (section IN (2,3)),
  subject_key TEXT,
  author_email TEXT NOT NULL,
  author_name TEXT,
  author_type TEXT NOT NULL CHECK (author_type IN ('staff','invited_teacher')),
  text TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reference_contributions_ref
ON reference_contributions(reference_id);

CREATE INDEX IF NOT EXISTS idx_reference_contributions_section
ON reference_contributions(reference_id, section);

CREATE INDEX IF NOT EXISTS idx_reference_contributions_subject
ON reference_contributions(reference_id, subject_key);

CREATE TABLE IF NOT EXISTS reference_invites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reference_id UUID NOT NULL REFERENCES student_references(id) ON DELETE CASCADE,

  teacher_email TEXT NOT NULL,
  teacher_name TEXT,
  subject_key TEXT,
  allowed_sections INT[] NOT NULL DEFAULT ARRAY[3],

  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,

  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT unique_reference_invite_token UNIQUE (token_hash)
);

CREATE INDEX IF NOT EXISTS idx_reference_invites_ref
ON reference_invites(reference_id);

CREATE INDEX IF NOT EXISTS idx_reference_invites_teacher
ON reference_invites(teacher_email);

