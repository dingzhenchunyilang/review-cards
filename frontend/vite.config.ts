import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The backend port is configurable so the app still works when 8000 is taken
// by another local service. Keep this in sync with the uvicorn --port flag.
const BACKEND_PORT = process.env.BACKEND_PORT ?? '8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
    },
  },
})
