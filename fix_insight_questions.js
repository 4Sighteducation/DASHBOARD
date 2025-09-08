// Fix for InsightDetailModal.vue - Lines to update

// 1. TIME MANAGEMENT (lines 155-159)
// BEFORE:
time_management: {
  questions: {
    'Q2': 'I plan and organise my time to get my work done',
    'q4': 'I complete all my homework on time', 
    'Q11': 'I always meet deadlines'
  }
}

// AFTER:
time_management: {
  questions: {
    'q2': 'I plan and organise my time to get my work done',
    'q4': 'I complete all my homework on time',
    'q11': 'I always meet deadlines'
  }
}

// 2. ACTIVE LEARNING (lines 139-143)
// BEFORE:
active_learning: {
  questions: {
    'Q7': 'I test myself on important topics until I remember them',
    'q23': 'When preparing for a test/exam I teach someone else the material',
    'q19': 'When revising I mix different kinds of topics/subjects in one study session'
  }
}

// AFTER:
active_learning: {
  questions: {
    'q7': 'I test myself on important topics until I remember them',
    'q23': 'When preparing for a test/exam I teach someone else the material',
    'q19': 'When revising I mix different kinds of topics/subjects in one study session'
  }
}

// 3. ORGANIZATION SKILLS - Also has uppercase (lines 114-116)
// BEFORE:
organization_skills: {
  questions: {
    'q2': 'I plan and organise my time to get my work done',
    'q22': 'My books/files are organised',
    'q11': 'I always meet deadlines'
  }
}
// This one is already correct - lowercase q2, q22, q11
