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
    'q2': 'I plan and organise my time to get my work done',
    'q4': 'I complete all my homework on time', 
    'q11': 'I always meet deadlines'
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

### Standard Questions (q1-q29)
- **q1**: I've worked out the next steps in my life
- **q2**: I plan and organise my time to get my work done
- **q3**: I give a lot of attention to my career planning
- **q4**: I complete all my homework on time
- **q5**: No matter who you are, you can change your intelligence a lot
- **q6**: I use all my independent study time effectively
- **q7**: I test myself on important topics until I remember them
- **q8**: I have a positive view of myself
- **q9**: I am a hard working student
- **q10**: I am confident in my academic ability
- **q11**: I always meet deadlines
- **q12**: I spread out my revision, rather than cramming at the last minute
- **q13**: I don't let a poor test/assessment result get me down for too long
- **q14**: I strive to achieve the goals I set for myself
- **q15**: I summarise important information in diagrams, tables or lists
- **q16**: I enjoy learning new things
- **q17**: I'm not happy unless my work is the best it can be
- **q18**: I take good notes in class which are useful for revision
- **q19**: When revising I mix different kinds of topics/subjects in one study session
- **q20**: I feel I can cope with the pressure at school/college/University
- **q21**: I work as hard as I can in most classes
- **q22**: My books/files are organised
- **q23**: When preparing for a test/exam I teach someone else the material
- **q24**: I'm happy to ask questions in front of a group
- **q25**: I use highlighting/colour coding for revision
- **q26**: Your intelligence is something about you that you can change very much
- **q27**: I like hearing feedback about how I can improve
- **q28**: I can control my nerves in tests/practical assessments
- **q29**: I understand why education is important for my future


### Outcome Questions
- **outcome_q_confident**: I am confident I will achieve my potential in my final exams
- **outcome_q_equipped**: I feel equipped to face the study and revision challenges this year
- **outcome_q_support**: I have the support I need to achieve this year

## Steps to Modify an Insight

### Example: Changing Time Management to include independent study
1. **Update Frontend Display** (`InsightDetailModal.vue`):
```javascript
time_management: {
  questions: {
    'q2': 'I plan and organise my time to get my work done',
    'q6': 'I use all my independent study time effectively',
    'q11': 'I always meet deadlines'
  }
}
```

2. **Update Backend API** (`app.py`):
```python
'time_management': {
    'question_ids': ['q2', 'q6', 'q11'],
    # ... rest stays the same
}
```

3. **Update Frontend Fallback** (`api.js`):
```javascript
{ 
  id: 'time_management',
  questionIds: ['q2', 'q6', 'q11'],
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

## Current Insight Configurations

Here are all the current insights and their questions as configured in the system:

### 1. Growth Mindset 🌱
- **Questions**: `q5`, `q26`, `q27`, `q16`
- **q5**: No matter who you are, you can change your intelligence a lot
- **q26**: Your intelligence is something about you that you can change very much
- **q27**: I like hearing feedback about how I can improve
- **q16**: I enjoy learning new things

### 2. Academic Momentum 🚀
- **Questions**: `q14`, `q16`, `q17`, `q9`
- **q14**: I strive to achieve the goals I set for myself
- **q16**: I enjoy learning new things
- **q17**: I'm not happy unless my work is the best it can be
- **q9**: I am a hard working student

### 3. Vision & Purpose 🎯
- **Questions**: `q1`, `q3`, `q29`
- **q1**: I've worked out the next steps in my life
- **q3**: I give a lot of attention to my career planning
- **q29**: I understand why education is important for my future

### 4. Study Strategies 📚
- **Questions**: `q7`, `q12`, `q15`, `q18`
- **q7**: I test myself on important topics until I remember them
- **q12**: I spread out my revision, rather than cramming at the last minute
- **q15**: I summarise important information in diagrams, tables or lists
- **q18**: I take good notes in class which are useful for revision

### 5. Exam Confidence ⭐
- **Questions**: `outcome_q_confident`, `q10`, `q28`
- **outcome_q_confident**: I am confident I will achieve my potential in my final exams
- **q10**: I am confident in my academic ability
- **q28**: I can control my nerves in tests/practical assessments

### 6. Organization & Materials 📦
- **Questions**: `q22`, `q18`, `q25`
- **q22**: My books/files are organised
- **q18**: I take good notes in class which are useful for revision
- **q25**: I use highlighting/colour coding for revision

### 7. Resilience Factor 💪
- **Questions**: `q13`, `q27`, `q8`
- **q13**: I don't let a poor test/assessment result get me down for too long
- **q27**: I like hearing feedback about how I can improve
- **q8**: I have a positive view of myself

### 8. Stress Management 😌
- **Questions**: `q20`, `q28`, `q24`
- **q20**: I feel I can cope with the pressure at school/college/University
- **q28**: I can control my nerves in tests/practical assessments
- **q24**: I'm happy to ask questions in front of a group

### 9. Support & Help-Seeking 🤝
- **Questions**: `outcome_q_support`, `q24`, `q27`
- **outcome_q_support**: I have the support I need to achieve this year
- **q24**: I'm happy to ask questions in front of a group
- **q27**: I like hearing feedback about how I can improve

### 10. Time Management ⏰
- **Questions**: `q2`, `q4`, `q11`
- **q2**: I plan and organise my time to get my work done
- **q4**: I complete all my homework on time
- **q11**: I always meet deadlines

### 11. Active Learning 🎓
- **Questions**: `q23`, `q19`, `q7`
- **q23**: When preparing for a test/exam I teach someone else the material
- **q19**: When revising I mix different kinds of topics/subjects in one study session
- **q7**: I test myself on important topics until I remember them

### 12. Revision Readiness 📖
- **Questions**: `outcome_q_equipped`, `q7`, `q12`, `q18`
- **outcome_q_equipped**: I feel equipped to face the study and revision challenges this year
- **q7**: I test myself on important topics until I remember them
- **q12**: I spread out my revision, rather than cramming at the last minute
- **q18**: I take good notes in class which are useful for revision

## Notes on Current Configuration
- **q7** appears in "Study Strategies", "Active Learning", and "Revision Readiness"
- **q12** appears in "Study Strategies" and "Revision Readiness"
- **q16** appears in "Growth Mindset" and "Academic Momentum"
- **q18** appears in "Study Strategies", "Organization & Materials", and "Revision Readiness"
- **q24** appears in "Stress Management" and "Support & Help-Seeking"
- **q27** appears in "Growth Mindset", "Resilience Factor", and "Support & Help-Seeking"
- **q28** appears in "Exam Confidence" and "Stress Management"
- This overlap is intentional as these questions contribute to multiple psychological constructs
