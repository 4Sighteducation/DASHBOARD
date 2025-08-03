<template>
  <div class="wordcloud-container">
    <canvas ref="wordCloudCanvas" id="wordCloudCanvas"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  data: Array
})

const wordCloudCanvas = ref(null)

function generateWordCloud() {
  if (!props.data || !wordCloudCanvas.value || !window.WordCloud) {
    console.warn('WordCloud dependencies not ready')
    return
  }
  
  // Convert data to WordCloud format
  const words = props.data.map(item => [item.text, item.size])
  
  // WordCloud options
  const options = {
    list: words,
    gridSize: 8,
    weightFactor: 10,
    fontFamily: 'Inter, sans-serif',
    color: function() {
      const colors = ['#ff8f00', '#86b4f0', '#72cb44', '#7f31a4', '#f032e6']
      return colors[Math.floor(Math.random() * colors.length)]
    },
    rotateRatio: 0.5,
    backgroundColor: 'transparent',
    click: function(item) {
      console.log('Word clicked:', item)
    }
  }
  
  // Generate word cloud
  window.WordCloud(wordCloudCanvas.value, options)
}

onMounted(() => {
  // Wait a bit for WordCloud library to load
  setTimeout(generateWordCloud, 500)
})

watch(() => props.data, () => {
  generateWordCloud()
}, { deep: true })
</script>

<style scoped>
.wordcloud-container {
  position: relative;
  width: 100%;
  height: 400px;
  background: var(--secondary-bg);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

#wordCloudCanvas {
  width: 100%;
  height: 100%;
}
</style>