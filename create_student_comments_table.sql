-- Create table for student comments and goals
CREATE TABLE IF NOT EXISTS student_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    cycle INTEGER NOT NULL CHECK (cycle IN (1, 2, 3)),
    comment_type VARCHAR(10) NOT NULL CHECK (comment_type IN ('rrc', 'goal')),
    comment_text TEXT,
    knack_field_id VARCHAR(20), -- Store which field this came from for tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one comment per student/cycle/type combination
    CONSTRAINT unique_student_comment UNIQUE (student_id, cycle, comment_type)
);

-- Create indexes for efficient queries
CREATE INDEX idx_student_comments_student_id ON student_comments(student_id);
CREATE INDEX idx_student_comments_cycle ON student_comments(cycle);
CREATE INDEX idx_student_comments_type ON student_comments(comment_type);
CREATE INDEX idx_student_comments_student_cycle ON student_comments(student_id, cycle);

-- Add RLS policies
ALTER TABLE student_comments ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role can manage all comments" ON student_comments
    FOR ALL USING (auth.role() = 'service_role');

-- Allow authenticated users to read comments for their establishment
CREATE POLICY "Users can read comments for their establishment" ON student_comments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM students s
            WHERE s.id = student_comments.student_id
            AND s.establishment_id IN (
                SELECT establishment_id FROM staff_admins 
                WHERE email = auth.jwt() ->> 'email'
            )
        )
    );

-- Create a view for word cloud generation
CREATE OR REPLACE VIEW student_comments_aggregated AS
SELECT 
    s.establishment_id,
    s.year_group,
    s.course,
    s.faculty,
    s."group",
    sc.cycle,
    sc.comment_type,
    sc.comment_text,
    vs.academic_year
FROM student_comments sc
JOIN students s ON s.id = sc.student_id
LEFT JOIN vespa_scores vs ON vs.student_id = sc.student_id AND vs.cycle = sc.cycle
WHERE sc.comment_text IS NOT NULL AND LENGTH(TRIM(sc.comment_text)) > 0;

-- Create function to get word frequencies for word cloud
CREATE OR REPLACE FUNCTION get_word_cloud_data(
    p_establishment_id UUID DEFAULT NULL,
    p_cycle INTEGER DEFAULT NULL,
    p_comment_type VARCHAR DEFAULT NULL,
    p_year_group VARCHAR DEFAULT NULL,
    p_course VARCHAR DEFAULT NULL,
    p_faculty VARCHAR DEFAULT NULL,
    p_group VARCHAR DEFAULT NULL,
    p_academic_year VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    word TEXT,
    frequency INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH filtered_comments AS (
        SELECT comment_text
        FROM student_comments_aggregated
        WHERE 
            (p_establishment_id IS NULL OR establishment_id = p_establishment_id)
            AND (p_cycle IS NULL OR cycle = p_cycle)
            AND (p_comment_type IS NULL OR comment_type = p_comment_type)
            AND (p_year_group IS NULL OR year_group = p_year_group)
            AND (p_course IS NULL OR course = p_course)
            AND (p_faculty IS NULL OR faculty = p_faculty)
            AND (p_group IS NULL OR "group" = p_group)
            AND (p_academic_year IS NULL OR academic_year = p_academic_year)
    ),
    words AS (
        SELECT LOWER(
            regexp_split_to_table(
                -- Remove punctuation and split by spaces
                regexp_replace(comment_text, '[^a-zA-Z0-9\s]', ' ', 'g'),
                '\s+'
            )
        ) AS word
        FROM filtered_comments
        WHERE LENGTH(comment_text) > 0
    )
    SELECT 
        word,
        COUNT(*)::INTEGER as frequency
    FROM words
    WHERE 
        LENGTH(word) > 2  -- Ignore very short words
        AND word NOT IN ( -- Common stop words
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'how',
            'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
            'did', 'his', 'put', 'say', 'she', 'too', 'use', 'that', 'with', 'have',
            'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good',
            'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like',
            'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well',
            'only', 'year', 'work', 'back', 'call', 'came', 'each', 'even', 'find',
            'give', 'hand', 'high', 'keep', 'last', 'left', 'life', 'live', 'look',
            'made', 'most', 'move', 'must', 'name', 'need', 'next', 'open', 'part',
            'play', 'said', 'same', 'seem', 'show', 'side', 'tell', 'turn', 'used',
            'want', 'ways', 'week', 'went', 'were', 'what', 'word', 'work', 'year'
        )
    GROUP BY word
    HAVING COUNT(*) > 1  -- Only show words that appear more than once
    ORDER BY frequency DESC
    LIMIT 100;  -- Limit to top 100 words
END;
$$ LANGUAGE plpgsql;

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_student_comments_updated_at BEFORE UPDATE ON student_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();