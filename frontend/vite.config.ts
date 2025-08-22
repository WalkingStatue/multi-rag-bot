import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Check if running in Docker (no proxy needed)
  const isDocker = process.env.DOCKER === 'true' || mode === 'docker';
  const isExternalAccess = mode === 'shared' || mode === 'devtunnels';
  
  return {
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
      host: '0.0.0.0', // Always allow external connections in Docker
      open: false, // Don't auto-open in Docker
      // Only use proxy when NOT in Docker and NOT in external access modes
      ...(!isDocker && !isExternalAccess ? {
        proxy: {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ''),
          },
        },
      } : {}),
    },
  };
});
