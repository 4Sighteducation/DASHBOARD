<template>
  <div class="qla-top-bottom-container">
    <!-- Top Questions Section -->
    <div class="qla-questions-section top-questions">
      <h3>
        <div class="title-content">
          <span class="icon">🏆</span> Top Statement Responses
        </div>
        <button class="qla-info-btn" @click="showInfoModal = true">
          <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
        </button>
      </h3>
      
      <div class="question-cards" v-if="!loading && topQuestions.length > 0">
        <QuestionCard
          v-for="(question, index) in topQuestions"
          :key="question.id"
          :question="question"
          :rank="index + 1"
          :type="'top'"
          @click="$emit('question-select', question)"
        />
      </div>
      
      <div v-else-if="loading" class="qla-loading">
        <div class="spinner"></div>
        <p>Loading question analysis...</p>
      </div>
      
      <div v-else class="empty-state">
        <p>No top questions available</p>
      </div>
    </div>

    <!-- Bottom Questions Section -->
    <div class="qla-questions-section bottom-questions">
      <h3>
        <div class="title-content">
          <span class="icon">⚠️</span> Responses Needing Attention
        </div>
      </h3>
      
      <div class="question-cards" v-if="!loading && bottomQuestions.length > 0">
        <QuestionCard
          v-for="(question, index) in bottomQuestions"
          :key="question.id"
          :question="question"
          :rank="index + 1"
          :type="'bottom'"
          @click="$emit('question-select', question)"
        />
      </div>
      
      <div v-else-if="loading" class="qla-loading">
        <div class="spinner"></div>
        <p>Loading question analysis...</p>
      </div>
      
      <div v-else class="empty-state">
        <p>No questions needing attention</p>
      </div>
    </div>

    <!-- Info Modal -->
    <QLAInfoModal v-if="showInfoModal" @close="showInfoModal = false" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import QuestionCard from './QuestionCard.vue'
import QLAInfoModal from './QLAInfoModal.vue'

const props = defineProps({
  topQuestions: {
    type: Array,
    default: () => []
  },
  bottomQuestions: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['question-select'])
const showInfoModal = ref(false)
</script>

<style scoped>
.qla-top-bottom-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: var(--spacing-xl);
  margin-top: var(--spacing-lg);
}

.qla-questions-section {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
  transition: all 0.3s ease;
}

.qla-questions-section:hover {
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.qla-questions-section h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-primary);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.title-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.icon {
  font-size: 1.5rem;
}

.qla-info-btn {
  width: 32px;
  height: 32px;
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

.qla-info-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: var(--text-primary);
  transform: scale(1.1);
}

/* Top Questions Styling */
.top-questions {
  background: linear-gradient(135deg, var(--card-bg) 0%, rgba(16, 185, 129, 0.05) 100%);
}

.top-questions h3 {
  color: #10b981;
}

/* Bottom Questions Styling */
.bottom-questions {
  background: linear-gradient(135deg, var(--card-bg) 0%, rgba(239, 68, 68, 0.05) 100%);
}

.bottom-questions h3 {
  color: #ef4444;
}

/* Question Cards Container */
.question-cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  max-height: 600px;
  overflow-y: auto;
  padding-right: var(--spacing-sm);
  margin-right: calc(var(--spacing-sm) * -1);
}

/* Custom Scrollbar */
.question-cards::-webkit-scrollbar {
  width: 6px;
}

.question-cards::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.question-cards::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.question-cards::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Loading State */
.qla-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--text-secondary);
}

.spinner {
  width: 40px;
  height: 40px;
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

/* Empty State */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--text-muted);
  font-style: italic;
}

/* Responsive Design */
@media (max-width: 1200px) {
  .qla-top-bottom-container {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .qla-questions-section {
    padding: var(--spacing-md);
  }
  
  .qla-questions-section h3 {
    font-size: 1.1rem;
  }
  
  .question-cards {
    max-height: 400px;
  }
}
</style>