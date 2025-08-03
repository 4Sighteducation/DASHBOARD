import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// Global initializer function that Knack's AppLoader will call
window.initializeVueDashboard = function() {
  console.log('Vue Dashboard: Initializing...')
  
  // Get config from AppLoader
  const config = window.DASHBOARD_CONFIG
  if (!config) {
    console.error('Vue Dashboard: No DASHBOARD_CONFIG found')
    return
  }
  
  // Check if app already exists and unmount it
  if (window.__vueDashboardApp) {
    console.log('Vue Dashboard: Unmounting existing app')
    window.__vueDashboardApp.unmount()
  }
  
  // Check if container exists
  const container = document.querySelector(config.elementSelector)
  if (!container) {
    console.error(`Vue Dashboard: Container not found: ${config.elementSelector}`)
    return
  }
  
  // Clear container
  container.innerHTML = ''
  
  // Create mount point
  const mountPoint = document.createElement('div')
  mountPoint.id = 'vue-dashboard-app'
  container.appendChild(mountPoint)
  
  // Create Vue app
  const app = createApp(App)
  
  // Create Pinia store
  const pinia = createPinia()
  app.use(pinia)
  
  // Make config available globally in Vue app
  app.config.globalProperties.$dashboardConfig = config
  
  // Provide config to all components
  app.provide('dashboardConfig', config)
  
  // Mount the app
  window.__vueDashboardApp = app.mount(mountPoint)
  
  console.log('Vue Dashboard: Initialized successfully')
}

// Also export for development
export const initializeVueDashboard = window.initializeVueDashboard