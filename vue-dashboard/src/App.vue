<template>
  <div id="vue-dashboard" class="dashboard-container">
    <!-- Loading State -->
    <div v-if="loading" class="dashboard-loading">
      <div class="spinner"></div>
      <p>Loading dashboard...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="dashboard-error">
      <div class="error-icon">⚠️</div>
      <h3>Error Loading Dashboard</h3>
      <p>{{ error }}</p>
      <button @click="retry" class="btn-retry">Retry</button>
    </div>

    <!-- Main Dashboard -->
    <div v-else class="dashboard-content">
      <!-- Header -->
      <DashboardHeader 
        :user-email="userEmail"
        :is-super-user="isSuperUser"
        :selected-establishment="selectedEstablishment"
        @establishment-change="handleEstablishmentChange"
      />

      <!-- Filters Bar -->
      <FilterBar 
        :filters="filters"
        @filter-change="handleFilterChange"
      />

      <!-- Tab Navigation -->
      <div class="dashboard-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          :class="['tab-button', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <transition name="fade" mode="out-in">
          <component 
            :is="currentTabComponent" 
            :key="activeTab"
            :data="dashboardData"
            :filters="filters"
            :loading="sectionLoading"
          />
        </transition>
      </div>
    </div>

    <!-- Super User Controls (Modal) -->
    <SuperUserModal 
      v-if="showSuperUserModal"
      :establishments="establishments"
      @select="handleEstablishmentSelect"
      @close="showSuperUserModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, provide } from 'vue'
import { useDashboardStore } from './stores/dashboard'
import DashboardHeader from './components/DashboardHeader.vue'
import FilterBar from './components/FilterBar.vue'
import SuperUserModal from './components/SuperUserModal.vue'
import OverviewSection from './components/Overview/OverviewSection.vue'
import QLASection from './components/QLA/QLASection.vue'
import InsightsSection from './components/Insights/InsightsSection.vue'

// Store
const store = useDashboardStore()

// State
const loading = ref(true)
const error = ref(null)
const sectionLoading = ref(false)
const activeTab = ref('overview')
const showSuperUserModal = ref(false)

// Computed
const userEmail = computed(() => store.userEmail)
const isSuperUser = computed(() => store.isSuperUser)
const selectedEstablishment = computed(() => store.selectedEstablishment)
const establishments = computed(() => store.establishments)
const dashboardData = computed(() => store.dashboardData)
const filters = computed(() => store.filters)

// Tab configuration
const tabs = [
  { id: 'overview', label: 'Overview', component: OverviewSection },
  { id: 'qla', label: 'Question Level Analysis', component: QLASection },
  { id: 'insights', label: 'Student Comment Insights', component: InsightsSection }
]

const currentTabComponent = computed(() => {
  const tab = tabs.find(t => t.id === activeTab.value)
  return tab ? tab.component : null
})

// Methods
async function initialize() {
  try {
    loading.value = true
    error.value = null
    
    await store.initialize()
    
    // If super user, show establishment selector
    if (store.isSuperUser) {
      showSuperUserModal.value = true
    } else {
      // Load data for staff admin's establishment
      await loadDashboardData()
    }
  } catch (err) {
    console.error('Dashboard initialization error:', err)
    error.value = err.message || 'Failed to initialize dashboard'
  } finally {
    loading.value = false
  }
}

async function loadDashboardData() {
  try {
    sectionLoading.value = true
    await store.loadDashboardData()
  } catch (err) {
    console.error('Error loading dashboard data:', err)
    error.value = err.message || 'Failed to load dashboard data'
  } finally {
    sectionLoading.value = false
  }
}

function handleEstablishmentChange(establishmentId) {
  store.selectEstablishment(establishmentId)
  loadDashboardData()
}

function handleEstablishmentSelect(establishment) {
  showSuperUserModal.value = false
  store.selectEstablishment(establishment.id)
  loadDashboardData()
}

function handleFilterChange(filterType, value) {
  store.updateFilter(filterType, value)
}

function retry() {
  initialize()
}

// Lifecycle
onMounted(() => {
  initialize()
})
</script>

<style>
/* Import existing styles */
@import './assets/styles/dashboard.css';

/* Vue-specific styles */
.dashboard-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.dashboard-loading,
.dashboard-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #4A90E2;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.dashboard-error {
  text-align: center;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 1rem;
}

.btn-retry {
  background: #4A90E2;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  transition: background 0.3s;
}

.btn-retry:hover {
  background: #357ABD;
}

/* Tab Navigation */
.dashboard-tabs {
  display: flex;
  background: white;
  border-bottom: 2px solid #e0e0e0;
  padding: 0;
  margin: 0 -20px;
  padding: 0 20px;
}

.tab-button {
  flex: 1;
  padding: 1rem 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.3s;
}

.tab-button:hover {
  color: #4A90E2;
}

.tab-button.active {
  color: #4A90E2;
  border-bottom-color: #4A90E2;
}

/* Tab Content */
.tab-content {
  padding: 2rem 0;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>