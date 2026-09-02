import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Dev proxy keeps the SPA same-origin with Django (session auth + CSRF).
const DJANGO = 'http://localhost:8888';

export default defineConfig({
  plugins: [react()],
  // Built assets are served by Django's staticfiles (frontend/dist is in
  // STATICFILES_DIRS), so asset URLs must live under /static/.
  base: '/static/',
  server: {
    port: 5173,
    proxy: {
      '/api': DJANGO,
      '/loginapi': DJANGO,
      '/logout': DJANGO,
      '/admin': DJANGO,
      '/static': DJANGO,
    },
  },
  build: {
    outDir: 'dist',
  },
});
