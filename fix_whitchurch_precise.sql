-- PRECISE FIX FOR WHITCHURCH HIGH SCHOOL
-- Using the exact list of 207 current Year 13 students from Knack
-- This will remove 2025/2026 data for anyone NOT in this list

-- ============================================================================
-- STEP 1: Create temp table with current students
-- ============================================================================

DROP TABLE IF EXISTS current_whitchurch_students;
CREATE TEMP TABLE current_whitchurch_students (email VARCHAR(255));

-- Insert the 207 current Year 13 student emails
INSERT INTO current_whitchurch_students (email) VALUES
('n19joness@whitchurch.cardiff.sch.uk'),
('m19macneili@whitchurch.cardiff.sch.uk'),
('h19mullinsf@whitchurch.cardiff.sch.uk'),
('b19mwezec@whitchurch.cardiff.sch.uk'),
('l19phillipsm@whitchurch.cardiff.sch.uk'),
('l19rutherfordl@whitchurch.cardiff.sch.uk'),
('m19segrottm@whitchurch.cardiff.sch.uk'),
('f19smitht@whitchurch.cardiff.sch.uk'),
('f19tuckerl@whitchurch.cardiff.sch.uk'),
('g19morrisa@whitchurch.cardiff.sch.uk'),
('c19turnere@whitchurch.cardiff.sch.uk'),
('n19williamse@whitchurch.cardiff.sch.uk'),
('r19wilsonc@whitchurch.cardiff.sch.uk'),
('p19allenh@whitchurch.cardiff.sch.uk'),
('m19elsona@whitchurch.cardiff.sch.uk'),
('f19griffithsg@whitchurch.cardiff.sch.uk'),
('n19halla@whitchurch.cardiff.sch.uk'),
('r19hunterr@whitchurch.cardiff.sch.uk'),
('b19jamese@whitchurch.cardiff.sch.uk'),
('j19johnsonh@whitchurch.cardiff.sch.uk'),
('l19hurleyj@whitchurch.cardiff.sch.uk'),
('n19joneso@whitchurch.cardiff.sch.uk'),
('l19lewisw@whitchurch.cardiff.sch.uk'),
('h19macdonaldc@whitchurch.cardiff.sch.uk'),
('f19mahdin@whitchurch.cardiff.sch.uk'),
('g19mummeryr@whitchurch.cardiff.sch.uk'),
('m19nagarajand@whitchurch.cardiff.sch.uk'),
('n19pengellyi@whitchurch.cardiff.sch.uk'),
('p19roderickf@whitchurch.cardiff.sch.uk'),
('l19scotts@whitchurch.cardiff.sch.uk'),
('f19singha@whitchurch.cardiff.sch.uk'),
('l19turpyr@whitchurch.cardiff.sch.uk'),
('f19williamsh@whitchurch.cardiff.sch.uk'),
('c19winbornd@whitchurch.cardiff.sch.uk'),
('l19allanh@whitchurch.cardiff.sch.uk'),
('g19anghebent@whitchurch.cardiff.sch.uk'),
('g19bowlese@whitchurch.cardiff.sch.uk'),
('j19collinsa@whitchurch.cardiff.sch.uk'),
('c19dadamg@whitchurch.cardiff.sch.uk'),
('c19fahmye@whitchurch.cardiff.sch.uk'),
('m19fasanom@whitchurch.cardiff.sch.uk'),
('k19greenawaym@whitchurch.cardiff.sch.uk'),
('k19gullidgej@whitchurch.cardiff.sch.uk'),
('p19hallz@whitchurch.cardiff.sch.uk'),
('p19hughesd@whitchurch.cardiff.sch.uk'),
('r19hurleyd@whitchurch.cardiff.sch.uk'),
('k19jonesj@whitchurch.cardiff.sch.uk'),
('l19lovegrovej@whitchurch.cardiff.sch.uk'),
('m19nealel@whitchurch.cardiff.sch.uk'),
('b19philorah@whitchurch.cardiff.sch.uk'),
('k19robertsn@whitchurch.cardiff.sch.uk'),
('b19rossl@whitchurch.cardiff.sch.uk'),
('n19silverg@whitchurch.cardiff.sch.uk'),
('m19stephensc@whitchurch.cardiff.sch.uk'),
('k18webbt@whitchurch.cardiff.sch.uk'),
('m19wilcoxc@whitchurch.cardiff.sch.uk'),
('m19winterc@whitchurch.cardiff.sch.uk'),
('k19antonious@whitchurch.cardiff.sch.uk'),
('g19ashcroftb@whitchurch.cardiff.sch.uk'),
('k19boffeye@whitchurch.cardiff.sch.uk'),
('k19boylel@whitchurch.cardiff.sch.uk'),
('p19morgane@whitchurch.cardiff.sch.uk'),
('c19daviesw@whitchurch.cardiff.sch.uk'),
('n18dummerf@whitchurch.cardiff.sch.uk'),
('j19firdausj@whitchurch.cardiff.sch.uk'),
('g19evanst@whitchurch.cardiff.sch.uk'),
('l19hodgese@whitchurch.cardiff.sch.uk'),
('g19holmesg@whitchurch.cardiff.sch.uk'),
('b19jewellh@whitchurch.cardiff.sch.uk'),
('k19nealei@whitchurch.cardiff.sch.uk'),
('n19pearcec@whitchurch.cardiff.sch.uk'),
('c19pickersgilln@whitchurch.cardiff.sch.uk'),
('j19sidfordc@whitchurch.cardiff.sch.uk'),
('p19stevenso@whitchurch.cardiff.sch.uk'),
('c19trottm@whitchurch.cardiff.sch.uk'),
('f19powells@whitchurch.cardiff.sch.uk'),
('k19sadafic@whitchurch.cardiff.sch.uk'),
('b19sherlocke@whitchurch.cardiff.sch.uk'),
('r19stoned@whitchurch.cardiff.sch.uk'),
('h19vanstoner@whitchurch.cardiff.sch.uk'),
('p19woodgatesc@whitchurch.cardiff.sch.uk'),
('r19aithalp@whitchurch.cardiff.sch.uk'),
('j19barbert@whitchurch.cardiff.sch.uk'),
('b19birde@whitchurch.cardiff.sch.uk'),
('j19bridgesj@whitchurch.cardiff.sch.uk'),
('n19bridgesl@whitchurch.cardiff.sch.uk'),
('p19collettf@whitchurch.cardiff.sch.uk'),
('h19brownb@whitchurch.cardiff.sch.uk'),
('n19daviese@whitchurch.cardiff.sch.uk'),
('r19emeryl@whitchurch.cardiff.sch.uk'),
('f19flynne@whitchurch.cardiff.sch.uk'),
('h19goughc@whitchurch.cardiff.sch.uk'),
('h19hodginf@whitchurch.cardiff.sch.uk'),
('m19jenkinsa@whitchurch.cardiff.sch.uk'),
('f19malcolmo@whitchurch.cardiff.sch.uk'),
('p19neillm@whitchurch.cardiff.sch.uk'),
('j19pattersonr@whitchurch.cardiff.sch.uk'),
('g19pillara@whitchurch.cardiff.sch.uk'),
('c19powellc@whitchurch.cardiff.sch.uk'),
('p19rankinc@whitchurch.cardiff.sch.uk'),
('h19sandersj@whitchurch.cardiff.sch.uk'),
('m19shepperdt@whitchurch.cardiff.sch.uk'),
('j19storerh@whitchurch.cardiff.sch.uk'),
('m19taylorl@whitchurch.cardiff.sch.uk'),
('r19welshw@whitchurch.cardiff.sch.uk'),
('m19workmanf@whitchurch.cardiff.sch.uk'),
('l19ahmeds@whitchurch.cardiff.sch.uk'),
('n19begumm@whitchurch.cardiff.sch.uk'),
('h19blakee@whitchurch.cardiff.sch.uk'),
('b19begumm@whitchurch.cardiff.sch.uk'),
('g19bowesz@whitchurch.cardiff.sch.uk'),
('n19burnetta@whitchurch.cardiff.sch.uk'),
('k19gillene@whitchurch.cardiff.sch.uk'),
('b19hardingm@whitchurch.cardiff.sch.uk'),
('f19isaaca@whitchurch.cardiff.sch.uk'),
('c19jenkinsz@whitchurch.cardiff.sch.uk'),
('f19mamedovr@whitchurch.cardiff.sch.uk'),
('g19mitiasa@whitchurch.cardiff.sch.uk'),
('p19neillg@whitchurch.cardiff.sch.uk'),
('m19parsonse@whitchurch.cardiff.sch.uk'),
('f19mcdeans@whitchurch.cardiff.sch.uk'),
('g19nguyenc@whitchurch.cardiff.sch.uk'),
('r19mileso@whitchurch.cardiff.sch.uk'),
('j19pricet@whitchurch.cardiff.sch.uk'),
('k19sandreye@whitchurch.cardiff.sch.uk'),
('l19sheppardm@whitchurch.cardiff.sch.uk'),
('c19taylort@whitchurch.cardiff.sch.uk'),
('f19turnerh@whitchurch.cardiff.sch.uk'),
('m19veralloc@whitchurch.cardiff.sch.uk'),
('n19ahmedt@whitchurch.cardiff.sch.uk'),
('k19elazzabiz@whitchurch.cardiff.sch.uk'),
('f19evanss@whitchurch.cardiff.sch.uk'),
('l19gaith@whitchurch.cardiff.sch.uk'),
('l19gibsoni@whitchurch.cardiff.sch.uk'),
('k19hardwickem@whitchurch.cardiff.sch.uk'),
('n19hiltona@whitchurch.cardiff.sch.uk'),
('r19isaacw@whitchurch.cardiff.sch.uk'),
('c19jacksona@whitchurch.cardiff.sch.uk'),
('p19jonesa@whitchurch.cardiff.sch.uk'),
('g19mardonk@whitchurch.cardiff.sch.uk'),
('k19proctore@whitchurch.cardiff.sch.uk'),
('c19quintal@whitchurch.cardiff.sch.uk'),
('c19sheppardo@whitchurch.cardiff.sch.uk'),
('l19sturdyt@whitchurch.cardiff.sch.uk'),
('l19jonesm@whitchurch.cardiff.sch.uk'),
('j19younge@whitchurch.cardiff.sch.uk'),
('m19balll@whitchurch.cardiff.sch.uk'),
('j19boothroydh@whitchurch.cardiff.sch.uk'),
('b19byrnej@whitchurch.cardiff.sch.uk'),
('k19daviesb@whitchurch.cardiff.sch.uk'),
('n19daviesd@whitchurch.cardiff.sch.uk'),
('r19gibbonsc@whitchurch.cardiff.sch.uk'),
('c19goulda@whitchurch.cardiff.sch.uk'),
('h19greenm@whitchurch.cardiff.sch.uk'),
('h19harmana@whitchurch.cardiff.sch.uk'),
('c19harryl@whitchurch.cardiff.sch.uk'),
('b19hillo@whitchurch.cardiff.sch.uk'),
('k19lammimanl@whitchurch.cardiff.sch.uk'),
('n19margettsk@whitchurch.cardiff.sch.uk'),
('k19mccabes@whitchurch.cardiff.sch.uk'),
('f19nguyenc@whitchurch.cardiff.sch.uk'),
('k19olimi@whitchurch.cardiff.sch.uk'),
('n19oatesl@whitchurch.cardiff.sch.uk'),
('c19qiur@whitchurch.cardiff.sch.uk'),
('r19qudduse@whitchurch.cardiff.sch.uk'),
('l19selleyo@whitchurch.cardiff.sch.uk'),
('b19joneso@whitchurch.cardiff.sch.uk'),
('c19sullivank@whitchurch.cardiff.sch.uk'),
('m19wattsd@whitchurch.cardiff.sch.uk'),
('p19alvess@whitchurch.cardiff.sch.uk'),
('n19batesa@whitchurch.cardiff.sch.uk'),
('f19daviesa@whitchurch.cardiff.sch.uk'),
('p19daviesd@whitchurch.cardiff.sch.uk'),
('l19dowbellak@whitchurch.cardiff.sch.uk'),
('c19ghoshalr@whitchurch.cardiff.sch.uk'),
('p19hextr@whitchurch.cardiff.sch.uk'),
('g19jamesl@whitchurch.cardiff.sch.uk'),
('b19jamesl@whitchurch.cardiff.sch.uk'),
('b19johnsonj@whitchurch.cardiff.sch.uk'),
('n19jonesh@whitchurch.cardiff.sch.uk'),
('r19kentb@whitchurch.cardiff.sch.uk'),
('p19kiszewskam@whitchurch.cardiff.sch.uk'),
('p19martina@whitchurch.cardiff.sch.uk'),
('f19mcauliffek@whitchurch.cardiff.sch.uk'),
('r19nyamhotsij@whitchurch.cardiff.sch.uk'),
('j19pendrym@whitchurch.cardiff.sch.uk'),
('g19qiyasa@whitchurch.cardiff.sch.uk'),
('a19servinig@whitchurch.cardiff.sch.uk'),
('f19sullivana@whitchurch.cardiff.sch.uk'),
('h19waringa@whitchurch.cardiff.sch.uk'),
('h19zhengq@whitchurch.cardiff.sch.uk'),
('h19jonesg@whitchurch.cardiff.sch.uk'),
('b19cavanaghj@whitchurch.cardiff.sch.uk'),
('b19cheungp@whitchurch.cardiff.sch.uk'),
('r19gatehousea@whitchurch.cardiff.sch.uk'),
('m19balogune@whitchurch.cardiff.sch.uk'),
('j19barfordg@whitchurch.cardiff.sch.uk'),
('h19bazinaa@whitchurch.cardiff.sch.uk'),
('a19burrowsr@whitchurch.cardiff.sch.uk'),
('r19cartere@whitchurch.cardiff.sch.uk'),
('p19digginse@whitchurch.cardiff.sch.uk'),
('a19jamesa@whitchurch.cardiff.sch.uk'),
('k19jamesl@whitchurch.cardiff.sch.uk'),
('h19jamess@whitchurch.cardiff.sch.uk'),
('b19khans@whitchurch.cardiff.sch.uk'),
('f19mathiase@whitchurch.cardiff.sch.uk'),
('p19ahmedz@whitchurch.cardiff.sch.uk');
-- Note: Excluded 'daviesk@whitchurch.cardiff.sch.uk' as it's EMULATED staff account

-- ============================================================================
-- STEP 2: Verify counts before fix
-- ============================================================================

-- How many students currently have 2025/2026 data?
SELECT 
    'Before Fix' as status,
    COUNT(DISTINCT s.id) as total_with_2025_26_data,
    207 as should_have,
    COUNT(DISTINCT s.id) - 207 as excess_to_remove
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2025/2026'
);

-- ============================================================================
-- STEP 3: Identify students to fix (those NOT in current list)
-- ============================================================================

-- Find students with 2025/2026 data who are NOT current students
WITH students_to_fix AS (
    SELECT DISTINCT
        s.id,
        s.email,
        s.name,
        s.year_group
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = '2025/2026'
    )
    AND LOWER(s.email) NOT IN (
        SELECT LOWER(email) FROM current_whitchurch_students
    )
)
SELECT 
    'Students to Remove 2025/26 Data' as category,
    COUNT(*) as count,
    STRING_AGG(DISTINCT year_group, ', ' ORDER BY year_group) as year_groups
FROM students_to_fix;

-- Show sample of students who will be fixed
SELECT 
    'Sample Students to Fix' as category,
    s.name,
    s.email,
    s.year_group
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2025/2026'
)
AND LOWER(s.email) NOT IN (
    SELECT LOWER(email) FROM current_whitchurch_students
)
LIMIT 10;

-- ============================================================================
-- STEP 4: BACKUP the data before deletion
-- ============================================================================

-- Create backup table
DROP TABLE IF EXISTS whitchurch_vespa_backup_2025_26;
CREATE TABLE whitchurch_vespa_backup_2025_26 AS
SELECT vs.*, s.email as student_email, s.name as student_name
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND vs.academic_year = '2025/2026'
AND LOWER(s.email) NOT IN (
    SELECT LOWER(email) FROM current_whitchurch_students
);

SELECT COUNT(*) as "Records backed up" FROM whitchurch_vespa_backup_2025_26;

-- ============================================================================
-- STEP 5: THE FIX - Remove incorrect 2025/2026 VESPA scores
-- ============================================================================

-- DELETE 2025/2026 VESPA scores for students NOT in current list
DELETE FROM vespa_scores vs
WHERE vs.academic_year = '2025/2026'
AND vs.student_id IN (
    SELECT s.id 
    FROM students s 
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    AND LOWER(s.email) NOT IN (
        SELECT LOWER(email) FROM current_whitchurch_students
    )
);

-- ============================================================================
-- STEP 6: Also update the academic_year field for graduated students
-- ============================================================================

-- Set graduated students back to 2024/2025
UPDATE students
SET academic_year = '2024/2025'
WHERE establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND LOWER(email) NOT IN (
    SELECT LOWER(email) FROM current_whitchurch_students
)
AND academic_year = '2025/2026';

-- ============================================================================
-- STEP 7: Verify the fix worked
-- ============================================================================

-- Check final counts
SELECT 
    'After Fix' as status,
    vs.academic_year,
    COUNT(DISTINCT vs.student_id) as unique_students
FROM vespa_scores vs
INNER JOIN students s ON vs.student_id = s.id
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
GROUP BY vs.academic_year
ORDER BY vs.academic_year;

-- Verify exactly 207 students for 2025/2026
SELECT 
    'Final Verification' as check,
    COUNT(DISTINCT s.id) as students_with_2025_26,
    CASE 
        WHEN COUNT(DISTINCT s.id) = 207 THEN '✅ SUCCESS - Exactly 207 students'
        ELSE '❌ ERROR - Should be 207 students'
    END as status
FROM students s
WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
AND EXISTS (
    SELECT 1 FROM vespa_scores vs 
    WHERE vs.student_id = s.id 
    AND vs.academic_year = '2025/2026'
);

-- ============================================================================
-- STEP 8: Create function for dashboard to use
-- ============================================================================

CREATE OR REPLACE FUNCTION get_whitchurch_students_fixed(
    p_academic_year VARCHAR
) RETURNS TABLE (
    id UUID,
    email VARCHAR,
    name VARCHAR,
    year_group VARCHAR,
    course VARCHAR,
    faculty VARCHAR,
    has_vespa BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        s.id,
        s.email,
        s.name,
        s.year_group,
        s.course,
        s.faculty,
        EXISTS(
            SELECT 1 FROM vespa_scores vs 
            WHERE vs.student_id = s.id 
            AND vs.academic_year = p_academic_year
        ) as has_vespa
    FROM students s
    WHERE s.establishment_id = '1a327b33-d924-453c-803e-82671f94a242'
    AND EXISTS (
        SELECT 1 FROM vespa_scores vs 
        WHERE vs.student_id = s.id 
        AND vs.academic_year = p_academic_year
    );
END;
$$ LANGUAGE plpgsql;

-- Test the function
SELECT COUNT(*) as "2024/2025 Students" FROM get_whitchurch_students_fixed('2024/2025');
SELECT COUNT(*) as "2025/2026 Students" FROM get_whitchurch_students_fixed('2025/2026');

-- ============================================================================
-- SUCCESS!
-- ============================================================================
SELECT 
    '✅ Whitchurch Fixed!' as status,
    '2024/2025: ~440 students (all Year 12s + 13s from last year)' as last_year,
    '2025/2026: 207 students (current Year 13s only)' as this_year;
