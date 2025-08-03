<template>
  <div class="filter-bar">
    <div class="filter-container">
      <div class="filter-group">
        <label class="filter-label">Academic Year</label>
        <select 
          class="form-select" 
          :value="filters.academicYear"
          @change="updateFilter('academicYear', $event.target.value)"
        >
          <option value="all">All Years</option>
          <option v-for="year in academicYears" :key="year" :value="year">
            {{ year }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">Key Stage</label>
        <select 
          class="form-select"
          :value="filters.keyStage"
          @change="updateFilter('keyStage', $event.target.value)"
        >
          <option value="all">All Key Stages</option>
          <option v-for="ks in keyStages" :key="ks" :value="ks">
            {{ ks }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">Year Group</label>
        <select 
          class="form-select"
          :value="filters.yearGroup"
          @change="updateFilter('yearGroup', $event.target.value)"
        >
          <option value="all">All Year Groups</option>
          <option v-for="year in yearGroups" :key="year" :value="year">
            Year {{ year }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">VESPA Area</label>
        <select 
          class="form-select"
          :value="filters.vespaArea"
          @change="updateFilter('vespaArea', $event.target.value)"
        >
          <option value="all">All Areas</option>
          <option value="vision">Vision</option>
          <option value="effort">Effort</option>
          <option value="systems">Systems</option>
          <option value="practice">Practice</option>
          <option value="attitude">Attitude</option>
        </select>
      </div>

      <button 
        v-if="hasActiveFilters" 
        @click="clearFilters"
        class="btn btn-secondary btn-sm"
      >
        Clear Filters
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDashboardStore } from '../stores/dashboard'

const props = defineProps({
  filters: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['filter-change'])

const store = useDashboardStore()

// Get filter options from store
const academicYears = computed(() => 
  store.filterOptions.academicYears
    .filter(opt => opt.value !== 'all')
    .map(opt => opt.value)
)

const keyStages = computed(() => 
  store.filterOptions.keyStages
    .filter(opt => opt.value !== 'all')
    .map(opt => opt.value)
)

const yearGroups = computed(() => 
  store.filterOptions.yearGroups
    .filter(opt => opt.value !== 'all')
    .map(opt => opt.value)
)

const hasActiveFilters = computed(() => {
  return Object.values(props.filters).some(value => value !== 'all')
})

function updateFilter(filterType, value) {
  emit('filter-change', filterType, value)
}

function clearFilters() {
  store.resetFilters()
}
</script>

<style scoped>
.filter-bar {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin: var(--spacing-lg) 0;
}

.filter-container {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-end;
  flex-wrap: wrap;
}

.filter-group {
  flex: 1;
  min-width: 200px;
}

.filter-label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-select {
  width: 100%;
  padding: 0.5rem 2.5rem 0.5rem 0.75rem;
  background-color: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.form-select:hover {
  border-color: var(--accent-primary);
}

.form-select:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

@media (max-width: 1024px) {
  .filter-group {
    min-width: calc(50% - var(--spacing-sm));
  }
}

@media (max-width: 640px) {
  .filter-container {
    flex-direction: column;
  }
  
  .filter-group {
    width: 100%;
    min-width: unset;
  }
  
  .btn-sm {
    width: 100%;
  }
}</style>