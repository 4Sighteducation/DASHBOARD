import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  },
  build: {
    // Library mode for single-file output
    lib: {
      entry: resolve(__dirname, 'src/main.js'),
      name: 'VueDashboard',
      formats: ['iife'] // Immediately invoked function for Knack
    },
    rollupOptions: {
      // Ensure we bundle everything
      external: [],
      output: {
        // JS output
        entryFileNames: 'vuedash1a.js',
        
        // CSS output - extracted to separate file
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith('.css')) {
            return 'vuedash.css'
          }
          return '[name][extname]'
        },
        
        // No globals needed since we're bundling everything
        globals: {}
      }
    },
    // Extract CSS to separate file
    cssCodeSplit: false,
    // Minify for production
    minify: true,
    // Generate sourcemaps for debugging
    sourcemap: true
  },
  // Development server config
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'https://vespa-dashboard-9a1f84ee5341.herokuapp.com',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path
      }
    }
  }
})