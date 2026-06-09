import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/annotation/',
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/annotation/api': {
        target: 'http://localhost:8001',
        rewrite: (path: string) => path.replace(/^\/annotation/, ''),
      },
    },
  },
})
