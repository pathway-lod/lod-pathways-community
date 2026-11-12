import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' so the built folder works from any path (e.g. a GitHub Pages subfolder)
// worker: the in-browser SHACL validation runs in a module Web Worker, loaded only when the button is clicked
// two pages: index.html (card viewer) and global.html (global view test, Cytoscape.js)
export default defineConfig({
  plugins: [react()], base: './',
  build: { rollupOptions: { input: { main: 'index.html', global: 'global.html' } } },
  // the SHACL validation worker (src/validation/worker.js) imports ES modules and is split into its own chunk
  worker: { format: 'es' },
});
