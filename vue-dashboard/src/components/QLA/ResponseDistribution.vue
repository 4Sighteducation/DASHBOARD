<template>
  <div class="distribution-card card">
    <h5 class="card-title">Response Distribution</h5>
    <div class="distribution-chart">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  distribution: Object
})

const chartCanvas = ref(null)
let chartInstance = null

function createChart() {
  if (!props.distribution || !chartCanvas.value) return
  
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  const labels = Object.keys(props.distribution).sort()
  const data = labels.map(label => props.distribution[label])
  
  const ctx = chartCanvas.value.getContext('2d')
  
  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: [
          '#ef4444',
          '#f59e0b',
          '#fbbf24',
          '#84cc16',
          '#10b981'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#a8b2d1'
          }
        }
      }
    }
  })
}

onMounted(() => {
  createChart()
})

watch(() => props.distribution, () => {
  createChart()
}, { deep: true })
</script>

<style scoped>
.distribution-card {
  padding: var(--spacing-lg);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.distribution-chart {
  height: 250px;
}</style>