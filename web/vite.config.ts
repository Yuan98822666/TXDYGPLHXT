// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // ✅ 只代理 /snapshot/ 开头的 API 路径
      '/snapshot/': {
        target: 'http://localhost:8084',
        changeOrigin: true,
        secure: false,
        // ✅ 关键：只匹配带斜杠的路径
      }
    }
  }
});