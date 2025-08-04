# Dashboard Migration Checklist: dashboard4c.js → Vue Dashboard

## Overview
This document provides a comprehensive checklist and reference guide for migrating all features from `dashboard4c.js` to the new Vue-based dashboard application that uses Supabase endpoints.

## Architecture Changes
- [x] Vue 3 with Composition API (already implemented)
- [x] Pinia store for state management (already implemented)
- [x] Supabase endpoints instead of direct Knack API calls
- [ ] Maintain compatibility with Knack page loading mechanism

## Core Features to Migrate

### 1. Authentication & User Management

#### 1.1 User Authentication
- [ ] Auto-detect logged-in user from Knack
- [ ] Get user email from Knack user object
- [ ] Check super user status via Supabase endpoint
- [ ] Staff admin record lookup by email

#### 1.2 Super User Features
- [x] Super user modal for establishment selection (basic implementation exists)
- [ ] Trust selection dropdown for super users
- [ ] Load all establishments for super users
- [ ] Trust-level analysis capabilities
- [ ] School comparison within trusts

### 2. Data Loading & Caching

#### 2.1 Smart Caching System
- [ ] Implement localStorage caching with timestamps
- [ ] Cache establishment data (1 hour expiry)
- [ ] Cache filter options (1 hour expiry)
- [ ] Cache dashboard data (30 minute expiry)
- [ ] Force refresh option for all cached data

#### 2.2 Progressive Loading
- [ ] Load core data first (establishment info, basic stats)
- [ ] Load detailed analysis data asynchronously
- [ ] Show loading states for each section independently

### 3. Overview Section (ERI & VESPA)

#### 3.1 Exam Readiness Index (ERI)
- [ ] Calculate ERI from 3 psychometric questions:
  - "I know where to get support if I need it"
  - "I feel prepared for my exams"
  - "I feel I will achieve my potential"
- [ ] Display ERI gauge/speedometer visualization
- [ ] Compare school vs national ERI
- [ ] ERI interpretation guide modal
- [ ] Color coding based on score ranges:
  - 4.0-5.0: Excellent (green)
  - 3.0-3.9: Good (blue)
  - 2.0-2.9: Below Average (orange)
  - 1.0-1.9: Low (red)

#### 3.2 VESPA Scores
- [ ] Display all 5 VESPA elements:
  - Vision
  - Effort
  - Systems
  - Practice
  - Attitude
- [ ] VESPA radar/spider chart
- [ ] VESPA bar chart comparison (school vs national)
- [ ] Individual VESPA element cards with:
  - Current score
  - Comparison to national average
  - Trend indicator
  - Response count

#### 3.3 Response Statistics
- [ ] Total response count display
- [ ] Response rate calculation
- [ ] Filter impact on response counts
- [ ] Year group distribution chart

### 4. Question Level Analysis (QLA) - CRITICAL FEATURES

#### 4.1 Top/Bottom Questions Display
- [ ] Top 5 performing questions cards
- [ ] Bottom 5 questions needing attention
- [ ] For each question card show:
  - Rank number
  - Full question text
  - Average score (color-coded)
  - Mini distribution chart
  - Response count
  - Standard deviation
  - Mode
- [ ] Click card for detailed analysis

#### 4.2 Question Statistics
- [ ] Calculate for each question:
  - Mean score
  - Standard deviation
  - Mode
  - Score distribution (1-5)
  - Response count
- [ ] Handle missing data gracefully with estimations

#### 4.3 Question Detail Modal
- [ ] Full question text
- [ ] Detailed statistics breakdown
- [ ] Full-size distribution chart
- [ ] Comparison to national average
- [ ] Sub-group analysis options
- [ ] Historical trend (if available)

#### 4.4 Advanced QLA Features
- [ ] Question search/filter
- [ ] Category-based analysis
- [ ] Export question data
- [ ] Print-friendly reports

### 5. Filtering System

#### 5.1 Core Filters
- [ ] Cycle selection (1, 2, 3)
- [ ] Year group multi-select
- [ ] Gender filter
- [ ] FSM status filter
- [ ] EAL status filter
- [ ] Custom field filters based on establishment

#### 5.2 Filter UI/UX
- [ ] Dropdown with counts for each option
- [ ] Active filter pills display
- [ ] Clear all filters button
- [ ] Filter state persistence
- [ ] Real-time data updates on filter change

### 6. Student Comment Insights

#### 6.1 Word Cloud
- [ ] Generate word cloud from student comments
- [ ] Interactive word sizing based on frequency
- [ ] Exclude common words
- [ ] Click word to see related comments

#### 6.2 Theme Analysis
- [ ] Auto-categorize comments into themes
- [ ] Display theme distribution
- [ ] Sentiment analysis per theme
- [ ] Drill-down to see comments by theme

### 7. Data Visualization Components

#### 7.1 Charts Required
- [ ] ERI Gauge/Speedometer (Chart.js)
- [ ] VESPA Radar Chart
- [ ] VESPA Bar Chart (comparison)
- [ ] Distribution histograms for questions
- [ ] Mini bar charts for question cards
- [ ] Year group distribution chart
- [ ] Response rate donut chart

#### 7.2 Chart Features
- [ ] Consistent color scheme
- [ ] Responsive sizing
- [ ] Interactive tooltips
- [ ] Export as image
- [ ] Print-friendly versions

### 8. Comparative Analysis

#### 8.1 Benchmarking
- [ ] School vs National comparisons
- [ ] School vs Trust comparisons (if applicable)
- [ ] Historical comparisons (previous cycles)
- [ ] Sub-group comparisons

#### 8.2 Statistical Insights
- [ ] Automated insights generation
- [ ] Significant differences highlighting
- [ ] Trend identification
- [ ] Performance alerts

### 9. Export & Reporting

#### 9.1 Export Options
- [ ] Export filtered data as CSV
- [ ] Generate PDF reports
- [ ] Print-optimized views
- [ ] Email report functionality

#### 9.2 Report Components
- [ ] Executive summary
- [ ] Detailed statistics tables
- [ ] All visualizations
- [ ] Actionable insights
- [ ] Appendix with raw data

### 10. UI/UX Features

#### 10.1 Responsive Design
- [ ] Mobile-optimized layouts
- [ ] Touch-friendly interactions
- [ ] Adaptive chart sizing
- [ ] Collapsible sections for mobile

#### 10.2 Accessibility
- [ ] ARIA labels
- [ ] Keyboard navigation
- [ ] High contrast mode
- [ ] Screen reader support

#### 10.3 Performance
- [ ] Lazy loading for charts
- [ ] Virtual scrolling for long lists
- [ ] Debounced filter updates
- [ ] Optimized re-renders

### 11. Error Handling & Validation

#### 11.1 Error States
- [ ] Network error handling
- [ ] Empty data states
- [ ] Partial data loading
- [ ] Graceful fallbacks

#### 11.2 Data Validation
- [ ] Validate API responses
- [ ] Handle missing fields
- [ ] Data type checking
- [ ] Range validation for scores

### 12. Integration Requirements

#### 12.1 Knack Integration
- [ ] Load within Knack page (iframe or embedded)
- [ ] Access Knack user object
- [ ] Maintain Knack session
- [ ] Handle Knack events

#### 12.2 Supabase API Endpoints Needed
- [ ] `/api/establishments` - Get all establishments
- [ ] `/api/statistics/{establishmentId}` - Get school statistics
- [ ] `/api/national-statistics` - Get national averages
- [ ] `/api/qla/top-bottom` - Get top/bottom questions
- [ ] `/api/qla/questions` - Get all questions with stats
- [ ] `/api/responses` - Get raw response data
- [ ] `/api/comments` - Get student comments
- [ ] `/api/super-users` - Check super user status
- [ ] `/api/trusts` - Get trust information

## Implementation Priority

### Phase 1 - Core Functionality (Critical)
1. Fix authentication and user detection
2. Implement ERI calculation and display
3. Complete QLA with top/bottom questions
4. Add question detail cards with statistics
5. Implement all VESPA visualizations

### Phase 2 - Enhanced Features
1. Complete filtering system
2. Add comparative analysis
3. Implement caching system
4. Add export functionality

### Phase 3 - Advanced Features
1. Student comment insights
2. Trust-level analysis
3. Historical trends
4. Advanced reporting

## Technical Considerations

### State Management (Pinia Store)
```javascript
// Additional state needed:
{
  // QLA specific
  questionStats: {},
  topQuestions: [],
  bottomQuestions: [],
  questionDetails: {},
  
  // ERI/VESPA
  schoolERI: null,
  nationalERI: null,
  vespaScores: {},
  
  // Caching
  cacheTimestamps: {},
  
  // UI State
  activeFilters: {},
  loadingStates: {},
}
```

### Component Structure
```
src/
├── components/
│   ├── Overview/
│   │   ├── ERIGauge.vue (new)
│   │   ├── ERIInfoModal.vue (new)
│   │   ├── VespaRadarChart.vue (enhance)
│   │   ├── VespaBarChart.vue (enhance)
│   │   └── ResponseStats.vue (new)
│   ├── QLA/
│   │   ├── TopBottomQuestions.vue (new - critical)
│   │   ├── QuestionCard.vue (new - critical)
│   │   ├── QuestionDetailModal.vue (new)
│   │   ├── QuestionStatistics.vue (new)
│   │   └── MiniDistributionChart.vue (new)
│   └── Shared/
│       ├── LoadingSpinner.vue
│       ├── ErrorState.vue
│       └── EmptyState.vue
```

### CSS Variables Needed
```css
:root {
  /* Score-based colors */
  --color-excellent: #10b981;
  --color-good: #3b82f6;
  --color-average: #f59e0b;
  --color-poor: #ef4444;
  
  /* Chart colors */
  --chart-school: #4A90E2;
  --chart-national: #E85F5C;
  --chart-trust: #9b59b6;
}
```

## Testing Checklist

### Functionality Tests
- [ ] User authentication flow
- [ ] Super user establishment selection
- [ ] All calculations (ERI, VESPA, statistics)
- [ ] Filter combinations
- [ ] Chart rendering and interactions
- [ ] Export functionality

### Integration Tests
- [ ] Knack page loading
- [ ] API error handling
- [ ] Session management
- [ ] Cross-browser compatibility

### Performance Tests
- [ ] Load time < 3 seconds
- [ ] Smooth filter updates
- [ ] Chart animation performance
- [ ] Memory usage optimization

## Notes for Implementation

1. **Question Indices**: The most critical missing feature is the QLA section with top/bottom question cards showing detailed statistics and mini charts.

2. **ERI Calculation**: Must use the specific 3 psychometric questions, not VESPA scores.

3. **Caching**: Implement aggressive caching to reduce API calls and improve performance.

4. **Progressive Enhancement**: Load basic data first, then enhance with detailed statistics.

5. **Backwards Compatibility**: Ensure the new dashboard can read and understand any existing localStorage data from the old dashboard.

This checklist should guide the complete migration of all features from dashboard4c.js to the Vue application.