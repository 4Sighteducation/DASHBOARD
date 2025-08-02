-- Create questions table to store all psychometric questions
-- This provides a single source of truth for question metadata

-- Drop table if exists (for clean migration)
DROP TABLE IF EXISTS questions CASCADE;

-- Create the questions table
CREATE TABLE questions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    question_id VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'q1', 'q2', 'outcome_q_support'
    question_text TEXT NOT NULL,
    vespa_category VARCHAR(20) NOT NULL, -- 'VISION', 'EFFORT', 'SYSTEMS', 'PRACTICE', 'ATTITUDE', 'NA_OUTCOME'
    question_order INTEGER, -- for display ordering
    current_cycle_field_id VARCHAR(20),
    historical_cycle_field_base VARCHAR(20), -- e.g., 'Q1v', 'Q2s'
    field_id_cycle_1 VARCHAR(20),
    field_id_cycle_2 VARCHAR(20), 
    field_id_cycle_3 VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_questions_question_id ON questions(question_id);
CREATE INDEX idx_questions_vespa_category ON questions(vespa_category);
CREATE INDEX idx_questions_order ON questions(question_order);

-- Add RLS policies
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read questions
CREATE POLICY "Allow authenticated users to read questions" ON questions
    FOR SELECT 
    TO authenticated
    USING (true);

-- Allow service role to manage questions (for initial load and updates)
CREATE POLICY "Allow service role to manage questions" ON questions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Alternatively, you can temporarily allow authenticated users to insert
-- This policy can be removed after initial data load if needed
CREATE POLICY "Allow authenticated users to insert questions" ON questions
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Add comments for documentation
COMMENT ON TABLE questions IS 'Static table containing all psychometric questions and their metadata';
COMMENT ON COLUMN questions.question_id IS 'Unique identifier for the question (e.g., q1, q2)';
COMMENT ON COLUMN questions.vespa_category IS 'VESPA category: VISION, EFFORT, SYSTEMS, PRACTICE, ATTITUDE, or NA_OUTCOME';
COMMENT ON COLUMN questions.question_order IS 'Display order for questions in the UI';
COMMENT ON COLUMN questions.historical_cycle_field_base IS 'Base field name for historical data (e.g., Q1v)';

-- Create a view for easy access to VESPA questions only
CREATE OR REPLACE VIEW vespa_questions AS
SELECT * FROM questions 
WHERE vespa_category != 'NA_OUTCOME' 
  AND is_active = true
ORDER BY question_order;