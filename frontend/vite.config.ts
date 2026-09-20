import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    proxy: {
      // 开发环境代理到后端 FastAPI（本机 localhost 解析异常，固定用 127.0.0.1:8010）
      '/api': 'http://127.0.0.1:8010',
    },
  },
})
