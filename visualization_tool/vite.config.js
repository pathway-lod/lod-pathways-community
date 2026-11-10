import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' so the built folder works from any path (e.g. a GitHub Pages subfolder)
export default defineConfig({ plugins: [react()], base: './' });
