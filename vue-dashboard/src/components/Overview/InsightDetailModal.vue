<template>
  <div class="insight-modal" @click.self="$emit('close')">
    <div class="insight-modal-content">
      <!-- Header -->
      <div class="modal-header">
        <div class="header-title">
          <span class="modal-icon">{{ insight.icon }}</span>
          <h2>{{ insight.title }}</h2>
        </div>
        <button class="modal-close" @click="$emit('close')">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Score Summary -->
      <div :class="['score-summary', insight.interpretation]">
        <div class="score-display">
          <div class="score-number">{{ insight.score.toFixed(2) }}</div>
          <div class="score-text">
            <div class="score-label">Average Score</div>
            <div class="score-status">{{ interpretationLabel }}</div>
          </div>
        </div>
        <div class="score-bar-large">
          <div 
            class="score-fill-large" 
            :style="{ width: (insight.score / 5 * 100) + '%' }"
          ></div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="modal-body">
        <!-- Description Section -->
        <section class="detail-section">
          <h3>What does this measure?</h3>
          <p>{{ insight.description }}</p>
        </section>

        <!-- Why It Matters -->
        <section class="detail-section">
          <h3>Why is this important?</h3>
          <p>{{ insight.why }}</p>
        </section>

        <!-- Contributing Questions -->
        <section class="detail-section">
          <h3>Questions Used</h3>
          <div class="questions-list">
            <div 
              v-for="question in insight.questions" 
              :key="question.id"
              class="question-item"
            >
              <span class="question-id">{{ question.id }}</span>
              <span class="question-text">{{ question.text }}</span>
            </div>
          </div>
        </section>

        <!-- Interpretation Guide -->
        <section class="detail-section">
          <h3>Score Interpretation</h3>
          <div class="interpretation-grid">
            <div 
              v-for="(text, level) in insight.interpretation" 
              :key="level"
              :class="['interpretation-item', level, { active: level === insight.interpretation }]"
            >
              <div class="interpretation-header">
                <span class="level-badge">{{ getLevelLabel(level) }}</span>
                <span class="level-range">{{ getLevelRange(level) }}</span>
              </div>
              <p>{{ text }}</p>
            </div>
          </div>
        </section>

        <!-- Current Status & Recommendations -->
        <section class="detail-section recommendations">
          <h3>Your Current Status</h3>
          <div :class="['status-box', insight.interpretation]">
            <p class="status-text">{{ insight.interpretationText }}</p>
          </div>
          
          <h4>Recommended Actions</h4>
          <ul class="recommendations-list">
            <li v-for="(action, index) in getRecommendedActions(insight.interpretation)" :key="index">
              {{ action }}
            </li>
          </ul>
        </section>

        <!-- Response Statistics -->
        <section class="detail-section">
          <h3>Response Statistics</h3>
          <div class="stats-grid">
            <div class="stat-box">
              <div class="stat-number">{{ insight.responseCount }}</div>
              <div class="stat-label">Total Responses</div>
            </div>
            <div class="stat-box">
              <div class="stat-number">{{ insight.questions.length }}</div>
              <div class="stat-label">Questions Analyzed</div>
            </div>
            <div class="stat-box">
              <div class="stat-number">{{ getPercentile(insight.score) }}%</div>
              <div class="stat-label">Performance Level</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  insight: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])

// Computed properties
const interpretationLabel = computed(() => {
  const labels = {
    excellent: 'Excellent Performance',
    good: 'Good Performance',
    average: 'Average Performance',
    poor: 'Needs Attention'
  }
  return labels[props.insight.interpretation] || 'Unknown'
})

// Helper functions
function getLevelLabel(level) {
  const labels = {
    excellent: 'Excellent',
    good: 'Good',
    average: 'Average',
    poor: 'Poor'
  }
  return labels[level] || level
}

function getLevelRange(level) {
  const ranges = {
    excellent: '4.0 - 5.0',
    good: '3.0 - 3.9',
    average: '2.0 - 2.9',
    poor: '1.0 - 1.9'
  }
  return ranges[level] || ''
}

function getPercentile(score) {
  // Simple percentile calculation based on score
  return Math.round((score / 5) * 100)
}

function getRecommendedActions(interpretation) {
  const actions = {
    excellent: [
      'Continue current practices to maintain high performance',
      'Share successful strategies with other students',
      'Consider mentoring peers who need support',
      'Document what\'s working well for future reference'
    ],
    good: [
      'Identify specific areas within this category for improvement',
      'Set goals to move towards excellent performance',
      'Learn from top performers in your cohort',
      'Maintain consistency in current practices'
    ],
    average: [
      'Prioritize improvement in this area',
      'Seek additional resources and support',
      'Create an action plan with specific goals',
      'Monitor progress regularly'
    ],
    poor: [
      'This area requires immediate attention',
      'Schedule meetings with support staff',
      'Implement targeted interventions',
      'Consider intensive support programs',
      'Track progress weekly'
    ]
  }
  return actions[interpretation] || []
}
</script>

<style scoped>
.insight-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-md);
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.insight-modal-content {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

/* Header */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-xl);
  border-bottom: 2px solid var(--border-color);
  position: sticky;
  top: 0;
  background: var(--card-bg);
  z-index: 10;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.modal-icon {
  font-size: 2.5rem;
}

.modal-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.modal-close {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
}

.modal-close:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: rotate(90deg);
}

/* Score Summary */
.score-summary {
  padding: var(--spacing-xl);
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-color);
}

.score-display {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.score-number {
  font-size: 3.5rem;
  font-weight: 700;
  color: currentColor;
  line-height: 1;
}

.score-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.score-label {
  font-size: 0.875rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.score-status {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.score-bar-large {
  width: 100%;
  height: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  overflow: hidden;
}

.score-fill-large {
  height: 100%;
  background: currentColor;
  border-radius: 6px;
  transition: width 0.5s ease;
}

/* Color coding */
.score-summary.excellent { color: #10b981; }
.score-summary.good { color: #3b82f6; }
.score-summary.average { color: #f59e0b; }
.score-summary.poor { color: #ef4444; }

/* Modal Body */
.modal-body {
  padding: var(--spacing-xl);
}

.detail-section {
  margin-bottom: var(--spacing-xl);
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
}

.detail-section h4 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.detail-section p {
  font-size: 1rem;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
}

/* Questions List */
.questions-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.question-item {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.question-id {
  font-weight: 600;
  color: var(--accent-primary);
  min-width: 40px;
}

.question-text {
  color: var(--text-secondary);
  line-height: 1.5;
}

/* Interpretation Grid */
.interpretation-grid {
  display: grid;
  gap: var(--spacing-md);
}

.interpretation-item {
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.3s ease;
}

.interpretation-item.active {
  border-color: currentColor;
  background: rgba(255, 255, 255, 0.05);
}

.interpretation-item.excellent { color: #10b981; }
.interpretation-item.good { color: #3b82f6; }
.interpretation-item.average { color: #f59e0b; }
.interpretation-item.poor { color: #ef4444; }

.interpretation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-sm);
}

.level-badge {
  font-weight: 600;
  font-size: 1.1rem;
}

.level-range {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.interpretation-item p {
  font-size: 0.95rem;
  margin: 0;
}

/* Status Box */
.status-box {
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  border: 2px solid currentColor;
  background: rgba(255, 255, 255, 0.02);
  margin-bottom: var(--spacing-lg);
}

.status-box.excellent { color: #10b981; }
.status-box.good { color: #3b82f6; }
.status-box.average { color: #f59e0b; }
.status-box.poor { color: #ef4444; }

.status-text {
  font-size: 1.1rem;
  font-weight: 500;
  margin: 0;
}

/* Recommendations */
.recommendations-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.recommendations-list li {
  position: relative;
  padding-left: 2rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.recommendations-list li::before {
  content: "→";
  position: absolute;
  left: 0;
  color: var(--accent-primary);
  font-weight: bold;
  font-size: 1.2rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-md);
}

.stat-box {
  text-align: center;
  padding: var(--spacing-lg);
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.stat-box .stat-label {
  font-size: 0.875rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Responsive */
@media (max-width: 768px) {
  .insight-modal-content {
    margin: var(--spacing-sm);
  }
  
  .modal-header {
    padding: var(--spacing-lg);
  }
  
  .modal-header h2 {
    font-size: 1.5rem;
  }
  
  .score-number {
    font-size: 2.5rem;
  }
  
  .modal-body {
    padding: var(--spacing-lg);
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* Scrollbar */
.insight-modal-content::-webkit-scrollbar {
  width: 8px;
}

.insight-modal-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.insight-modal-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.insight-modal-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>