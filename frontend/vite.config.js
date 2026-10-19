import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const frontendPort = Number(process.env.FRONTEND_PORT || env.FRONTEND_PORT || 5174)
  const backendPort = process.env.BACKEND_PORT || env.BACKEND_PORT || 8000
  const backendProxy =
    process.env.VITE_BACKEND_PROXY ||
    env.VITE_BACKEND_PROXY ||
    `http://backend:${backendPort}`

  return {
    plugins: [vue()],
    server: {
      host: '0.0.0.0',
      port: frontendPort,
      strictPort: true,
      allowedHosts: true,
      watch: {
        usePolling: true,
      },
      proxy: {
        '/api': {
          target: backendProxy,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: frontendPort,
      allowedHosts: true,
    },
  }
})
