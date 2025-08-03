<template>
  <div :class="['stat-card', `stat-card-${color}`]">
    <div class="stat-header">
      <div class="stat-icon">
        <component :is="iconComponent" />
      </div>
      <div v-if="change" :class="['stat-change', changeClass]">
        <svg v-if="change > 0" class="change-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
        </svg>
        <svg v-else class="change-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
        {{ Math.abs(change) }}%
      </div>
    </div>
    
    <div class="stat-value">{{ value }}</div>
    <div class="stat-title">{{ title }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  value: [String, Number],
  change: Number,
  icon: String,
  color: {
    type: String,
    default: 'primary'
  }
})

const changeClass = computed(() => {
  if (!props.change) return ''
  return props.change > 0 ? 'positive' : 'negative'
})

// Simple icon components (you can replace with a proper icon library)
const iconComponent = computed(() => ({
  template: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    ${getIconPath(props.icon)}
  </svg>`
}))

function getIconPath(icon) {
  const icons = {
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>',
    'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline>',
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>',
    'chart-bar': '<rect x="12" y="2" width="9" height="20"></rect><rect x="3" y="8" width="9" height="14"></rect>'
  }
  return icons[icon] || icons['chart-bar']
}
</script>

<style scoped>
.stat-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--secondary-bg);
  color: var(--text-secondary);
}

.stat-card-primary .stat-icon {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.stat-card-success .stat-icon {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.stat-card-info .stat-icon {
  background: rgba(134, 180, 240, 0.1);
  color: #86b4f0;
}

.stat-card-warning .stat-icon {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.stat-change {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 0.875rem;
  font-weight: 500;
}

.stat-change.positive {
  color: #10b981;
}

.stat-change.negative {
  color: #ef4444;
}

.change-icon {
  width: 16px;
  height: 16px;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.stat-title {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
}</style>