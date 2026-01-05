// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 将 /snapshot 开头的请求代理到后端
      '/snapshot': {
        target: 'http://localhost:8084',
        changeOrigin: true,
        secure: false,
      },
      // 将 /hot 开头的请求也代理到后端
      '/hot': {
        target: 'http://localhost:8084',
        changeOrigin: true,
        secure: false,
      },
      // 如果以后还有其他 API，比如 /sentiment，也可以加进来
      '/sentiment': {
        target: 'http://localhost:8084',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})