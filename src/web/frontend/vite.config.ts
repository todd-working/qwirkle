import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        // Use Docker service name when running in container, localhost for local dev
        target: process.env.DOCKER_ENV ? 'http://backend:8080' : 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
