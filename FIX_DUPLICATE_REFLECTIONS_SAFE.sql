-- Safe Deletion of Duplicate Reflection Questions
-- Keeps the FIRST occurrence (lowest display_order) of each question

-- STEP 1: See which questions will be KEPT (the ones with lowest display_order)
SELECT 
  'KEPT' as action,
  id,
  activity_id,
  question_title,
  display_order,
  created_at
FROM activity_questions
WHERE show_in_final_questions = true
  AND id IN (
    -- These are the IDs that will be KEPT
    SELECT DISTINCT ON (activity_id, question_title)
      id
    FROM activity_questions
    WHERE show_in_final_questions = true
    ORDER BY activity_id, question_title, display_order ASC, created_at ASC
  )
ORDER BY activity_id, question_title, display_order;

-- STEP 2: See which questions will be DELETED (higher display_order duplicates)
SELECT 
  'WILL DELETE' as action,
  id,
  activity_id,
  question_title,
  display_order,
  created_at
FROM activity_questions
WHERE show_in_final_questions = true
  AND id NOT IN (
    SELECT DISTINCT ON (activity_id, question_title)
      id
    FROM activity_questions
    WHERE show_in_final_questions = true
    ORDER BY activity_id, question_title, display_order ASC, created_at ASC
  )
ORDER BY activity_id, question_title, display_order;

-- STEP 3: Actual deletion (UNCOMMENT AND RUN AFTER REVIEWING ABOVE)
/*
DELETE FROM activity_questions
WHERE show_in_final_questions = true
  AND id NOT IN (
    SELECT DISTINCT ON (activity_id, question_title)
      id
    FROM activity_questions
    WHERE show_in_final_questions = true
    ORDER BY activity_id, question_title, display_order ASC, created_at ASC
  );
*/

-- STEP 4: Verify no reflection duplicates remain (should return 0 rows)
/*
SELECT 
  activity_id,
  question_title,
  COUNT(*) as count
FROM activity_questions 
WHERE is_active = true 
  AND show_in_final_questions = true
GROUP BY activity_id, question_title
HAVING COUNT(*) > 1;
*/

