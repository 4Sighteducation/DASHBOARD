<template>
  <header class="dashboard-header">
    <div class="header-content">
      <div class="header-left">
        <h1 class="dashboard-title">VESPA Dashboard</h1>
        <div v-if="selectedEstablishment" class="establishment-info">
          <span class="establishment-label">Viewing:</span>
          <span class="establishment-name">{{ establishmentName }}</span>
        </div>
      </div>
      
      <div class="header-right">
        <div class="user-info">
          <span class="user-email">{{ userEmail }}</span>
          <span v-if="isSuperUser" class="user-role">Super User</span>
          <span v-else class="user-role">Staff Admin</span>
        </div>
        
        <button v-if="isSuperUser" @click="openEstablishmentSelector" class="btn btn-secondary">
          <svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
          Change School
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { API } from '../services/api'

const props = defineProps({
  userEmail: String,
  isSuperUser: Boolean,
  selectedEstablishment: String
})

const emit = defineEmits(['establishment-change'])

const establishmentName = ref('Loading...')

// Fetch establishment name when selection changes
watch(() => props.selectedEstablishment, async (newVal) => {
  if (newVal) {
    try {
      const data = await API.getEstablishmentName(newVal)
      establishmentName.value = data.name
    } catch (error) {
      establishmentName.value = 'Unknown School'
    }
  }
}, { immediate: true })

function openEstablishmentSelector() {
  emit('establishment-change')
}
</script>

<style scoped>
.dashboard-header {
  background: var(--secondary-bg);
  border-bottom: 1px solid var(--border-color);
  padding: var(--spacing-md) 0;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.dashboard-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.establishment-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  background: var(--card-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.establishment-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.establishment-name {
  color: var(--text-primary);
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.user-email {
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 500;
}

.user-role {
  color: var(--text-secondary);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.icon {
  margin-right: var(--spacing-xs);
}

@media (max-width: 768px) {
  .header-content {
    padding: 0 var(--spacing-md);
  }
  
  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }
  
  .dashboard-title {
    font-size: 1.25rem;
  }
  
  .establishment-info {
    font-size: 0.875rem;
  }
  
  .user-info {
    display: none;
  }
}</style>