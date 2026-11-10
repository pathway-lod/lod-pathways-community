import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' so the built folder works from any path (e.g. a GitHub Pages subfolder)
// two pages: index.html (card viewer) and global.html (global view test, Cytoscape.js)
export default defineConfig({
  plugins: [react()], base: './',
  build: { rollupOptions: { input: { main: 'index.html', global: 'global.html' } } },
});
