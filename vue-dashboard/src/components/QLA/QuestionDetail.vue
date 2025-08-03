<template>
  <div class="question-detail card">
    <h4 class="question-text">{{ question?.text }}</h4>
    <div class="question-meta">
      <span class="meta-item">
        <strong>Sub-theme:</strong> {{ question?.subTheme }}
      </span>
      <span class="meta-item">
        <strong>VESPA Area:</strong> {{ question?.vespaArea }}
      </span>
      <span class="meta-item">
        <strong>Responses:</strong> {{ responses?.length || 0 }}
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  question: Object,
  responses: Array
})
</script>

<style scoped>
.question-detail {
  padding: var(--spacing-lg);
}

.question-text {
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
}

.question-meta {
  display: flex;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.meta-item {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.meta-item strong {
  color: var(--text-primary);
  font-weight: 500;
}
</style>