<template>
  <div class="chart-placeholder">
    <p>Bar Chart Component</p>
    <pre>{{ data }}</pre>
  </div>
</template>

<script setup>
defineProps({
  data: Object
})
</script>

<style scoped>
.chart-placeholder {
  padding: 2rem;
  background: var(--secondary-bg);
  border-radius: var(--radius-sm);
  text-align: center;
  color: var(--text-secondary);
}

pre {
  font-size: 0.75rem;
  margin-top: 1rem;
  text-align: left;
  overflow: auto;
}
</style>