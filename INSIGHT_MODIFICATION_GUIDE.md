# Guide to Modifying Questionnaire Insights

## Overview
To change which questions are included in each insight, you need to update **3 locations**:

## 1. Frontend Display (InsightDetailModal.vue)
**File**: `DASHBOARD-Vue/src/components/QLA/InsightDetailModal.vue`
**Lines**: 75-176

This controls what question text is shown in the modal when users click on an insight.

### Example Structure:
```javascript
time_management: {
  description: 'Students ability to effectively plan...',
  importance: 'Good time management reduces stress...',
  questions: {
    'q2': 'I complete all my homework on time',
    'q4': 'I start my work promptly rather than procrastinating', 
    'q11': 'I plan and organise my time to get my work done'
  }
}
```

## 2. Backend API Configuration (app.py)
**File**: `app.py`
**Lines**: ~6391-6450

This controls which questions are used to calculate the percentage scores.

### Example Structure:
```python
'time_management': {
    'title': 'Time Management',
    'question_ids': ['q2', 'q4', 'q11'],  # Must match frontend
    'icon': '⏰',
    'question': 'What percentage manage their time effectively?'
}
```

## 3. Frontend Fallback Data (api.js)
**File**: `DASHBOARD-Vue/src/services/api.js`
**Lines**: ~336-348

This provides fallback data if the API fails.

### Example Structure:
```javascript
{ 
  id: 'time_management', 
  title: 'Time Management', 
  percentageAgreement: 0, 
  questionIds: ['q2', 'q4', 'q11'],  // Must match backend
  icon: '⏰', 
  totalResponses: 0 
}
```

## Available Questions
Here are all questions you can use (must use lowercase IDs):

### Standard Questions (q1-q28)
- **q1**: I work as hard as I can in most classes
- **q2**: I complete all my homework on time
- **q3**: I enjoy studying  
- **q4**: I start my work promptly rather than procrastinating
- **q5**: No matter who you are, you can change your intelligence a lot
- **q6**: I always use comments from my teacher when preparing for tests
- **q7**: I test myself on important topics until I remember them
- **q8**: I have a positive view of myself
- **q9**: I am a hard working student
- **q10**: I am confident in my academic ability
- **q11**: I plan and organise my time to get my work done
- **q12**: I spread out my revision, rather than cramming at the last minute
- **q13**: I don't let a poor test/assessment result get me down for too long
- **q14**: I strive to achieve the goals I set for myself
- **q15**: I summarise important information in diagrams, tables or lists
- **q16**: I enjoy learning new things
- **q17**: I'm not happy unless my work is the best it can be
- **q18**: I ask my teachers when I don't understand something
- **q19**: When revising I mix different kinds of topics/subjects in one study session
- **q20**: I feel I can cope with the pressure at school/college/University
- **q21**: I track how well I'm doing in each of my subjects
- **q22**: My books/files are organised
- **q23**: When preparing for a test/exam I teach someone else the material
- **q24**: I always study in places where I can concentrate
- **q25**: If I become confused when studying, I go back and try to figure it out
- **q26**: Your intelligence is something about you that you can change very much
- **q27**: I like hearing feedback about how I can improve
- **q28**: I can control my nerves in tests/practical assessments

### Outcome Questions
- **outcome_q_confident**: I am confident I will achieve my potential in my final exams
- **outcome_q_equipped**: I feel equipped to face the study and revision challenges this year
- **outcome_q_support**: I have the support I need to achieve this year

## Steps to Modify an Insight

### Example: Changing Time Management to focus on procrastination
1. **Update Frontend Display** (`InsightDetailModal.vue`):
```javascript
time_management: {
  questions: {
    'q4': 'I start my work promptly rather than procrastinating',
    'q11': 'I plan and organise my time to get my work done',
    'q24': 'I always study in places where I can concentrate'
  }
}
```

2. **Update Backend API** (`app.py`):
```python
'time_management': {
    'question_ids': ['q4', 'q11', 'q24'],
    # ... rest stays the same
}
```

3. **Update Frontend Fallback** (`api.js`):
```javascript
{ 
  id: 'time_management',
  questionIds: ['q4', 'q11', 'q24'],
  // ... rest stays the same
}
```

4. **Rebuild Frontend**:
```bash
cd DASHBOARD-Vue
npm run build
```

5. **Commit and Deploy**:
```bash
git add -A
git commit -m "Update time management insight questions"
git push
```

## Important Notes
- Always use **lowercase** question IDs (q1, not Q1)
- Keep the same question IDs in all 3 locations
- The percentage calculation uses the distribution arrays from `question_statistics`
- Questions with scores 4 and 5 count as "agreement"
- After changes, the statistics don't need recalculating - the API dynamically calculates percentages

## Testing
After making changes:
1. Check the insight modal displays the correct question text
2. Verify the percentage calculations use the new questions
3. Test on different academic years/cycles to ensure consistency
