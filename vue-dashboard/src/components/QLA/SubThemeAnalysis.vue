<template>
  <div class="subtheme-card card">
    <h5 class="card-title">Sub-theme Analysis</h5>
    <div class="placeholder">
      <p>Sub-theme analysis visualization</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  data: Object
})
</script>

<style scoped>
.subtheme-card {
  padding: var(--spacing-lg);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.placeholder {
  padding: 3rem;
  text-align: center;
  color: var(--text-secondary);
  background: var(--secondary-bg);
  border-radius: var(--radius-sm);
}
</style>