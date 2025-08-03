<template>
  <div class="modal-backdrop" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">Select Establishment</h2>
        <button @click="close" class="modal-close">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="modal-body">
        <div class="search-box">
          <input 
            v-model="searchTerm"
            type="text"
            placeholder="Search establishments..."
            class="form-control"
          />
        </div>
        
        <div class="establishments-list">
          <div 
            v-for="establishment in filteredEstablishments" 
            :key="establishment.id"
            class="establishment-item"
            @click="selectEstablishment(establishment)"
          >
            <div class="establishment-name">{{ establishment.name }}</div>
            <div class="establishment-type">{{ establishment.type }}</div>
          </div>
          
          <div v-if="filteredEstablishments.length === 0" class="no-results">
            No establishments found
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  establishments: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['select', 'close'])

const searchTerm = ref('')

const filteredEstablishments = computed(() => {
  if (!searchTerm.value) {
    return props.establishments
  }
  
  const term = searchTerm.value.toLowerCase()
  return props.establishments.filter(est => 
    est.name.toLowerCase().includes(term) ||
    est.type.toLowerCase().includes(term)
  )
})

function selectEstablishment(establishment) {
  emit('select', establishment)
}

function close() {
  emit('close')
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.modal-content {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.5rem;
  border-radius: var(--radius-sm);
  transition: all 0.3s ease;
}

.modal-close:hover {
  color: var(--text-primary);
  background: var(--border-color);
}

.modal-body {
  padding: var(--spacing-lg);
  overflow-y: auto;
}

.search-box {
  margin-bottom: var(--spacing-md);
}

.establishments-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.establishment-item {
  padding: var(--spacing-md);
  background: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.3s ease;
}

.establishment-item:hover {
  background: var(--card-hover-bg);
  border-color: var(--accent-primary);
  transform: translateX(4px);
}

.establishment-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.establishment-type {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.no-results {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-secondary);
}

@media (max-width: 640px) {
  .modal-backdrop {
    padding: var(--spacing-md);
  }
  
  .modal-content {
    max-height: 90vh;
  }
}</style>