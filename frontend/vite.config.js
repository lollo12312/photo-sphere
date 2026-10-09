import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
      '/photos': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000'
    }
  },
  build: {
    // 分包：three.js / vue 运行时单独成 chunk，主包不再塞 571KB，浏览器可并行加载 + 命中缓存
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          'vue-vendor': ['vue', 'vue-router']
        }
      }
    }
  }
})