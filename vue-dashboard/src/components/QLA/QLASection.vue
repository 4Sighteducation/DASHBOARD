<template>
  <div class="qla-section">
    <!-- Loading State -->
    <div v-if="loading" class="section-loading">
      <div class="spinner"></div>
      <p>Loading question analysis...</p>
    </div>

    <!-- Content -->
    <div v-else class="qla-content">
      <!-- Top/Bottom Questions Display -->
      <TopBottomQuestions
        :top-questions="topQuestions"
        :bottom-questions="bottomQuestions"
        :loading="loading"
        @question-select="handleQuestionSelect"
      />

      <!-- Question Selection -->
      <div class="qla-controls">
        <select 
          v-model="selectedQuestion"
          class="form-select"
        >
          <option value="">Select a question for detailed analysis...</option>
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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import TopBottomQuestions from './TopBottomQuestions.vue'
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

// Top and Bottom Questions
const topQuestions = computed(() => {
  if (!props.data?.qlaData) return []
  
  // Get top questions from API or calculate from available data
  if (props.data.qlaData.topQuestions) {
    return props.data.qlaData.topQuestions
  }
  
  // Calculate from questions if not provided
  const sortedQuestions = [...questions.value]
    .filter(q => q.mean_score || q.score)
    .sort((a, b) => (b.mean_score || b.score) - (a.mean_score || a.score))
  
  return sortedQuestions.slice(0, 5)
})

const bottomQuestions = computed(() => {
  if (!props.data?.qlaData) return []
  
  // Get bottom questions from API or calculate from available data
  if (props.data.qlaData.bottomQuestions) {
    return props.data.qlaData.bottomQuestions
  }
  
  // Calculate from questions if not provided
  const sortedQuestions = [...questions.value]
    .filter(q => q.mean_score || q.score)
    .sort((a, b) => (a.mean_score || a.score) - (b.mean_score || b.score))
  
  return sortedQuestions.slice(0, 5)
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

// Methods
function handleQuestionSelect(question) {
  selectedQuestion.value = question.id
  // Scroll to analysis section
  nextTick(() => {
    const analysisElement = document.querySelector('.question-analysis')
    if (analysisElement) {
      analysisElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

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