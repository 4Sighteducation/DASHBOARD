<template>
  <div class="comparative-card card">
    <h5 class="card-title">Comparative Analysis</h5>
    <div class="comparison-content">
      <div class="comparison-item">
        <span class="label">School Average:</span>
        <span class="value">{{ schoolData?.average || 'N/A' }}</span>
      </div>
      <div class="comparison-item">
        <span class="label">National Average:</span>
        <span class="value">{{ nationalData?.average || 'N/A' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  schoolData: Object,
  nationalData: Object
})
</script>

<style scoped>
.comparative-card {
  padding: var(--spacing-lg);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.comparison-content {
  display: flex;
  gap: var(--spacing-lg);
}

.comparison-item {
  flex: 1;
  padding: var(--spacing-md);
  background: var(--secondary-bg);
  border-radius: var(--radius-sm);
  text-align: center;
}

.label {
  display: block;
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.value {
  display: block;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
}
</style>