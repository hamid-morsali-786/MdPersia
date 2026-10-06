import { defineConfig, Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';
import { exec, spawn } from 'child_process';
import fs from 'fs';

function windowsNativePlugin(): Plugin {
  const projectRoot = path.resolve(__dirname, '..');
  const pythonBin = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');
  const pythonPath = fs.existsSync(pythonBin) ? pythonBin : 'python';

  return {
    name: 'windows-native-bridge',
    configureServer(server) {
      // 1. Pick a directory via native Windows dialog
      server.middlewares.use('/api/pick-folder', (_req, res) => {
        const pyCmd = `import tkinter.filedialog as fd, tkinter as tk; r=tk.Tk(); r.withdraw(); r.attributes('-topmost', True); p=fd.askdirectory(title='انتخاب پوشه'); print(p)`;
        exec(`"${pythonPath}" -c "${pyCmd}"`, (_err, stdout) => {
          const selected = (stdout || '').trim();
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ path: selected }));
        });
      });

      // 2. Pick files via native Windows dialog with real file stats
      server.middlewares.use('/api/pick-files', (_req, res) => {
        const pyCmd = `import tkinter.filedialog as fd, tkinter as tk, json; r=tk.Tk(); r.withdraw(); r.attributes('-topmost', True); files=fd.askopenfilenames(title='انتخاب فایل‌های مارک‌داون', filetypes=[('Markdown Files', '*.md *.markdown')]); print(json.dumps(list(files)))`;
        exec(`"${pythonPath}" -c "${pyCmd}"`, (_err, stdout) => {
          try {
            const rawFiles: string[] = JSON.parse((stdout || '[]').trim());
            const files = rawFiles.map((f) => {
              const stat = fs.existsSync(f) ? fs.statSync(f) : { size: 1024 };
              return {
                name: path.basename(f),
                path: f.replace(/\\/g, '/'),
                sizeBytes: stat.size,
                sizeStr: `${(stat.size / 1024).toFixed(1)} KB`,
              };
            });
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ files }));
          } catch {
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ files: [] }));
          }
        });
      });

      // 3. Scan directory with recursive option
      server.middlewares.use('/api/scan-folder', (req, res) => {
        let body = '';
        req.on('data', (c) => { body += c; });
        req.on('end', () => {
          try {
            const { folderPath, recursive = true } = JSON.parse(body || '{}');
            if (!folderPath || !fs.existsSync(folderPath)) {
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ files: [] }));
              return;
            }

            const entries = fs.readdirSync(folderPath, {
              recursive: Boolean(recursive),
              withFileTypes: true,
            });
            const files = entries
              .filter((e) => e.isFile() && (e.name.endsWith('.md') || e.name.endsWith('.markdown')))
              .map((e) => {
                const parent = (e as any).parentPath || folderPath;
                const fullPath = path.join(parent, e.name);
                const stat = fs.statSync(fullPath);
                return {
                  name: e.name,
                  path: fullPath.replace(/\\/g, '/'),
                  sizeBytes: stat.size,
                  relativePath: path.relative(folderPath, fullPath).replace(/\\/g, '/'),
                };
              });
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ files }));
          } catch {
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ files: [] }));
          }
        });
      });

      // 4. Open folder or select file in Windows Explorer
      server.middlewares.use('/api/open-folder', (req, res) => {
        let body = '';
        req.on('data', (c) => { body += c; });
        req.on('end', () => {
          try {
            const { targetPath } = JSON.parse(body || '{}');
            const p = (targetPath || projectRoot).replace(/\//g, '\\');
            exec(`explorer.exe "${p}"`);
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ success: true }));
          } catch {
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ success: false }));
          }
        });
      });

      // 5. Read real file content from disk for preview
      server.middlewares.use('/api/read-file', (req, res) => {
        let body = '';
        req.on('data', (c) => { body += c; });
        req.on('end', () => {
          try {
            const { filePath } = JSON.parse(body || '{}');
            if (filePath && fs.existsSync(filePath)) {
              const content = fs.readFileSync(filePath, 'utf-8');
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ ok: true, content }));
            } else {
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ ok: false, error: 'File not found' }));
            }
          } catch (e: any) {
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ ok: false, error: e.message }));
          }
        });
      });

      // 6. REAL conversion execution with SSE streaming
      server.middlewares.use('/api/convert-job', (req, res) => {
        let body = '';
        req.on('data', (c) => { body += c; });
        req.on('end', () => {
          try {
            const { args } = JSON.parse(body || '{}');
            if (!Array.isArray(args)) {
              res.statusCode = 400;
              res.end('Missing args');
              return;
            }

            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');

            const pyArgs = ['-m', 'fa_md_pdf.cli', ...args];
            const proc = spawn(pythonPath, pyArgs, {
              cwd: projectRoot,
              env: {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                PYTHONUTF8: '1',
              },
            });

            proc.stdout.on('data', (chunk) => {
              const text = chunk.toString('utf-8');
              res.write(`data: ${JSON.stringify({ type: 'stdout', text })}\n\n`);
            });

            proc.stderr.on('data', (chunk) => {
              const text = chunk.toString('utf-8');
              res.write(`data: ${JSON.stringify({ type: 'stderr', text })}\n\n`);
            });

            proc.on('close', (code) => {
              res.write(`data: ${JSON.stringify({ type: 'exit', code })}\n\n`);
              res.end();
            });

            proc.on('error', (err) => {
              res.write(`data: ${JSON.stringify({ type: 'error', error: err.message })}\n\n`);
              res.end();
            });
          } catch (err: any) {
            res.statusCode = 500;
            res.end(err.message);
          }
        });
      });
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
    host: '0.0.0.0',
  },
});
