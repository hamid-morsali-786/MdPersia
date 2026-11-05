/** Production entry for the existing desktop UI and native bridge. No Vite/plugins at runtime. */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { installDesktopBridge, type Middleware } from './desktopBridge';

const dist = path.dirname(fileURLToPath(import.meta.url));
const routes: Array<{ route: string; handler: Middleware }> = [];
installDesktopBridge({ middlewares: { use: (route, handler) => routes.push({ route, handler }) } }, true);
const mime: Record<string, string> = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.png': 'image/png',
  '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.json': 'application/json' };

http.createServer((req, res) => {
  let index = 0;
  const fail = () => { if (!res.headersSent) res.writeHead(500); res.end('Desktop request failed'); };
  const next = () => {
    const entry = routes[index++];
    if (entry) {
      const original = req.url || '/';
      const pathname = original.split('?')[0];
      if (pathname !== entry.route && !pathname.startsWith(entry.route + '/')) return next();
      req.url = original.slice(entry.route.length) || '/';
      try {
        Promise.resolve(entry.handler(req, res, () => { req.url = original; next(); })).catch(fail);
      } catch { fail(); }
      return;
    }
    if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); res.end(); return; }
    try {
      const pathname = decodeURIComponent(new URL(req.url || '/', 'http://localhost').pathname);
      const file = path.resolve(dist, '.' + (pathname === '/' ? '/index.html' : pathname));
      const relative = path.relative(dist, file);
      if (relative.startsWith('..') || path.isAbsolute(relative) || !fs.statSync(file).isFile()) {
        res.writeHead(404); res.end(); return;
      }
      res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
      res.setHeader('Cache-Control', pathname.startsWith('/assets/') ? 'public, max-age=31536000, immutable' : 'no-cache');
      if (req.method === 'HEAD') res.end();
      else fs.createReadStream(file).on('error', fail).pipe(res);
    } catch { res.writeHead(404); res.end(); }
  };
  next();
}).listen(Number(process.argv[process.argv.indexOf('--port') + 1]) || 1420, '127.0.0.1');
