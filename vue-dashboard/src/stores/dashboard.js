import { defineStore } from 'pinia'
import { API } from '../services/api'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    // User info
    userEmail: null,
    userRole: null,
    isSuperUser: false,
    staffAdminEstablishmentId: null,
    
    // Establishment data
    establishments: [],
    selectedEstablishment: null,
    
    // Dashboard data
    dashboardData: {
      statistics: null,
      qlaData: null,
      wordCloudData: null,
      commentInsights: null
    },
    
    // Filters
    filters: {
      academicYear: 'all',
      keyStage: 'all', 
      yearGroup: 'all',
      vespaArea: 'all',
      questionSubTheme: 'all'
    },
    
    // Filter options
    filterOptions: {
      academicYears: [],
      keyStages: [],
      yearGroups: [],
      vespaAreas: [
        { value: 'all', label: 'All VESPA Areas' },
        { value: 'vision', label: 'Vision' },
        { value: 'effort', label: 'Effort' },
        { value: 'systems', label: 'Systems' },
        { value: 'practice', label: 'Practice' },
        { value: 'attitude', label: 'Attitude' }
      ],
      questionSubThemes: []
    },
    
    // Loading states
    loading: {
      init: false,
      data: false,
      filters: false
    },
    
    // Error states
    errors: {
      init: null,
      data: null
    }
  }),

  getters: {
    isStaffAdmin: (state) => state.userRole === 'staff_admin',
    hasData: (state) => state.dashboardData.statistics !== null,
    activeFilters: (state) => {
      return Object.entries(state.filters)
        .filter(([key, value]) => value !== 'all')
        .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})
    }
  },

  actions: {
    async initialize() {
      this.loading.init = true
      this.errors.init = null
      
      try {
        // Get config from window
        const config = window.DASHBOARD_CONFIG
        if (!config) {
          throw new Error('Dashboard configuration not found')
        }
        
        // Set user email
        this.userEmail = config.loggedInUserEmail
        
        // Check if user is super user
        if (this.userEmail) {
          try {
            console.log('Checking super user status for:', this.userEmail)
            const superUserCheck = await API.checkSuperUser(this.userEmail)
            console.log('Super user check result:', superUserCheck)
            this.isSuperUser = superUserCheck.is_super_user
          } catch (err) {
            console.error('Super user check failed:', err)
            console.error('API URL:', API.getBaseUrl())
            console.warn('Assuming staff admin role')
            this.isSuperUser = false
          }
        }
        
        // Load establishments for super users
        if (this.isSuperUser) {
          await this.loadEstablishments()
        } else {
          // For staff admins, get their establishment from Knack
          await this.loadStaffAdminEstablishment()
        }
        
        // Load filter options
        await this.loadFilterOptions()
        
      } catch (error) {
        this.errors.init = error.message
        throw error
      } finally {
        this.loading.init = false
      }
    },

    async loadEstablishments() {
      try {
        const schools = await API.getSchools()
        this.establishments = schools.map(school => ({
          id: school.id,
          name: school.name,
          type: school.type
        }))
      } catch (error) {
        console.error('Failed to load establishments:', error)
        throw error
      }
    },

    async loadStaffAdminEstablishment() {
      // This mimics the getStaffAdminRecordIdByEmail functionality
      const config = window.DASHBOARD_CONFIG
      
      try {
        // Get Knack user attributes
        const userAttributes = Knack.getUserAttributes()
        const userEmail = userAttributes.email
        
        // Query Knack for staff admin record
        const filters = {
          match: 'and',
          rules: [{
            field: 'field_86', // Staff admin email field
            operator: 'is',
            value: userEmail
          }]
        }
        
        const response = await fetch(`https://api.knack.com/v1/objects/${config.objectKeys.staffAdminRoles}/records?filters=${encodeURIComponent(JSON.stringify(filters))}`, {
          headers: {
            'X-Knack-Application-Id': config.knackAppId,
            'X-Knack-REST-API-Key': config.knackApiKey
          }
        })
        
        const data = await response.json()
        
        if (data.records && data.records.length > 0) {
          const staffRecord = data.records[0]
          // Extract establishment ID from field_110_raw
          if (staffRecord.field_110_raw && staffRecord.field_110_raw.length > 0) {
            this.staffAdminEstablishmentId = staffRecord.field_110_raw[0].id
            this.selectedEstablishment = this.staffAdminEstablishmentId
          }
        }
      } catch (error) {
        console.error('Failed to get staff admin establishment:', error)
        throw new Error('Unable to determine your establishment')
      }
    },

    async loadFilterOptions() {
      try {
        this.loading.filters = true
        
        // Load all filter options in parallel
        const [academicYears, keyStages, yearGroups] = await Promise.all([
          API.getAcademicYears(),
          API.getKeyStages(),
          API.getYearGroups()
        ])
        
        this.filterOptions.academicYears = [
          { value: 'all', label: 'All Academic Years' },
          ...academicYears.map(year => ({ value: year, label: year }))
        ]
        
        this.filterOptions.keyStages = [
          { value: 'all', label: 'All Key Stages' },
          ...keyStages.map(ks => ({ value: ks, label: ks }))
        ]
        
        this.filterOptions.yearGroups = [
          { value: 'all', label: 'All Year Groups' },
          ...yearGroups.map(yg => ({ value: yg, label: `Year ${yg}` }))
        ]
        
      } catch (error) {
        console.error('Failed to load filter options:', error)
      } finally {
        this.loading.filters = false
      }
    },

    async loadDashboardData() {
      if (!this.selectedEstablishment) {
        throw new Error('No establishment selected')
      }
      
      this.loading.data = true
      this.errors.data = null
      
      try {
        // Load all data in parallel
        const [statistics, qlaData, wordCloudData, commentInsights] = await Promise.all([
          API.getStatistics(this.selectedEstablishment, this.activeFilters),
          API.getQLAData(this.selectedEstablishment, this.activeFilters),
          API.getWordCloudData(this.selectedEstablishment, this.activeFilters),
          API.getCommentInsights(this.selectedEstablishment, this.activeFilters)
        ])
        
        this.dashboardData = {
          statistics,
          qlaData,
          wordCloudData,
          commentInsights
        }
        
      } catch (error) {
        this.errors.data = error.message
        throw error
      } finally {
        this.loading.data = false
      }
    },

    selectEstablishment(establishmentId) {
      this.selectedEstablishment = establishmentId
    },

    updateFilter(filterType, value) {
      if (this.filters.hasOwnProperty(filterType)) {
        this.filters[filterType] = value
        // Reload data when filters change
        this.loadDashboardData()
      }
    },

    resetFilters() {
      this.filters = {
        academicYear: 'all',
        keyStage: 'all',
        yearGroup: 'all',
        vespaArea: 'all',
        questionSubTheme: 'all'
      }
      this.loadDashboardData()
    }
  }
})