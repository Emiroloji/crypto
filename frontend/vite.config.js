import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Build output goes directly into backend's /static directory
  base: '/static/',
  build: {
    outDir: path.resolve(__dirname, './dist'),
    emptyOutDir: true,        // clears old files on every build
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          icons: ['lucide-react'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy all API calls to backend in dev
      '/status': 'http://127.0.0.1:8000',
      '/config': 'http://127.0.0.1:8000',
      '/signals': 'http://127.0.0.1:8000',
      '/positions': 'http://127.0.0.1:8000',
      '/trades': 'http://127.0.0.1:8000',
      '/performance': 'http://127.0.0.1:8000',
      '/bot': 'http://127.0.0.1:8000',
      '/killswitch': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
});
