import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  
  resolve: {
    alias: {
      '@': '/src',
      '@/components': '/src/components',
      '@/hooks': '/src/hooks',
      '@/utils': '/src/utils',
      '@/services': '/src/services',
      '@/types': '/src/types',
      '@/pages': '/src/pages',
      '@/stores': '/src/stores',
      '@/styles': '/src/styles'
    },
  },

  server: {
    port: 3000,
    host: '0.0.0.0',
    open: false, // Disable auto-opening browser in Docker
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});