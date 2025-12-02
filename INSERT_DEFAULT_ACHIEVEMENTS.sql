-- Insert default achievement definitions
-- Run this in Supabase SQL Editor to populate achievement_definitions table

-- First, create the table if it doesn't exist
CREATE TABLE IF NOT EXISTS achievement_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    achievement_type VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    icon_emoji VARCHAR(10) DEFAULT '🏆',
    points_value INTEGER DEFAULT 0,
    criteria JSONB,
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert the standard achievements
INSERT INTO achievement_definitions (achievement_type, name, description, icon_emoji, points_value, criteria, display_order) 
VALUES 
    ('first_steps', 'First Steps! 🎯', 'Complete your first activity - every journey begins with a single step!', '🎯', 5, '{"min_completed": 1}', 1),
    ('getting_going', 'Getting Going! 🚀', 'Complete 5 activities - you''re building momentum!', '🚀', 25, '{"min_completed": 5}', 2),
    ('on_fire', 'On Fire! 🔥', 'Complete 10 activities - unstoppable progress!', '🔥', 50, '{"min_completed": 10}', 3),
    ('unstoppable', 'Unstoppable! ⭐', 'Complete 25 activities - you''re a VESPA superstar!', '⭐', 100, '{"min_completed": 25}', 4),
    ('vespa_champion', 'VESPA Champion! 🏆', 'Complete 50 activities - legendary achievement!', '🏆', 200, '{"min_completed": 50}', 5),
    ('streak_3', 'Three Day Streak! 🌟', 'Complete activities 3 days in a row', '🌟', 15, '{"streak_days": 3}', 6),
    ('streak_7', 'Week Warrior! 💪', 'Complete activities 7 days in a row', '💪', 50, '{"streak_days": 7}', 7),
    ('streak_14', 'Fortnight Fighter! ⚡', 'Complete activities 14 days in a row', '⚡', 100, '{"streak_days": 14}', 8),
    ('category_vision', 'Vision Expert! 👁️', 'Complete 5 Vision activities', '👁️', 30, '{"category": "Vision", "min_completed": 5}', 10),
    ('category_effort', 'Effort Expert! 💪', 'Complete 5 Effort activities', '💪', 30, '{"category": "Effort", "min_completed": 5}', 11),
    ('category_systems', 'Systems Expert! ⚙️', 'Complete 5 Systems activities', '⚙️', 30, '{"category": "Systems", "min_completed": 5}', 12),
    ('category_practice', 'Practice Expert! 🎯', 'Complete 5 Practice activities', '🎯', 30, '{"category": "Practice", "min_completed": 5}', 13),
    ('category_attitude', 'Attitude Expert! 🧠', 'Complete 5 Attitude activities', '🧠', 30, '{"category": "Attitude", "min_completed": 5}', 14)
ON CONFLICT (achievement_type) DO NOTHING;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_achievement_definitions_active ON achievement_definitions(is_active);
CREATE INDEX IF NOT EXISTS idx_achievement_definitions_type ON achievement_definitions(achievement_type);

