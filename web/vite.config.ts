// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)), // ✅ 安全替代 resolve(__dirname, 'src')
    },
  },
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
      },
      // 👇 新增：将 /api 开头的请求代理到你的 FastAPI（回测服务）
      '/api': {
        target: 'http://localhost:8084', // FastAPI 默认端口
        changeOrigin: true,
        secure: false,
      }
    }
  }
});