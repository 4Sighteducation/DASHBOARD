<template>
  <div class="insights-section">
    <!-- Loading State -->
    <div v-if="loading" class="section-loading">
      <div class="spinner"></div>
      <p>Loading student insights...</p>
    </div>

    <!-- Content -->
    <div v-else class="insights-content">
      <!-- Word Cloud -->
      <div class="card">
        <h3 class="card-title">Student Comment Word Cloud</h3>
        <WordCloud :data="wordCloudData" />
      </div>
      
      <!-- Comment Insights Grid -->
      <div class="insights-grid">
        <div class="insight-card card">
          <h4 class="insight-title">Positive Themes</h4>
          <ul class="themes-list">
            <li v-for="theme in positiveThemes" :key="theme.id" class="theme-item positive">
              <span class="theme-name">{{ theme.name }}</span>
              <span class="theme-count">{{ theme.count }}</span>
            </li>
          </ul>
        </div>
        
        <div class="insight-card card">
          <h4 class="insight-title">Areas for Improvement</h4>
          <ul class="themes-list">
            <li v-for="theme in improvementThemes" :key="theme.id" class="theme-item improvement">
              <span class="theme-name">{{ theme.name }}</span>
              <span class="theme-count">{{ theme.count }}</span>
            </li>
          </ul>
        </div>
      </div>
      
      <!-- Sample Comments -->
      <div class="card">
        <h4 class="card-title">Sample Student Comments</h4>
        <div class="comments-list">
          <div v-for="comment in sampleComments" :key="comment.id" class="comment-item">
            <p class="comment-text">"{{ comment.text }}"</p>
            <div class="comment-meta">
              <span>{{ comment.yearGroup }}</span>
              <span>{{ comment.date }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import WordCloud from './WordCloud.vue'

const props = defineProps({
  data: Object,
  filters: Object,
  loading: Boolean
})

const wordCloudData = computed(() => {
  return props.data?.wordCloudData || null
})

const positiveThemes = computed(() => {
  return props.data?.commentInsights?.positive || []
})

const improvementThemes = computed(() => {
  return props.data?.commentInsights?.improvement || []
})

const sampleComments = computed(() => {
  return props.data?.commentInsights?.samples || []
})
</script>

<style scoped>
.insights-section {
  padding: var(--spacing-lg) 0;
}

.section-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.insights-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.insight-card {
  padding: var(--spacing-lg);
}

.insight-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.themes-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.theme-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
  border-radius: var(--radius-sm);
  background: var(--secondary-bg);
}

.theme-item.positive {
  border-left: 3px solid var(--accent-success);
}

.theme-item.improvement {
  border-left: 3px solid var(--accent-warning);
}

.theme-name {
  font-weight: 500;
  color: var(--text-primary);
}

.theme-count {
  font-size: 0.875rem;
  color: var(--text-secondary);
  background: var(--card-bg);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.comment-item {
  padding: var(--spacing-md);
  background: var(--secondary-bg);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--accent-primary);
}

.comment-text {
  font-style: italic;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.comment-meta {
  display: flex;
  gap: var(--spacing-md);
  font-size: 0.875rem;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .insights-grid {
    grid-template-columns: 1fr;
  }
}</style>