import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig(({ mode }) => ({
  plugins: [react(), {
    name: 'public-annotator-entry',
    transformIndexHtml: { order: 'pre', handler(html) {
      return mode === 'public' ? html.replace('/src/main.tsx', '/src/main.public.tsx').replace('Administrator Portal', 'Annotation') : html;
    } },
    generateBundle(_options, bundle) {
      if (mode !== 'public') return;
      for (const output of Object.values(bundle)) {
        if (output.type !== 'chunk') continue;
        for (const id of Object.keys(output.modules)) {
          if (/layouts\/(AdminLayout|AuthLayout)|pages\/dashboard|pages\/views\/(Training|Datasets|Models|PilotResults)|pages\/auth\/(Login|Register)|router\/index|auth\/(PrivateGuard|privateSession)/.test(id.replaceAll('\\', '/'))) {
            this.error(`Admin module included in public build: ${id}`);
          }
        }
      }
    },
  }],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  build: { outDir: mode === 'public' ? 'dist-public' : 'dist-private' },
  server: { proxy: { '/api': { target: mode === 'render' ? 'https://vectofit.onrender.com' : 'http://localhost:8000', changeOrigin: true, secure: mode === 'render' } } },
}));
