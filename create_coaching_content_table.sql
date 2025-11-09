-- Create coaching_content table in Supabase
-- Stores all VESPA coaching statements, questions, and suggestions

CREATE TABLE IF NOT EXISTS coaching_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level VARCHAR(20) NOT NULL,  -- 'Level 2' or 'Level 3'
    category VARCHAR(20) NOT NULL,  -- 'Vision', 'Effort', 'Systems', 'Practice', 'Attitude', 'Overall'
    score_min INTEGER NOT NULL,  -- Minimum score for this content
    score_max INTEGER NOT NULL,  -- Maximum score for this content
    rating VARCHAR(20),  -- 'Very Low', 'Low', 'Medium', 'High', 'Very High'
    statement_text TEXT,  -- Main coaching statement
    questions TEXT[],  -- Array of questions
    coaching_comments TEXT[],  -- Array of coaching comments
    suggested_tools TEXT,  -- Suggested activities/tools
    welsh_text TEXT,  -- Welsh translation of statement
    welsh_questions TEXT,  -- Welsh questions
    welsh_tools TEXT,  -- Welsh tools
    welsh_coaching_comments TEXT,  -- Welsh coaching comments
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Composite unique constraint
    UNIQUE (level, category, score_min, score_max)
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_coaching_content_lookup 
ON coaching_content (level, category, score_min, score_max);

-- Add helpful comment
COMMENT ON TABLE coaching_content IS 'VESPA coaching content by level, category, and score range';

