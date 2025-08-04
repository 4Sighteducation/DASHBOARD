<template>
  <div 
    :class="['insight-card', interpretationClass]"
    @click="$emit('click', insight)"
  >
    <!-- Icon and Title -->
    <div class="insight-header">
      <span class="insight-icon">{{ insight.icon }}</span>
      <h3>{{ insight.title }}</h3>
    </div>

    <!-- Score Display -->
    <div class="insight-score">
      <div class="score-value">{{ formattedScore }}</div>
      <div class="score-label">Average Score</div>
    </div>

    <!-- Progress Bar -->
    <div class="score-bar">
      <div 
        class="score-fill" 
        :style="{ width: scorePercentage + '%' }"
      ></div>
    </div>

    <!-- Interpretation -->
    <div class="insight-interpretation">
      <p>{{ insight.interpretationText }}</p>
    </div>

    <!-- Quick Stats -->
    <div class="insight-stats">
      <div class="stat">
        <span class="stat-label">Questions</span>
        <span class="stat-value">{{ insight.questions.length }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Responses</span>
        <span class="stat-value">{{ insight.responseCount }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Status</span>
        <span :class="['stat-value', 'status', interpretationClass]">
          {{ interpretationLabel }}
        </span>
      </div>
    </div>

    <!-- Action Hint -->
    <div class="insight-action">
      <span>Click for detailed analysis →</span>
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

const emit = defineEmits(['click'])

// Computed properties
const formattedScore = computed(() => {
  return props.insight.score.toFixed(2)
})

const scorePercentage = computed(() => {
  return (props.insight.score / 5) * 100
})

const interpretationClass = computed(() => {
  return props.insight.interpretation
})

const interpretationLabel = computed(() => {
  const labels = {
    excellent: 'Excellent',
    good: 'Good',
    average: 'Average',
    poor: 'Needs Attention'
  }
  return labels[props.insight.interpretation] || 'Unknown'
})
</script>

<style scoped>
.insight-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  border: 2px solid var(--border-color);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.insight-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: currentColor;
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.insight-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border-color: currentColor;
}

.insight-card:hover::before {
  transform: scaleX(1);
}

/* Color coding */
.insight-card.excellent {
  color: #10b981;
}

.insight-card.good {
  color: #3b82f6;
}

.insight-card.average {
  color: #f59e0b;
}

.insight-card.poor {
  color: #ef4444;
}

/* Header */
.insight-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.insight-icon {
  font-size: 2rem;
}

.insight-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

/* Score Display */
.insight-score {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.score-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: currentColor;
  line-height: 1;
}

.score-label {
  font-size: 0.875rem;
  color: var(--text-muted);
}

/* Progress Bar */
.score-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: var(--spacing-md);
}

.score-fill {
  height: 100%;
  background: currentColor;
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* Interpretation */
.insight-interpretation {
  margin-bottom: var(--spacing-md);
}

.insight-interpretation p {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

/* Quick Stats */
.insight-stats {
  display: flex;
  gap: var(--spacing-lg);
  padding: var(--spacing-sm) 0;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  margin-bottom: var(--spacing-md);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.stat-value.status {
  color: currentColor;
}

/* Action Hint */
.insight-action {
  text-align: center;
  font-size: 0.875rem;
  color: var(--text-muted);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.insight-card:hover .insight-action {
  opacity: 1;
}

/* Responsive */
@media (max-width: 768px) {
  .insight-card {
    padding: var(--spacing-md);
  }
  
  .score-value {
    font-size: 2rem;
  }
  
  .insight-stats {
    gap: var(--spacing-md);
  }
}
</style>