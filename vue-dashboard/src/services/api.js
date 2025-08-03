import axios from 'axios'

// Create axios instance with base configuration
const apiClient = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for adding auth headers if needed
apiClient.interceptors.request.use(
  config => {
    // Get config from global
    const dashboardConfig = window.DASHBOARD_CONFIG
    if (dashboardConfig) {
      // Add Knack API headers if needed
      if (dashboardConfig.knackAppId) {
        config.headers['X-Knack-Application-Id'] = dashboardConfig.knackAppId
      }
      if (dashboardConfig.knackApiKey) {
        config.headers['X-Knack-REST-API-KEY'] = dashboardConfig.knackApiKey
      }
    }
    return config
  },
  error => Promise.reject(error)
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    const message = error.response?.data?.message || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

// API service matching the previous implementation
export const API = {
  // Get base URL from config
  getBaseUrl() {
    const config = window.DASHBOARD_CONFIG
    return config?.herokuAppUrl || 'https://vespa-dashboard-9a1f84ee5341.herokuapp.com'
  },

  // Supabase endpoints
  async getSchools() {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/schools`)
    return response.data
  },

  async checkSuperUser(email) {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/check-super-user`, {
      params: { email }
    })
    return response.data
  },

  async getAcademicYears() {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/academic-years`)
    return response.data
  },

  async getKeyStages() {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/key-stages`)
    return response.data
  },

  async getYearGroups() {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/year-groups`)
    return response.data
  },

  async getStatistics(establishmentId, filters = {}) {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/statistics`, {
      params: {
        establishment_id: establishmentId,
        ...filters
      }
    })
    return response.data
  },

  async getQLAData(establishmentId, filters = {}) {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/qla`, {
      params: {
        establishment_id: establishmentId,
        ...filters
      }
    })
    return response.data
  },

  async getWordCloudData(establishmentId, filters = {}) {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/word-cloud`, {
      params: {
        establishment_id: establishmentId,
        ...filters
      }
    })
    return response.data
  },

  async getCommentInsights(establishmentId, filters = {}) {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/comment-insights`, {
      params: {
        establishment_id: establishmentId,
        ...filters
      }
    })
    return response.data
  },

  async getEstablishmentName(establishmentId) {
    const response = await apiClient.get(`${this.getBaseUrl()}/api/establishment/${establishmentId}`)
    return response.data
  },

  // Utility methods
  handleResponse(response) {
    if (!response.ok) {
      throw new Error(response.statusText || 'Request failed')
    }
    return response.json()
  },

  buildQueryString(params) {
    return Object.entries(params)
      .filter(([_, value]) => value !== null && value !== undefined && value !== '')
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&')
  }
}

// Also export individual methods for convenience
export const {
  getSchools,
  checkSuperUser,
  getAcademicYears,
  getKeyStages,
  getYearGroups,
  getStatistics,
  getQLAData,
  getWordCloudData,
  getCommentInsights,
  getEstablishmentName
} = API