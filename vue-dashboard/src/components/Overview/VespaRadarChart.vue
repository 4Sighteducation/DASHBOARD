<template>
  <div class="chart-container">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  data: Object
})

const chartCanvas = ref(null)
let chartInstance = null

const vespaColors = {
  vision: '#ff8f00',
  effort: '#86b4f0',
  systems: '#72cb44',
  practice: '#7f31a4',
  attitude: '#f032e6'
}

function createChart() {
  if (!props.data || !chartCanvas.value) return
  
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  const ctx = chartCanvas.value.getContext('2d')
  
  chartInstance = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude'],
      datasets: [{
        label: 'School Average',
        data: [
          props.data.vision || 0,
          props.data.effort || 0,
          props.data.systems || 0,
          props.data.practice || 0,
          props.data.attitude || 0
        ],
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderColor: '#3b82f6',
        borderWidth: 2,
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#3b82f6'
      }, {
        label: 'National Average',
        data: [
          props.data.nationalVision || 0,
          props.data.nationalEffort || 0,
          props.data.nationalSystems || 0,
          props.data.nationalPractice || 0,
          props.data.nationalAttitude || 0
        ],
        backgroundColor: 'rgba(107, 114, 128, 0.1)',
        borderColor: '#6b7280',
        borderWidth: 2,
        pointBackgroundColor: '#6b7280',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#6b7280'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#a8b2d1',
            padding: 20
          }
        }
      },
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          ticks: {
            color: '#64748b',
            backdropColor: 'transparent'
          },
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          },
          pointLabels: {
            color: '#a8b2d1',
            font: {
              size: 12,
              weight: '500'
            }
          }
        }
      }
    }
  })
}

onMounted(() => {
  createChart()
})

watch(() => props.data, () => {
  createChart()
}, { deep: true })
</script>

<style scoped>
.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
}
</style>