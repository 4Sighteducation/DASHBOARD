<template>
  <div class="qla-info-modal" @click.self="$emit('close')">
    <div class="qla-info-content">
      <div class="qla-info-header">
        <h3>Understanding Question Level Analysis</h3>
        <button class="qla-info-close" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
      
      <div class="qla-info-body">
        <div class="qla-section">
          <h4>What is Question Level Analysis?</h4>
          <p>Question Level Analysis (QLA) provides detailed insights into how students responded to individual survey questions. It helps identify:</p>
          <ul>
            <li>Which questions received the most positive responses</li>
            <li>Areas where students may need additional support</li>
            <li>Patterns in student responses across different questions</li>
          </ul>
        </div>

        <div class="qla-section">
          <h4>Understanding the Metrics</h4>
          
          <div class="metric-item">
            <h5>Average Score</h5>
            <p>The mean score (1-5) for all responses to this question. Higher scores indicate more positive responses.</p>
            <div class="score-scale">
              <div class="scale-item excellent">4.0 - 5.0: Excellent</div>
              <div class="scale-item good">3.0 - 3.9: Good</div>
              <div class="scale-item average">2.0 - 2.9: Average</div>
              <div class="scale-item poor">1.0 - 1.9: Needs Attention</div>
            </div>
          </div>

          <div class="metric-item">
            <h5>Standard Deviation (Std Dev)</h5>
            <p>Measures how spread out the responses are. Lower values indicate more agreement among students:</p>
            <ul>
              <li><strong>&lt; 0.7:</strong> Strong consensus</li>
              <li><strong>0.7 - 1.0:</strong> Moderate agreement</li>
              <li><strong>&gt; 1.0:</strong> Diverse opinions</li>
            </ul>
          </div>

          <div class="metric-item">
            <h5>Mode</h5>
            <p>The most frequently selected response (1-5). This shows the most common opinion among students.</p>
          </div>

          <div class="metric-item">
            <h5>Response Distribution</h5>
            <p>The mini chart shows how responses are distributed across the 5-point scale. Look for:</p>
            <ul>
              <li><strong>Skewed left:</strong> Most students disagree</li>
              <li><strong>Centered:</strong> Mixed opinions</li>
              <li><strong>Skewed right:</strong> Most students agree</li>
            </ul>
          </div>
        </div>

        <div class="qla-section">
          <h4>How to Use This Information</h4>
          <ul>
            <li><strong>Top Questions:</strong> Celebrate and maintain these strengths. Share best practices that contribute to these positive outcomes.</li>
            <li><strong>Questions Needing Attention:</strong> Focus improvement efforts here. Develop targeted interventions to address these areas.</li>
            <li><strong>Look for Patterns:</strong> Are related questions scoring similarly? This might indicate broader themes.</li>
            <li><strong>Compare with National Data:</strong> Click on any question to see how your school compares to national averages.</li>
          </ul>
        </div>

        <div class="qla-section tip-section">
          <h4>💡 Pro Tip</h4>
          <p>Click on any question card to see detailed analysis including:</p>
          <ul>
            <li>Full response distribution</li>
            <li>Comparison with national averages</li>
            <li>Year-over-year trends</li>
            <li>Subgroup analysis</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['close'])
</script>

<style scoped>
.qla-info-modal {
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

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.qla-info-content {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
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

.qla-info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.qla-info-header h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.qla-info-close {
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

.qla-info-close:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: rotate(90deg);
}

.qla-info-body {
  color: var(--text-secondary);
  line-height: 1.8;
}

.qla-section {
  margin-bottom: var(--spacing-xl);
}

.qla-section h4 {
  color: var(--text-primary);
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: var(--spacing-md);
}

.qla-section h5 {
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
}

.qla-section p {
  margin-bottom: var(--spacing-md);
}

.qla-section ul {
  list-style: none;
  padding-left: 0;
}

.qla-section ul li {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: var(--spacing-sm);
}

.qla-section ul li::before {
  content: "•";
  position: absolute;
  left: 0;
  color: var(--accent-primary);
  font-weight: bold;
}

/* Metric Items */
.metric-item {
  background: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

/* Score Scale */
.score-scale {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.scale-item {
  padding: var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-weight: 600;
  text-align: center;
  border: 2px solid currentColor;
}

.scale-item.excellent {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.scale-item.good {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.scale-item.average {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.scale-item.poor {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

/* Tip Section */
.tip-section {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
}

/* Responsive */
@media (max-width: 768px) {
  .qla-info-content {
    padding: var(--spacing-lg);
  }
  
  .qla-info-header h3 {
    font-size: 1.25rem;
  }
  
  .scale-item {
    font-size: 0.9rem;
  }
}

/* Scrollbar Styling */
.qla-info-content::-webkit-scrollbar {
  width: 8px;
}

.qla-info-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.qla-info-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.qla-info-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>