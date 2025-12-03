-- Fix Duplicate Reflection Questions
-- Only removes duplicates where show_in_final_questions = true (Reflect section)
-- Keeps the oldest question (lowest display_order) for each duplicate set

-- Step 1: See what will be deleted (DRY RUN)
SELECT 
  id,
  activity_id,
  question_title,
  display_order,
  created_at
FROM activity_questions
WHERE show_in_final_questions = true
  AND id NOT IN (
    -- Keep only the first occurrence (lowest display_order/oldest created_at)
    SELECT DISTINCT ON (activity_id, question_title)
      id
    FROM activity_questions
    WHERE show_in_final_questions = true
    ORDER BY activity_id, question_title, display_order ASC, created_at ASC
  )
ORDER BY activity_id, question_title, display_order;

-- Step 2: Actual deletion (RUN THIS AFTER REVIEWING STEP 1)
-- DELETE FROM activity_questions
-- WHERE show_in_final_questions = true
--   AND id NOT IN (
--     SELECT DISTINCT ON (activity_id, question_title)
--       id
--     FROM activity_questions
--     WHERE show_in_final_questions = true
--     ORDER BY activity_id, question_title, display_order ASC, created_at ASC
--   );

-- Step 3: Verify no duplicates remain
-- SELECT 
--   activity_id,
--   question_title,
--   COUNT(*) as count
-- FROM activity_questions 
-- WHERE is_active = true 
--   AND show_in_final_questions = true
-- GROUP BY activity_id, question_title
-- HAVING COUNT(*) > 1;

