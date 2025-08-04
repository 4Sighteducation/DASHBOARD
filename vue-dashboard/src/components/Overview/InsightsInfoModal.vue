<template>
  <div class="insights-info-modal" @click.self="$emit('close')">
    <div class="insights-info-content">
      <div class="info-header">
        <h3>Understanding Automated Insights</h3>
        <button class="info-close" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
      
      <div class="info-body">
        <div class="info-section">
          <h4>What are Automated Insights?</h4>
          <p>Automated Insights analyze student responses across 12 key areas that research shows are critical for academic success. Each insight combines responses from related questions to provide a comprehensive view of student attitudes, behaviors, and readiness.</p>
        </div>

        <div class="info-section">
          <h4>The 12 Insight Categories</h4>
          <div class="categories-grid">
            <div class="category-item">
              <span class="category-icon">🌱</span>
              <div>
                <strong>Growth Mindset</strong>
                <p>Belief that abilities can be developed</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">🚀</span>
              <div>
                <strong>Academic Momentum</strong>
                <p>Drive and engagement with learning</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">📚</span>
              <div>
                <strong>Study Effectiveness</strong>
                <p>Use of proven study techniques</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">💪</span>
              <div>
                <strong>Exam Confidence</strong>
                <p>Belief in ability to succeed</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">📋</span>
              <div>
                <strong>Organization Skills</strong>
                <p>Planning and managing responsibilities</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">🛡️</span>
              <div>
                <strong>Resilience</strong>
                <p>Bouncing back from setbacks</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">🧘</span>
              <div>
                <strong>Stress Management</strong>
                <p>Handling pressure effectively</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">🎯</span>
              <div>
                <strong>Active Learning</strong>
                <p>Engaging with material actively</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">🤝</span>
              <div>
                <strong>Support Readiness</strong>
                <p>Awareness of available support</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">⏰</span>
              <div>
                <strong>Time Management</strong>
                <p>Effective use of time</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">🎓</span>
              <div>
                <strong>Academic Confidence</strong>
                <p>Self-belief in academic abilities</p>
              </div>
            </div>
            <div class="category-item">
              <span class="category-icon">📝</span>
              <div>
                <strong>Revision Readiness</strong>
                <p>Preparedness for revision challenges</p>
              </div>
            </div>
          </div>
        </div>

        <div class="info-section">
          <h4>How to Interpret Scores</h4>
          <div class="score-guide">
            <div class="score-level excellent">
              <span class="score-range">4.0 - 5.0</span>
              <span class="score-label">Excellent</span>
              <p>Area of strength - maintain and share best practices</p>
            </div>
            <div class="score-level good">
              <span class="score-range">3.0 - 3.9</span>
              <span class="score-label">Good</span>
              <p>Performing well with room for improvement</p>
            </div>
            <div class="score-level average">
              <span class="score-range">2.0 - 2.9</span>
              <span class="score-label">Average</span>
              <p>Mixed results - targeted support recommended</p>
            </div>
            <div class="score-level poor">
              <span class="score-range">1.0 - 1.9</span>
              <span class="score-label">Needs Attention</span>
              <p>Priority area requiring immediate intervention</p>
            </div>
          </div>
        </div>

        <div class="info-section">
          <h4>Using Insights Effectively</h4>
          <ul>
            <li><strong>Prioritize Low Scores:</strong> Focus interventions on areas marked as "Needs Attention"</li>
            <li><strong>Look for Patterns:</strong> Related insights often cluster together</li>
            <li><strong>Track Progress:</strong> Monitor how scores change over time</li>
            <li><strong>Take Action:</strong> Click any insight for specific recommendations</li>
            <li><strong>Share Success:</strong> Use high-scoring areas as models for improvement</li>
          </ul>
        </div>

        <div class="info-section tip-box">
          <h4>💡 Pro Tip</h4>
          <p>Insights are most powerful when used together. For example, low "Study Effectiveness" combined with low "Time Management" suggests students need help with planning and study skills.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['close'])
</script>

<style scoped>
.insights-info-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-md);
  animation: fadeIn 0.3s ease;
}

.insights-info-content {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.info-header h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.info-close {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
}

.info-close:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: rotate(90deg);
}

.info-body {
  color: var(--text-secondary);
  line-height: 1.8;
}

.info-section {
  margin-bottom: var(--spacing-xl);
}

.info-section h4 {
  color: var(--text-primary);
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
}

.info-section p {
  margin-bottom: var(--spacing-md);
}

/* Categories Grid */
.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-md);
  margin-top: var(--spacing-md);
}

.category-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.category-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.category-item strong {
  display: block;
  color: var(--text-primary);
  font-size: 0.95rem;
  margin-bottom: 0.25rem;
}

.category-item p {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: 0;
}

/* Score Guide */
.score-guide {
  display: grid;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

.score-level {
  display: grid;
  grid-template-columns: 100px 120px 1fr;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 2px solid currentColor;
  background: rgba(255, 255, 255, 0.02);
}

.score-level.excellent {
  color: #10b981;
}

.score-level.good {
  color: #3b82f6;
}

.score-level.average {
  color: #f59e0b;
}

.score-level.poor {
  color: #ef4444;
}

.score-range {
  font-weight: 600;
  font-size: 1rem;
}

.score-label {
  font-weight: 600;
  font-size: 1.1rem;
}

.score-level p {
  margin: 0;
  font-size: 0.95rem;
  color: var(--text-secondary);
}

/* List Styling */
.info-section ul {
  list-style: none;
  padding-left: 0;
}

.info-section ul li {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: var(--spacing-sm);
}

.info-section ul li::before {
  content: "•";
  position: absolute;
  left: 0;
  color: var(--accent-primary);
  font-weight: bold;
}

/* Tip Box */
.tip-box {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
}

.tip-box h4 {
  color: var(--accent-primary);
}

/* Responsive */
@media (max-width: 768px) {
  .insights-info-content {
    padding: var(--spacing-lg);
  }
  
  .categories-grid {
    grid-template-columns: 1fr;
  }
  
  .score-level {
    grid-template-columns: 80px 100px 1fr;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm);
  }
  
  .score-range,
  .score-label {
    font-size: 0.9rem;
  }
}

/* Scrollbar */
.insights-info-content::-webkit-scrollbar {
  width: 8px;
}

.insights-info-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.insights-info-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.insights-info-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>