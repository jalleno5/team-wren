import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    // sends the app's /api requests to the api server (npm run api, or npm run mock-api)
    proxy: {
      '/api': 'http://localhost:3001',
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Put the Supabase library in its own file so the main app file stays smaller
        manualChunks(id) {
          if (id.includes('/node_modules/@supabase/')) return 'supabase'
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.js'],
  },
})