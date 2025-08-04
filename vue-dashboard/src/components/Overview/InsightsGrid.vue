<template>
  <div class="insights-container">
    <!-- Header -->
    <div class="insights-header">
      <h2>
        <span class="icon">💡</span>
        Automated Insights
      </h2>
      <button class="insights-info-btn" @click="showInfoModal = true">
        <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="insights-loading">
      <div class="spinner"></div>
      <p>Analyzing responses and generating insights...</p>
    </div>

    <!-- Insights Grid -->
    <div v-else-if="insights.length > 0" class="insights-grid">
      <InsightCard
        v-for="insight in insights"
        :key="insight.key"
        :insight="insight"
        @click="selectedInsight = insight"
      />
    </div>

    <!-- Empty State -->
    <div v-else class="insights-empty">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <p>No insights available. Ensure you have response data.</p>
    </div>

    <!-- Insight Detail Modal -->
    <InsightDetailModal
      v-if="selectedInsight"
      :insight="selectedInsight"
      @close="selectedInsight = null"
    />

    <!-- Insights Info Modal -->
    <InsightsInfoModal
      v-if="showInfoModal"
      @close="showInfoModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { insightDefinitions, calculateInsightScore, getScoreInterpretation } from '@/config/insights'
import InsightCard from './InsightCard.vue'
import InsightDetailModal from './InsightDetailModal.vue'
import InsightsInfoModal from './InsightsInfoModal.vue'

const props = defineProps({
  responses: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const selectedInsight = ref(null)
const showInfoModal = ref(false)

// Calculate insights from responses
const insights = computed(() => {
  if (!props.responses || props.responses.length === 0) return []
  
  const insightResults = []
  
  // Calculate aggregate scores for all responses
  const aggregateScores = {}
  
  // Initialize aggregates
  Object.keys(insightDefinitions).forEach(key => {
    aggregateScores[key] = { total: 0, count: 0 }
  })
  
  // Process all responses
  props.responses.forEach(response => {
    Object.keys(insightDefinitions).forEach(insightKey => {
      const score = calculateInsightScore(insightKey, response)
      if (score !== null) {
        aggregateScores[insightKey].total += score
        aggregateScores[insightKey].count++
      }
    })
  })
  
  // Calculate average scores and create insight objects
  Object.entries(insightDefinitions).forEach(([key, definition]) => {
    const aggregate = aggregateScores[key]
    if (aggregate.count > 0) {
      const avgScore = aggregate.total / aggregate.count
      const interpretation = getScoreInterpretation(avgScore)
      
      insightResults.push({
        key,
        ...definition,
        score: avgScore,
        interpretation,
        interpretationText: definition.interpretation[interpretation],
        responseCount: aggregate.count
      })
    }
  })
  
  // Sort by score (lowest first to highlight areas needing attention)
  return insightResults.sort((a, b) => a.score - b.score)
})
</script>

<style scoped>
.insights-container {
  margin-top: var(--spacing-xl);
}

.insights-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 2px solid var(--border-color);
}

.insights-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin: 0;
}

.insights-header .icon {
  font-size: 1.75rem;
}

.insights-info-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.insights-info-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: var(--text-primary);
  transform: scale(1.1);
}

/* Loading State */
.insights-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.spinner {
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-md);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.insights-loading p {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

/* Insights Grid */
.insights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-lg);
}

/* Empty State */
.insights-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
}

.insights-empty svg {
  margin-bottom: var(--spacing-md);
  opacity: 0.5;
}

.insights-empty p {
  font-size: 1.1rem;
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .insights-grid {
    grid-template-columns: 1fr;
  }
  
  .insights-header h2 {
    font-size: 1.25rem;
  }
}
</style>