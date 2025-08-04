// Insights configuration with all 12 insight categories
export const insightDefinitions = {
  growth_mindset: {
    title: 'Growth Mindset',
    icon: '🌱',
    description: 'Measures students\' belief that intelligence and abilities can be developed through effort and learning.',
    why: 'Students with a growth mindset are more likely to persist through challenges, embrace feedback, and achieve better academic outcomes.',
    questions: [
      { id: 'Q5', text: 'No matter who you are, you can change your intelligence a lot' },
      { id: 'Q26', text: 'Your intelligence is something about you that you can change very much' }
    ],
    interpretation: {
      excellent: 'Most students believe they can improve their abilities - excellent foundation for learning',
      good: 'Good growth mindset culture, but room for improvement',
      average: 'Mixed beliefs about ability to improve - consider growth mindset interventions',
      poor: 'Fixed mindset prevalent - urgent need for growth mindset education'
    }
  },
  
  academic_momentum: {
    title: 'Academic Momentum',
    icon: '🚀',
    description: 'Captures students\' intrinsic drive, engagement with learning, and commitment to excellence.',
    why: 'Students with high academic momentum are self-motivated and more likely to sustain performance through challenges.',
    questions: [
      { id: 'Q14', text: 'I strive to achieve the goals I set for myself' },
      { id: 'Q16', text: 'I enjoy learning new things' },
      { id: 'Q17', text: 'I\'m not happy unless my work is the best it can be' },
      { id: 'Q9', text: 'I am a hard working student' }
    ],
    interpretation: {
      excellent: 'Students show strong drive and engagement - maintain this momentum',
      good: 'Good levels of motivation, but could be strengthened',
      average: 'Moderate engagement - explore ways to boost intrinsic motivation',
      poor: 'Low academic drive - investigate underlying causes and provide support'
    }
  },
  
  study_effectiveness: {
    title: 'Study Effectiveness',
    icon: '📚',
    description: 'Measures adoption of evidence-based study techniques that improve learning and retention.',
    why: 'Effective study techniques significantly improve exam performance and long-term retention of material.',
    questions: [
      { id: 'Q7', text: 'I test myself on important topics until I remember them' },
      { id: 'Q12', text: 'I spread out my revision, rather than cramming at the last minute' },
      { id: 'Q15', text: 'I summarise important information in diagrams, tables or lists' }
    ],
    interpretation: {
      excellent: 'Students use proven study techniques - likely to achieve strong results',
      good: 'Good study habits, but some techniques could be improved',
      average: 'Mixed study practices - provide training on effective techniques',
      poor: 'Poor study habits prevalent - urgent need for study skills training'
    }
  },
  
  exam_confidence: {
    title: 'Exam Confidence',
    icon: '💪',
    description: 'Students\' belief in their ability to achieve their potential in final exams.',
    why: 'Confidence correlates with performance - students who believe they can succeed are more likely to do so.',
    questions: [
      { id: 'Outcome_Q', text: 'I am confident I will achieve my potential in my final exams' }
    ],
    interpretation: {
      excellent: 'High confidence levels - students believe in their ability to succeed',
      good: 'Good confidence, but some students need reassurance',
      average: 'Mixed confidence - identify and support less confident students',
      poor: 'Low confidence widespread - investigate causes and provide support'
    }
  },
  
  organization_skills: {
    title: 'Organization Skills',
    icon: '📋',
    description: 'Measures students\' ability to plan, organize, and manage their academic responsibilities.',
    why: 'Well-organized students are less stressed, more productive, and better able to balance multiple demands.',
    questions: [
      { id: 'Q2', text: 'I plan and organise my time to get my work done' },
      { id: 'Q22', text: 'My books/files are organised' },
      { id: 'Q11', text: 'I always meet deadlines' }
    ],
    interpretation: {
      excellent: 'Students are highly organized - a key success factor',
      good: 'Good organizational skills, minor improvements possible',
      average: 'Mixed organization - provide tools and training',
      poor: 'Poor organization widespread - implement organizational support systems'
    }
  },
  
  resilience_factor: {
    title: 'Resilience',
    icon: '🛡️',
    description: 'Students\' ability to bounce back from setbacks and maintain a positive outlook.',
    why: 'Resilient students persist through challenges and learn from failures rather than being defeated by them.',
    questions: [
      { id: 'Q13', text: 'I don\'t let a poor test/assessment result get me down for too long' },
      { id: 'Q8', text: 'I have a positive view of myself' },
      { id: 'Q27', text: 'I like hearing feedback about how I can improve' }
    ],
    interpretation: {
      excellent: 'High resilience - students bounce back well from setbacks',
      good: 'Good resilience, but some students need support',
      average: 'Mixed resilience - build culture of learning from mistakes',
      poor: 'Low resilience - implement resilience-building programs'
    }
  },
  
  stress_management: {
    title: 'Stress Management',
    icon: '🧘',
    description: 'Students\' ability to handle academic pressure and control exam nerves.',
    why: 'Effective stress management improves performance, wellbeing, and prevents burnout.',
    questions: [
      { id: 'Q20', text: 'I feel I can cope with the pressure at school/college/University' },
      { id: 'Q28', text: 'I can control my nerves in tests/practical assessments' }
    ],
    interpretation: {
      excellent: 'Students manage stress well - maintain supportive environment',
      good: 'Good stress management, but monitor for changes',
      average: 'Some students struggling - provide stress management resources',
      poor: 'High stress levels - urgent intervention needed'
    }
  },
  
  active_learning: {
    title: 'Active Learning',
    icon: '🎯',
    description: 'Engagement with active learning techniques that deepen understanding and retention.',
    why: 'Active learning techniques are proven to be more effective than passive studying.',
    questions: [
      { id: 'Q7', text: 'I test myself on important topics until I remember them' },
      { id: 'Q23', text: 'When preparing for a test/exam I teach someone else the material' },
      { id: 'Q19', text: 'When revising I mix different kinds of topics/subjects in one study session' }
    ],
    interpretation: {
      excellent: 'Strong use of active learning - excellent practice',
      good: 'Good active learning, could expand techniques',
      average: 'Some active learning - promote more techniques',
      poor: 'Passive learning dominant - teach active strategies'
    }
  },
  
  support_readiness: {
    title: 'Support Readiness',
    icon: '🤝',
    description: 'Students\' perception of having adequate support to achieve their goals.',
    why: 'Students who feel supported are more likely to seek help when needed and achieve better outcomes.',
    questions: [
      { id: 'Outcome_Q2', text: 'I have the support I need to achieve this year' }
    ],
    interpretation: {
      excellent: 'Students feel well-supported - maintain this environment',
      good: 'Good support perception, but some gaps exist',
      average: 'Mixed feelings about support - investigate specific needs',
      poor: 'Students feel unsupported - review support systems urgently'
    }
  },
  
  time_management: {
    title: 'Time Management',
    icon: '⏰',
    description: 'Students\' ability to effectively plan and use their time for academic work.',
    why: 'Good time management reduces stress, improves work quality, and enables better work-life balance.',
    questions: [
      { id: 'Q2', text: 'I plan and organise my time to get my work done' },
      { id: 'Q4', text: 'I complete all my homework on time' },
      { id: 'Q11', text: 'I always meet deadlines' }
    ],
    interpretation: {
      excellent: 'Excellent time management skills across cohort',
      good: 'Good time management, minor improvements possible',
      average: 'Mixed time management - provide planning tools',
      poor: 'Poor time management - implement time management training'
    }
  },
  
  academic_confidence: {
    title: 'Academic Confidence',
    icon: '🎓',
    description: 'Students\' belief in their academic abilities and positive self-perception.',
    why: 'Academic confidence is a strong predictor of achievement and willingness to take on challenges.',
    questions: [
      { id: 'Q10', text: 'I am confident in my academic ability' },
      { id: 'Q8', text: 'I have a positive view of myself' }
    ],
    interpretation: {
      excellent: 'High academic confidence - students believe in themselves',
      good: 'Good confidence levels, some students need boosting',
      average: 'Mixed confidence - identify and support less confident students',
      poor: 'Low academic confidence - build success experiences'
    }
  },
  
  revision_readiness: {
    title: 'Revision Readiness',
    icon: '📝',
    description: 'Students\' perception of being equipped to handle revision and study challenges.',
    why: 'Feeling prepared for revision reduces anxiety and improves study effectiveness.',
    questions: [
      { id: 'Outcome_Q3', text: 'I feel equipped to face the study and revision challenges this year' }
    ],
    interpretation: {
      excellent: 'Students feel well-prepared for revision challenges',
      good: 'Good preparation, but some students need support',
      average: 'Mixed readiness - provide revision skills training',
      poor: 'Students feel unprepared - urgent revision support needed'
    }
  }
}

// Helper function to get score interpretation
export function getScoreInterpretation(score) {
  if (score >= 4.0) return 'excellent'
  if (score >= 3.0) return 'good'
  if (score >= 2.0) return 'average'
  return 'poor'
}

// Helper function to get color for score
export function getScoreColor(score) {
  if (score >= 4.0) return '#10b981' // green
  if (score >= 3.0) return '#3b82f6' // blue
  if (score >= 2.0) return '#f59e0b' // amber
  return '#ef4444' // red
}

// Helper function to calculate insight score from question responses
export function calculateInsightScore(insightKey, responses) {
  const insight = insightDefinitions[insightKey]
  if (!insight || !responses) return null
  
  const questionIds = insight.questions.map(q => q.id)
  let totalScore = 0
  let count = 0
  
  questionIds.forEach(qid => {
    // Look for the question in various field formats
    const fieldKeys = [
      `field_${qid}`, 
      `field_${qid}_raw`,
      qid,
      `${qid}_raw`
    ]
    
    for (const key of fieldKeys) {
      if (responses[key] !== undefined && responses[key] !== null) {
        const score = parseFloat(responses[key])
        if (!isNaN(score) && score >= 1 && score <= 5) {
          totalScore += score
          count++
          break
        }
      }
    }
  })
  
  return count > 0 ? totalScore / count : null
}