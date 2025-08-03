<template>
  <div class="overview-section">
    <!-- Loading State -->
    <div v-if="loading" class="section-loading">
      <div class="spinner"></div>
      <p>Loading overview data...</p>
    </div>

    <!-- Content -->
    <div v-else class="overview-content">
      <!-- Statistics Cards -->
      <div class="statistics-grid">
        <StatCard 
          v-for="stat in statistics" 
          :key="stat.id"
          :title="stat.title"
          :value="stat.value"
          :change="stat.change"
          :icon="stat.icon"
          :color="stat.color"
        />
      </div>

      <!-- VESPA Scores -->
      <div class="charts-grid">
        <div class="chart-card">
          <h3 class="chart-title">VESPA Scores Distribution</h3>
          <VespaRadarChart :data="vespaScores" />
        </div>
        
        <div class="chart-card">
          <h3 class="chart-title">Score Comparison</h3>
          <VespaBarChart :data="vespaComparison" />
        </div>
      </div>

      <!-- ERI Gauge -->
      <div class="eri-section">
        <ERIGauge 
          :value="eriScore" 
          :nationalAverage="nationalERI"
          :trend="eriTrend"
        />
      </div>

      <!-- Year Group Performance -->
      <div class="chart-card full-width">
        <h3 class="chart-title">Performance by Year Group</h3>
        <YearGroupChart :data="yearGroupData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatCard from './StatCard.vue'
import VespaRadarChart from './VespaRadarChart.vue'
import VespaBarChart from './VespaBarChart.vue'
import ERIGauge from './ERIGauge.vue'
import YearGroupChart from './YearGroupChart.vue'

const props = defineProps({
  data: Object,
  filters: Object,
  loading: Boolean
})

// Computed properties for formatted data
const statistics = computed(() => {
  if (!props.data?.statistics) return []
  
  const stats = props.data.statistics
  return [
    {
      id: 'total-students',
      title: 'Total Students',
      value: stats.totalStudents || 0,
      change: null,
      icon: 'users',
      color: 'primary'
    },
    {
      id: 'avg-eri',
      title: 'Average ERI',
      value: stats.averageERI ? stats.averageERI.toFixed(1) : '0.0',
      change: stats.eriChange || null,
      icon: 'trending-up',
      color: 'success'
    },
    {
      id: 'completion-rate',
      title: 'Completion Rate',
      value: stats.completionRate ? `${stats.completionRate}%` : '0%',
      change: null,
      icon: 'check-circle',
      color: 'info'
    },
    {
      id: 'avg-score',
      title: 'Average Score',
      value: stats.averageScore ? stats.averageScore.toFixed(1) : '0.0',
      change: stats.scoreChange || null,
      icon: 'chart-bar',
      color: 'warning'
    }
  ]
})

const vespaScores = computed(() => {
  if (!props.data?.statistics?.vespaScores) return null
  return props.data.statistics.vespaScores
})

const vespaComparison = computed(() => {
  if (!props.data?.statistics?.comparison) return null
  return props.data.statistics.comparison
})

const eriScore = computed(() => {
  return props.data?.statistics?.averageERI || 0
})

const nationalERI = computed(() => {
  return props.data?.statistics?.nationalERI || 0
})

const eriTrend = computed(() => {
  return props.data?.statistics?.eriTrend || 'stable'
})

const yearGroupData = computed(() => {
  if (!props.data?.statistics?.yearGroupPerformance) return null
  return props.data.statistics.yearGroupPerformance
})
</script>

<style scoped>
.overview-section {
  padding: var(--spacing-lg) 0;
}

.section-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.overview-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-md);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--spacing-lg);
}

.chart-card {
  background: var(--card-bg);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  border: 1px solid var(--border-color);
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.eri-section {
  display: flex;
  justify-content: center;
  padding: var(--spacing-lg) 0;
}

@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}</style>