import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,     // ⬅️ 開發模式（npm run dev）使用的 port
    host: true      // ⬅️ 對外開放（讓 Docker 容器能存取）
  },
  preview: {
    port: 3000,     // ⬅️ 預覽模式（npm run preview）使用的 port
    host: true,     // ⬅️ 同樣對外開放
    allowedHosts: ['d2es4l7u4ujgso.cloudfront.net']  // ✅ 加入這行
  }
})