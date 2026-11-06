import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Builds one script and one stylesheet, which are committed into indigo/static/rjsf/.
// Django loads them through the form widget (see indigo/forms.py).
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // The bundle is always a production build. The tests (mode "test") need React's development build, which has act().
  define: mode === 'test' ? {} : { 'process.env.NODE_ENV': '"production"' },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: './src/test-setup.js',
  },
  build: {
    outDir: '../indigo/static/rjsf',
    emptyOutDir: true,
    lib: {
      entry: './src/main.jsx',
      name: 'IndigoRjsf',
      formats: ['iife'],
      fileName: () => 'rjsf-form.js',
      cssFileName: 'rjsf-form',
    },
  },
}))
