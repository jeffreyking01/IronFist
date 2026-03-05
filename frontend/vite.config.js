import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      // Proxy all /api calls to the FastAPI backend
      '/api': {
        target: 'http://api:8000',
        changeOrigin: true,
      }
    }
  }
})
