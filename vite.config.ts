import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// 前端只打 /api/v1/*（api.ts 里本来就写死这个前缀）。
// 开发期由这里的 proxy 转给 AI 服务的薄 BFF 层（默认 127.0.0.1:8100）；
// 生产期换成网关/反向代理转发，前端代码不用改。
// 想换地址：在本地环境里设 AI_SERVICE_URL=... 再 npm run dev。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const aiTarget = env.AI_SERVICE_URL || 'http://127.0.0.1:8100'
  return {
    plugins: [vue()],
    server: {
      port: 5173,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: aiTarget,
          changeOrigin: true
        }
      }
    }
  }
})
