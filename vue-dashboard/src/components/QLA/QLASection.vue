<template>
  <div class="qla-section">
    <!-- Loading State -->
    <div v-if="loading" class="section-loading">
      <div class="spinner"></div>
      <p>Loading question analysis...</p>
    </div>

    <!-- Content -->
    <div v-else class="qla-content">
      <!-- Question Selection -->
      <div class="qla-controls">
        <select 
          v-model="selectedQuestion"
          class="form-select"
        >
          <option value="">Select a question...</option>
          <option 
            v-for="question in questions" 
            :key="question.id"
            :value="question.id"
          >
            {{ question.text }}
          </option>
        </select>
      </div>

      <!-- Question Analysis -->
      <div v-if="selectedQuestion" class="question-analysis">
        <QuestionDetail 
          :question="currentQuestion"
          :responses="currentResponses"
        />
        
        <div class="analysis-grid">
          <ResponseDistribution 
            :distribution="responseDistribution"
          />
          
          <SubThemeAnalysis 
            :data="subThemeData"
          />
        </div>
        
        <ComparativeAnalysis 
          :schoolData="schoolPerformance"
          :nationalData="nationalPerformance"
        />
      </div>
      
      <!-- Empty State -->
      <div v-else class="empty-state">
        <svg class="empty-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
        <p>Select a question to view detailed analysis</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import QuestionDetail from './QuestionDetail.vue'
import ResponseDistribution from './ResponseDistribution.vue'
import SubThemeAnalysis from './SubThemeAnalysis.vue'
import ComparativeAnalysis from './ComparativeAnalysis.vue'

const props = defineProps({
  data: Object,
  filters: Object,
  loading: Boolean
})

const selectedQuestion = ref('')

const questions = computed(() => {
  return props.data?.qlaData?.questions || []
})

const currentQuestion = computed(() => {
  if (!selectedQuestion.value || !props.data?.qlaData) return null
  return props.data.qlaData.questions.find(q => q.id === selectedQuestion.value)
})

const currentResponses = computed(() => {
  if (!selectedQuestion.value || !props.data?.qlaData) return []
  return props.data.qlaData.responses[selectedQuestion.value] || []
})

const responseDistribution = computed(() => {
  if (!currentResponses.value.length) return null
  
  // Calculate distribution from responses
  const distribution = {}
  currentResponses.value.forEach(response => {
    distribution[response.score] = (distribution[response.score] || 0) + 1
  })
  
  return distribution
})

const subThemeData = computed(() => {
  if (!currentQuestion.value) return null
  return props.data?.qlaData?.subThemes[selectedQuestion.value] || null
})

const schoolPerformance = computed(() => {
  if (!selectedQuestion.value) return null
  return props.data?.qlaData?.schoolPerformance[selectedQuestion.value] || null
})

const nationalPerformance = computed(() => {
  if (!selectedQuestion.value) return null
  return props.data?.qlaData?.nationalPerformance[selectedQuestion.value] || null
})

// Auto-select first question if available
watch(() => questions.value, (newQuestions) => {
  if (newQuestions.length > 0 && !selectedQuestion.value) {
    selectedQuestion.value = newQuestions[0].id
  }
}, { immediate: true })
</script>

<style scoped>
.qla-section {
  padding: var(--spacing-lg) 0;
}

.section-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.qla-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.qla-controls {
  background: var(--card-bg);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  border: 1px solid var(--border-color);
}

.form-select {
  width: 100%;
  max-width: 600px;
}

.question-analysis {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--spacing-lg);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: var(--spacing-xl);
  background: var(--card-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.empty-icon {
  color: var(--text-muted);
  margin-bottom: var(--spacing-md);
}

.empty-state p {
  color: var(--text-secondary);
  font-size: 1.125rem;
}

@media (max-width: 768px) {
  .analysis-grid {
    grid-template-columns: 1fr;
  }
}</style>