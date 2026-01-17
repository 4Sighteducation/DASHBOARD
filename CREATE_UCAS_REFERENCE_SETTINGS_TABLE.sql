-- Establishment-level settings for UCAS Reference workflow (Supabase)
-- Stores per-school UCAS lead / staff admin notification targets.

CREATE TABLE IF NOT EXISTS establishment_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  establishment_id TEXT NOT NULL,

  -- Emails of UCAS reference admins / UCAS leads for this establishment
  -- Stored as JSONB array: ["admin@school.org", "ucaslead@school.org"]
  ucas_reference_admin_emails JSONB NOT NULL DEFAULT '[]'::jsonb,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT unique_establishment_settings UNIQUE(establishment_id)
);

CREATE INDEX IF NOT EXISTS idx_establishment_settings_establishment
ON establishment_settings (establishment_id);

