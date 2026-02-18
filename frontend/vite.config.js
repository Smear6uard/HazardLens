import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        configure: (proxy) => {
          // Prevent proxy from buffering SSE responses
          proxy.on('proxyRes', (proxyRes, req, res) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              res.setHeader('Cache-Control', 'no-cache, no-transform');
              res.setHeader('Connection', 'keep-alive');
              res.setHeader('X-Accel-Buffering', 'no');
            }
          });
        },
      },
      '/ws': {
        target: 'ws://localhost:8001',
        ws: true,
      },
    },
  },
});
