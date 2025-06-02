# DASHBOARD

An App which will be loaded into my Knack Application and contain a live, interactive Dashboard for the Staff Admin User Role.
The UI will show a variety of interactive charts and detailed information relating to the customers VESPA Results 
NB: The VESPA Questionnaire is an academic mindset questionnaire that records the students scores for 5 non-congitive elements - Vision - The degre to which the student has goals and a vision for their future, Effort- The degree to which the student reports hard wor, Systems - The degree to which the student reports they are organised, Practice - the degree to which the student is confident to undertake effective revision / study and Attitude - The degree to which the student has  apositive, growth mindset and is able to recover from setbacks

The main connection fields are - 
## 3. Data Map & Knowledge Base

### 3.1. Knack Objects & Key Fields

**Object_10: VESPA Results** (Primary record for a student's VESPA engagement)
*   `record_id`: Unique ID for this object's record.
*   `field_197_raw.email`: Student's email address (key for linking).
*   `field_187_raw.full`: Student Name.
*   `field_568_raw`: Student Level (e.g., "Level 2", "Level 3").
*   `field_146_raw`: `currentMCycle` (Indicates the latest completed VESPA cycle: 1, 2, or 3).
*   **Current VESPA Scores (1-10 scale, dynamically show latest cycle based on `field_146`):**
    *   `field_147`: Vision (V)
    *   `field_148`: Effort (E)
    *   `field_149`: Systems (S)
    *   `field_150`: Practice (P)
    *   `field_151`: Attitude (A)
    *   `field_152`: Overall (O)
*   **Historical Cycle 1 Scores (1-10 scale):**
    *   `field_155` - `field_160` (V1, E1, S1, P1, A1, O1)
*   **Historical Cycle 2 Scores (1-10 scale):**
    *   `field_161` - `field_166` (V2, E2, S2, P2, A2, O2)
*   **Historical Cycle 3 Scores (1-10 scale):**
    *   `field_167` - `field_172` (V3, E3, S3, P3, A3, O3)
*   `field_3271`: AI Coaching Summary (Write-back field for AI "memory").
*   **Student Reflections & Goals (Current Cycle - if available):**
    *   `field_2302`: RRC1 (Report Response Comment 1)
    *   `field_2303`: RRC2 (Report Response Comment 2)
    *   `field_2304`: RRC3 (Report Response Comment 3)
    *   `field_2499`: GOAL1 (Student Goal 1)
    *   `field_2493`: GOAL2 (Student Goal 2)
    *   `field_2494`: GOAL3 (Student Goal 3)

**Object_29: Questionnaire Qs** (Individual psychometric question responses)
*   `field_792`: Connection to `Object_10` (VESPA_RESULT).
*   `field_863_raw`: `Cycle` number (1, 2, or 3) for the responses in this record (assuming one `Object_29` record per cycle per student).
*   **Current Cycle Generic Response Fields (1-5 scale):**
    *   `field_794` - `field_821`, `field_2317`, `field_1816`, `field_1817`, `field_1818` (as mapped in `AIVESPACoach/question_id_to_text_mapping.json` and `AIVESPACoach/psychometric_question_details.json`).
*   **Historical Cycle-Specific Response Fields (1-5 scale):**
    *   e.g., `field_1953` (`c1_Q1v`), `field_1955` (`c2_Q1v`), `field_1956` (`c3_Q1v`), etc. (as mapped in `AIVESPACoach/psychometric_question_details.json`).

**Object_33: ReportText Content** (Content shown on student reports)
*   `field_848`: `Level` (e.g., "Level 2", "Level 3")
*   `field_844`: `Category` (e.g., "Vision", "Overall")
*   `field_842`: `ShowForScore` (e.g., "High", "Medium", "Low", "Very Low")
*   `field_845`: `Text` (Student report text)
*   `field_846`: `Questions` (Student report questions)
*   `field_847`: `Suggested Tools` (Student report tools)
*   `field_853`: `Coaching Comments` (Primary coaching prompts for tutor)
*   `field_849`, `field_850`, `field_851`, `field_854`: Welsh equivalents.

**Object_112: SubjectInformation / Homepage Profile** (Academic profile summary)
*   `field_3070`: `Account` (Connection to `Object_3` - User Account).
*   `field_3080` (`Sub1`) - `field_3094` (`Sub15`): Store JSON strings for each academic subject (details like subject name, exam type, board, MEG, CG, TG, effort, behavior, attendance).

**Object_3: User Accounts** (Central user table)
*   `record_id`: Unique ID for the user account.
*   `field_70`: User's email address (key for linking).

**Linkage Paths:**
*   **`Object_10` to `Object_112` (for Academic Data):** `Object_10.field_197_raw.email` -> `Object_3.field_70` (match email) -> Get `Object_3.record_id` -> Match with `Object_112.field_3070` (Account connection).
*   **`Object_10` to `Object_29` (for Individual Responses):** `Object_10.record_id` -> `Object_29.field_792` (VESPA_RESULT connection).
