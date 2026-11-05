import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    ws: true
  },
  // 商品图片使用独立图片服务器。开发环境将同源 /images 请求转发到 8001，
  // 避免浏览器错误地从 Vite 的 5173 端口读取图片。
  '/images': {
    target: 'http://127.0.0.1:8001',
    changeOrigin: true
  }
}

export default defineConfig({
  plugins: [vue()],

  esbuild: {
    pure: ['console.log', 'console.debug']
  },

  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy
  },

  preview: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy
  }
})
