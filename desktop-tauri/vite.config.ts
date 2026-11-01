import { defineConfig, Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';
import fs from 'fs';

import { installDesktopBridge, projectRoot } from './desktopBridge';

const fontsDir = path.join(projectRoot, 'fonts');
const vendorDir = path.join(projectRoot, 'vendor');

function windowsNativePlugin(): Plugin {
  return {
    name: 'windows-native-bridge',
    configureServer(server) { installDesktopBridge(server); },
    configurePreviewServer(server) { installDesktopBridge(server, true); },

    // Ship the bundled fonts and Mermaid runtime into the production dist (offline viewer).
    async closeBundle() {
      if (fs.existsSync(fontsDir)) {
        const target = path.resolve(__dirname, 'dist', 'fonts');
        fs.mkdirSync(target, { recursive: true });
        for (const f of fs.readdirSync(fontsDir)) {
          if (f.toLowerCase().endsWith('.ttf')) {
            fs.copyFileSync(path.join(fontsDir, f), path.join(target, f));
          }
        }
      }
      if (fs.existsSync(vendorDir)) {
        const target = path.resolve(__dirname, 'dist', 'vendor');
        fs.mkdirSync(target, { recursive: true });
        for (const f of fs.readdirSync(vendorDir)) {
          if (f.toLowerCase().endsWith('.js')) {
            fs.copyFileSync(path.join(vendorDir, f), path.join(target, f));
          }
        }
      }
      fs.copyFileSync(path.join(projectRoot, 'src', 'fa_md_pdf', 'assets', 'mdpersia.svg'), path.resolve(__dirname, 'dist', 'mdpersia.svg'));
      fs.copyFileSync(path.join(projectRoot, 'src', 'fa_md_pdf', 'assets', 'mdpersia.ico'), path.resolve(__dirname, 'dist', 'mdpersia.ico'));
      const { build } = await import('esbuild');
      await build({ entryPoints: [path.resolve(__dirname, 'desktop-server.ts')], outfile: path.resolve(__dirname, 'dist', 'desktop-server.mjs'), bundle: true, platform: 'node', format: 'esm', target: 'node18' });
      fs.writeFileSync(path.resolve(__dirname, 'dist', '.mdpersia-build'), 'MdPersia desktop build\n');
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), windowsNativePlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    // Loopback only: the native bridge can read local files and open Explorer windows.
    host: process.env.MDPERSIA_DEV_HOST || '127.0.0.1',
  },
  preview: { port: 1420, strictPort: true, host: '127.0.0.1' },
});
