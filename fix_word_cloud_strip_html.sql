-- Updated word cloud function that strips HTML tags
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
    cleaned_comments AS (
        SELECT 
            -- Strip HTML tags and decode common HTML entities
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        regexp_replace(
                            regexp_replace(comment_text, '<[^>]*>', ' ', 'g'),  -- Remove HTML tags
                            '&nbsp;', ' ', 'g'  -- Replace &nbsp; with space
                        ),
                        '&amp;', '&', 'g'  -- Replace &amp; with &
                    ),
                    '&lt;', '<', 'g'  -- Replace &lt; with <
                ),
                '&gt;', '>', 'g'  -- Replace &gt; with >
            ) AS clean_text
        FROM filtered_comments
        WHERE LENGTH(comment_text) > 0
    ),
    words AS (
        SELECT LOWER(
            regexp_split_to_table(
                -- Remove punctuation and split by spaces
                regexp_replace(clean_text, '[^a-zA-Z0-9\s]', ' ', 'g'),
                '\s+'
            )
        ) AS word
        FROM cleaned_comments
        WHERE LENGTH(clean_text) > 0
    )
    SELECT 
        words.word,
        COUNT(*)::INTEGER as frequency
    FROM words
    WHERE 
        LENGTH(words.word) > 2
        AND words.word NOT IN (
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
    GROUP BY words.word
    HAVING COUNT(*) > 1
    ORDER BY frequency DESC
    LIMIT 100;
END;
$$ LANGUAGE plpgsql;

-- Also create a helper function to strip HTML for general use
CREATE OR REPLACE FUNCTION strip_html(text_with_html TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        COALESCE(text_with_html, ''), 
                        '<[^>]*>', ' ', 'g'  -- Remove HTML tags
                    ),
                    '&nbsp;', ' ', 'g'
                ),
                '&amp;', '&', 'g'
            ),
            '&lt;', '<', 'g'
        ),
        '&gt;', '>', 'g'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Example usage to see cleaned comments
-- SELECT 
--     comment_text as original,
--     strip_html(comment_text) as cleaned
-- FROM student_comments 
-- LIMIT 5;