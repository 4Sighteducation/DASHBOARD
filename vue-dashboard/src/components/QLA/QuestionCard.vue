<template>
  <div 
    :class="['question-card', scoreClass]"
    @click="$emit('click', question)"
  >
    <!-- Rank Badge -->
    <div class="question-rank">{{ rank }}</div>
    
    <!-- Question Text -->
    <div class="question-text">{{ question.text || question.question_text }}</div>
    
    <!-- Score Section -->
    <div class="score-section">
      <div class="score-indicator">{{ formattedScore }}</div>
      <div class="mini-chart-container">
        <canvas :ref="chartRef"></canvas>
      </div>
    </div>
    
    <!-- Statistics Details -->
    <div class="stats-details">
      <div class="stat-item">
        <span class="stat-label">Responses</span>
        <span class="stat-value">{{ statistics.count || question.n || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Std Dev</span>
        <span class="stat-value">{{ formattedStdDev }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Mode</span>
        <span class="stat-value">{{ statistics.mode || estimatedMode }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  question: {
    type: Object,
    required: true
  },
  rank: {
    type: Number,
    required: true
  },
  type: {
    type: String,
    default: 'top' // 'top' or 'bottom'
  },
  statistics: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['click'])

// Chart reference
const chartRef = ref(null)
let chartInstance = null

// Computed properties
const score = computed(() => {
  return props.question.score || props.question.mean_score || props.question.avg_score || 0
})

const formattedScore = computed(() => {
  return score.value.toFixed(2)
})

const scoreClass = computed(() => {
  if (score.value >= 4) return 'excellent'
  if (score.value >= 3) return 'good'
  if (score.value >= 2) return 'average'
  return 'poor'
})

const formattedStdDev = computed(() => {
  const stdDev = props.statistics.stdDev || props.question.std_dev || estimatedStdDev.value
  return stdDev.toFixed(2)
})

// Estimate statistics if not provided
const estimatedStdDev = computed(() => {
  // Estimate standard deviation based on score
  if (score.value >= 4.5 || score.value <= 1.5) return 0.65
  if (score.value >= 4 || score.value <= 2) return 0.75
  return 0.95
})

const estimatedMode = computed(() => {
  return Math.round(score.value)
})

const distribution = computed(() => {
  // Use provided distribution or estimate it
  if (props.statistics.distribution && props.statistics.distribution.some(v => v > 0)) {
    return props.statistics.distribution
  }
  
  return estimateDistribution(score.value, props.question.n || props.statistics.count || 100)
})

// Functions
function estimateDistribution(avgScore, responseCount) {
  const dist = [0, 0, 0, 0, 0]
  const variance = 0.8
  
  for (let i = 1; i <= 5; i++) {
    const distance = Math.abs(i - avgScore)
    const probability = Math.exp(-(distance * distance) / (2 * variance))
    dist[i - 1] = Math.round(probability * responseCount * 0.4)
  }
  
  // Normalize to match response count
  const total = dist.reduce((sum, val) => sum + val, 0)
  if (total > 0) {
    const scaleFactor = responseCount / total
    for (let i = 0; i < 5; i++) {
      dist[i] = Math.round(dist[i] * scaleFactor)
    }
  }
  
  return dist
}

function createMiniChart() {
  if (!chartRef.value) return
  
  const ctx = chartRef.value.getContext('2d')
  
  // Destroy existing chart if any
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  // Color based on performance
  const colors = {
    excellent: '#10b981',
    good: '#3b82f6',
    average: '#f59e0b',
    poor: '#ef4444'
  }
  
  const color = colors[scoreClass.value] || '#64748b'
  
  // Create chart
  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['1', '2', '3', '4', '5'],
      datasets: [{
        data: distribution.value,
        backgroundColor: color + 'CC',
        borderColor: color,
        borderWidth: 1.5,
        borderRadius: 3,
        barPercentage: 0.8,
        categoryPercentage: 0.9
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          enabled: false
        }
      },
      scales: {
        y: {
          display: false,
          beginAtZero: true
        },
        x: {
          display: true,
          grid: {
            display: false
          },
          ticks: {
            color: 'rgba(255, 255, 255, 0.5)',
            font: {
              size: 9
            }
          }
        }
      },
      layout: {
        padding: {
          top: 5,
          bottom: 0,
          left: 2,
          right: 2
        }
      }
    }
  })
}

// Lifecycle
onMounted(async () => {
  await nextTick()
  createMiniChart()
})
</script>

<style scoped>
.question-card {
  background: var(--secondary-bg);
  border-radius: 12px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid var(--border-color);
  position: relative;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.question-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: currentColor;
  transition: width 0.3s ease;
}

.question-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border-color: currentColor;
}

.question-card:hover::before {
  width: 6px;
}

/* Rank Badge */
.question-rank {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  color: var(--text-secondary);
}

/* Question Text */
.question-text {
  font-size: 0.95rem;
  color: var(--text-primary);
  margin-bottom: 1rem;
  padding-right: 3rem;
  line-height: 1.5;
  min-height: 3em;
}

/* Score Section */
.score-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.score-indicator {
  font-size: 2rem;
  font-weight: 700;
  color: currentColor;
}

.mini-chart-container {
  flex: 1;
  height: 60px;
  min-height: 60px;
  max-width: 120px;
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  padding: 4px;
}

.mini-chart-container canvas {
  width: 100% !important;
  height: 100% !important;
  display: block;
}

/* Statistics Details */
.stats-details {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 0.8rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.stat-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.2rem;
  opacity: 0.8;
  color: var(--text-muted);
}

.stat-value {
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 0.95rem;
}

/* Color coding for score ranges */
.question-card.excellent {
  color: #10b981;
}

.question-card.good {
  color: #3b82f6;
}

.question-card.average {
  color: #f59e0b;
}

.question-card.poor {
  color: #ef4444;
}

/* Responsive */
@media (max-width: 768px) {
  .question-card {
    padding: 1.25rem;
  }
  
  .question-text {
    font-size: 0.9rem;
    padding-right: 2.5rem;
  }
  
  .score-indicator {
    font-size: 1.75rem;
  }
  
  .stats-details {
    gap: 1rem;
  }
  
  .stat-value {
    font-size: 0.85rem;
  }
}
</style>