import { DOCUMENT_EXTENSIONS, isMarkdownPath } from './src/services/documentFormats';
import { previewStyles } from './src/services/previewStyles';
import { DEFAULT_APP_SETTINGS } from './src/services/appSettings';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawn, execFile, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { createInterface } from 'node:readline';
import { randomUUID } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';

const documentPattern = DOCUMENT_EXTENSIONS.map(extension => '*.' + extension).join(';');
const DOCUMENT_FILTER = 'Markdown / MDX (' + documentPattern + ')|' + documentPattern;

export type Middleware = (req: IncomingMessage, res: ServerResponse, next: () => void) => void;
export interface BridgeServer {
  middlewares: { use(route: string, handler: Middleware): void };
  httpServer?: { once(event: string, listener: () => void): unknown } | null;
}

export const projectRoot = findProjectRoot();
function findProjectRoot(): string {
  let current = path.dirname(fileURLToPath(import.meta.url));
  while (!fs.existsSync(path.join(current, 'src', 'fa_md_pdf'))) {
    const parent = path.dirname(current);
    if (parent === current) throw new Error('MdPersia source root was not found');
    current = parent;
  }
  return current;
}
const fontsDir = path.join(projectRoot, 'fonts');
const vendorDir = path.join(projectRoot, 'vendor');

/**
 * Bundled Vazirmatn weights are served from /fonts in dev and copied into dist at build,
 * so the app shell never depends on a CDN (offline viewer requirement).
 */
const FONT_WEIGHTS: Record<string, number> = {
  'Vazirmatn-Thin.ttf': 100,
  'Vazirmatn-ExtraLight.ttf': 200,
  'Vazirmatn-Light.ttf': 300,
  'Vazirmatn-Regular.ttf': 400,
  'Vazirmatn-Medium.ttf': 500,
  'Vazirmatn-SemiBold.ttf': 600,
  'Vazirmatn-Bold.ttf': 700,
  'Vazirmatn-ExtraBold.ttf': 800,
  'Vazirmatn-Black.ttf': 900,
};

function fontFaceCss(): string {
  return Object.entries(FONT_WEIGHTS)
    .map(
      ([file, weight]) =>
        `@font-face { font-family: "Vazirmatn"; src: url("/fonts/${file}") format("truetype"); font-weight: ${weight}; font-style: normal; font-display: swap; }`
    )
    .join('\n');
}

type Picker = 'files' | 'folder' | 'save';

/**
 * Windows native picker. The script travels as UTF-16LE base64 through -EncodedCommand so
 * cmd.exe cannot damage its quoting, and it always answers ok / cancelled / error so the
 * caller can report an outcome instead of leaving the button looking dead.
 */
function pickerScript(kind: Picker, title: string, filter: string, defaultPath = ''): string {
  const defaultExtension = isMarkdownPath(defaultPath) ? path.extname(defaultPath).slice(1) : 'md';
  const safe = title.replace(/'/g, "''");
  // FolderBrowserDialog only has Description; OpenFileDialog only has Title.
  const dialog =
    kind === 'folder'
      ? `$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = '${safe}'
$d.ShowNewFolderButton = $true`
      : `$d = New-Object System.Windows.Forms.${kind === 'save' ? 'SaveFileDialog' : 'OpenFileDialog'}
${kind === 'save' ? `$d.DefaultExt = "${defaultExtension}"; $d.AddExtension = $true; $d.OverwritePrompt = $false; $d.FileName = '${defaultPath.replace(/'/g, "''")}'` : '$d.Multiselect = $true'}
$d.Title = '${safe}'
$d.Filter = '${filter.replace(/'/g, "''")}'`;
  const result =
    kind === 'folder'
      ? `if ($d.SelectedPath) { [Console]::Out.Write((ConvertTo-Json -Compress @{ ok = $true; paths = @($d.SelectedPath) })) } else { [Console]::Out.Write('{"ok":false,"cancelled":true}') }`
      : `if ($d.FileNames.Count -gt 0) { [Console]::Out.Write((ConvertTo-Json -Compress @{ ok = $true; paths = $d.FileNames })) } else { [Console]::Out.Write('{"ok":false,"cancelled":true}') }`;

  return [
    "$ProgressPreference = 'SilentlyContinue'",
    '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8',
    'Add-Type -AssemblyName System.Windows.Forms | Out-Null',
    '$owner = New-Object System.Windows.Forms.Form',
    '$owner.TopMost = $true',
    '$owner.Width = 0',
    '$owner.Height = 0',
    '$owner.Opacity = 0',
    '$owner.ShowInTaskbar = $false',
    '$owner.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen',
    'try {',
    '  $owner.Show()',
    '  $owner.Activate()',
    '  $owner.BringToFront()',
    dialog,
    '  $r = $d.ShowDialog($owner)',
    `  if ($r -eq [System.Windows.Forms.DialogResult]::OK) { ${result} } else { [Console]::Out.Write('{"ok":false,"cancelled":true}') }`,
    '} catch {',
    `  [Console]::Out.Write((ConvertTo-Json -Compress @{ ok = $false; error = $_.Exception.Message }))`,
    '} finally {',
    '  if ($owner -ne $null) { $owner.Dispose() }',
    '  [System.Windows.Forms.Application]::ExitThread()',
    '}',
  ].join('\n');
}

type PickerResult = { paths?: string[]; cancelled?: boolean; error?: string };

/** execFile puts the whole argv, encoded script included, into its error text. */
function failReason(err: Error): string {
  const first = (err.message || String(err)).split('\n')[0];
  return first.length > 200 ? first.slice(0, 200) : first;
}

function runPicker(
  kind: Picker,
  title: string,
  filter: string,
  done: (r: PickerResult) => void,
  defaultPath = ''
): void {
  const encoded = Buffer.from(pickerScript(kind, title, filter, defaultPath), 'utf16le').toString('base64');
  execFile(
    'powershell.exe',
    ['-NoProfile', '-NonInteractive', '-STA', '-WindowStyle', 'Hidden', '-EncodedCommand', encoded],
    { windowsVerbatimArguments: true, maxBuffer: 8 * 1024 * 1024 },
    (err, stdout) => {
      if (err && !(stdout || '').trim()) {
        done({ error: failReason(err) });
        return;
      }
      try {
        done(JSON.parse((stdout || '').trim()) as PickerResult);
      } catch {
        done({ error: 'Native picker returned an unreadable response.' });
      }
    }
  );
}

function openInExplorerNative(rawPath: string, done: (err?: string) => void): void {
  let target = rawPath ? String(rawPath).trim() : projectRoot;
  if (!path.isAbsolute(target)) {
    target = path.resolve(projectRoot, target);
  }
  target = path.normalize(target);
  if (/^[A-Za-z]:$/.test(target)) {
    target += '\\';
  }

  // If path doesn't exist, try parent folder or fallback to projectRoot
  if (!fs.existsSync(target)) {
    const parent = path.dirname(target);
    if (fs.existsSync(parent)) {
      target = parent;
    } else {
      target = projectRoot;
    }
  }

  const isFile = fs.existsSync(target) && fs.statSync(target).isFile();

  const script = [
    "$ProgressPreference = 'SilentlyContinue'",
    `$target = '${target.replace(/'/g, "''")}'`,
    `$isDir = ${!isFile ? '$true' : '$false'}`,
    'if ($isDir) {',
    '  Start-Process -FilePath "explorer.exe" -ArgumentList "`"$target`""',
    '} else {',
    '  Start-Process -FilePath "explorer.exe" -ArgumentList ("/select,`"" + $target + "`"")',
    '}',
    'Start-Sleep -Milliseconds 350',
    'Add-Type -MemberDefinition \'[DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr hWnd, bool fAltTab);\' -Name "NativeWin" -Namespace "Win32" -ErrorAction SilentlyContinue',
    '$sh = New-Object -ComObject Shell.Application',
    'for ($i = 0; $i -lt $sh.Windows().Count; $i++) {',
    '  try {',
    '    $w = $sh.Windows().Item($i)',
    '    if ($w.HWND) {',
    '      [Win32.NativeWin]::SwitchToThisWindow([IntPtr][long]$w.HWND, $true)',
    '    }',
    '  } catch {}',
    '}',
  ].join('\r\n');

  const encoded = Buffer.from(script, 'utf16le').toString('base64');
  execFile(
    'powershell.exe',
    ['-NoProfile', '-NonInteractive', '-STA', '-WindowStyle', 'Hidden', '-EncodedCommand', encoded],
    (err) => {
      done(err ? failReason(err) : undefined);
    }
  );
}

function json(res: import('http').ServerResponse, body: unknown, status = 200): void {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(body));
}

function checkOrigin(req: import('http').IncomingMessage, res: import('http').ServerResponse): boolean {
  if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}`) {
    json(res, { error: 'Origin rejected' }, 403);
    return false;
  }
  return true;
}


function readBody(req: import('http').IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let body = '';
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > 34 * 1024 * 1024) reject(new Error('حجم درخواست بیش از حد مجاز است.'));
      else body += c;
    });
    req.on('end', () => resolve(body));
    req.on('aborted', () => reject(new Error('درخواست قطع شد.')));
    req.on('error', reject);
  });
}

/** Preview assets must reach the browser over HTTP; file:// URLs are blocked by Chromium. */
function rewriteLocalUrls(html: string): string {
  return html.replace(/file:\/\/([^"')\s]+)/g, (_m, raw: string) => {
    let p = decodeURIComponent(raw);
    if (/^\/[A-Za-z]:/.test(p)) p = p.slice(1);
    p = p.replace(/\//g, path.sep);
    if (path.dirname(p) === fontsDir) {
      return `/fonts/${path.basename(p).replace(/\\/g, '/')}`;
    }
    if (path.dirname(p) === vendorDir) {
      return `/vendor/${path.basename(p).replace(/\\/g, '/')}`;
    }
    return `/api/asset/${p.replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/')}`;
  });
}

const ASSET_ALLOWLIST = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.avif',
  '.ttf', '.otf', '.woff', '.woff2',
]);

export function installDesktopBridge(server: BridgeServer, production = false) {
  const pythonBin = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');
  const pythonPath =
    process.env.PYTHON_EXECUTABLE || (fs.existsSync(pythonBin) ? pythonBin : 'python');

  // Every python spawn needs src/ on PYTHONPATH: fa_md_pdf is a source checkout here,
  // not an installed distribution, so the fallback `python` cannot import it otherwise.
  const bridgeEnv = (): NodeJS.ProcessEnv => ({
    ...process.env,
    PYTHONPATH:
      path.join(projectRoot, 'src') +
      (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : ''),
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
  });

  // The same native bridge serves both the development UI and its production build.
  const windows = new Set<import('http').ServerResponse>();
  const windowOwners = new Map<import('http').ServerResponse, string>();
  const conversions = new Set<ReturnType<typeof spawn>>();
  const watchJobs = new Set<ReturnType<typeof spawn>>();
  const jobOwners = new Map<ReturnType<typeof spawn>, string>();
  const jobs = new Map<string, ReturnType<typeof spawn>>();
  const stopJob = (proc: ReturnType<typeof spawn>) => new Promise<void>((resolve, reject) => {
    if (proc.exitCode !== null || !proc.pid) { resolve(); return; }
    proc.once('close', () => resolve());
    if (process.platform === 'win32') {
      execFile('taskkill.exe', ['/PID', String(proc.pid), '/T', '/F'], { windowsHide: true }, error => {
        if (error && proc.exitCode === null) reject(new Error('فرآیند تبدیل متوقف نشد. دوباره تلاش کنید.'));
      });
    } else proc.kill('SIGTERM');
  });
  let shutdownTimer: ReturnType<typeof setTimeout> | undefined;
  const idleShutdown = (delay = 3000) => {
    if (!production) return;
    if (shutdownTimer) clearTimeout(shutdownTimer);
    shutdownTimer = setTimeout(() => {
      if (windows.size) return;
      // A continuous watch belongs to its application window, not an invisible daemon.
      for (const job of watchJobs) void stopJob(job).catch(() => {});
      if (conversions.size) return idleShutdown();
      process.exit(0);
    }, delay);
    shutdownTimer.unref();
  };
  // Allow ample time for the first browser window to start on a cold machine.
  idleShutdown(60000);

  server.middlewares.use('/api/health', (_req, res) => {
    json(res, { app: 'MdPersia', mode: production ? 'production' : 'development', windows: windows.size, pid: process.pid, rendererPid: worker?.pid });
  });
  server.middlewares.use('/api/open-files', (req, res) => {
    const owner = new URL(req.url || '', 'http://localhost').searchParams.get('window') || '';
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
    res.write('data: {"ready":true}\n\n');
    windows.add(res);
    windowOwners.set(res, owner);
    if (shutdownTimer) clearTimeout(shutdownTimer);
    const keepAlive = setInterval(() => res.write(': keep-alive\n\n'), 20000);
    req.on('close', () => {
      clearInterval(keepAlive);
      windows.delete(res);
      windowOwners.delete(res);
      setTimeout(() => {
        if ([...windowOwners.values()].includes(owner)) return;
        for (const job of watchJobs) if (jobOwners.get(job) === owner) void stopJob(job).catch(() => {});
      }, 1000).unref();
      if (windows.size === 0) idleShutdown();
    });
  });
  server.middlewares.use('/api/open-file', async (req, res) => {
    if (req.method !== 'POST') return json(res, { delivered: false }, 405);
    try {
      const body = JSON.parse(await readBody(req));
      const file = typeof body.path === 'string' ? path.resolve(body.path) : '';
      if (!isMarkdownPath(file) || !fs.statSync(file).isFile()) {
        return json(res, { delivered: false }, 400);
      }
      for (const client of windows) client.write(`data: ${JSON.stringify({ path: file })}\n\n`);
      json(res, { delivered: windows.size > 0 });
    } catch { json(res, { delivered: false }, 400); }
  });
  server.middlewares.use('/mdpersia.svg', (_req, res) => {
    res.setHeader('Content-Type', 'image/svg+xml');
    fs.createReadStream(path.join(projectRoot, 'src', 'fa_md_pdf', 'assets', 'mdpersia.svg')).pipe(res);
  });
  server.middlewares.use('/mdpersia.ico', (_req, res) => {
    res.setHeader('Content-Type', 'image/x-icon');
    fs.createReadStream(path.join(projectRoot, 'src', 'fa_md_pdf', 'assets', 'mdpersia.ico')).pipe(res);
  });
  server.middlewares.use('/mdpersia.png', (_req, res) => {
    res.setHeader('Content-Type', 'image/png');
    fs.createReadStream(path.join(projectRoot, 'src', 'fa_md_pdf', 'assets', 'mdpersia.png')).pipe(res);
  });

  // Bundled fonts, served with CORS + cache headers for the preview iframe.
  server.middlewares.use('/fonts', (req, res, next) => {
    const cleanUrl = (req.url || '').split('?')[0].replace(/^\//, '');
    const fontFile = path.join(fontsDir, cleanUrl);
    if (cleanUrl && fs.existsSync(fontFile) && fs.statSync(fontFile).isFile()) {
      res.setHeader('Content-Type', 'font/ttf');
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
      fs.createReadStream(fontFile).pipe(res);
    } else {
      next();
    }
  });

  // 1. Native Windows folder picker.
  server.middlewares.use('/api/pick-folder', async (req, res) => {
    const url = new URL(req.url || '', 'http://localhost');
    const title = url.searchParams.get('title') || 'انتخاب پوشه حاوی اسناد';
    runPicker('folder', title, '', (r) => {
      if (r.error) return json(res, { path: '', error: r.error });
      json(res, { path: r.paths?.[0] || '', cancelled: !!r.cancelled });
    });
  });

  // 1b. Bundled Mermaid runtime so diagrams render without a CDN.
  server.middlewares.use('/vendor', (req, res, next) => {
    const cleanUrl = (req.url || '').split('?')[0].replace(/^\//, '');
    const file = path.join(vendorDir, cleanUrl);
    if (cleanUrl && fs.existsSync(file) && fs.statSync(file).isFile()) {
      res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
      fs.createReadStream(file).pipe(res);
    } else {
      next();
    }
  });

  // 2. Native Windows multi-file picker.
  server.middlewares.use('/api/pick-save-file', (req, res) => {
    const defaultPath = new URL(req.url || '', 'http://localhost').searchParams.get('defaultPath') || '';
    runPicker('save', 'ذخیرهٔ یک نسخهٔ Markdown', DOCUMENT_FILTER, r =>
      json(res, { path: r.paths?.[0] || '', cancelled: !!r.cancelled, error: r.error }), defaultPath);
  });

  server.middlewares.use('/api/pick-files', async (req, res) => {
    const url = new URL(req.url || '', 'http://localhost');
    const exts = (url.searchParams.get('exts') || DOCUMENT_EXTENSIONS.join(','))
      .split(',')
      .map((e) => e.trim().replace(/^\./, ''))
      .filter(Boolean);
    const pattern = exts.map((e) => `*.${e}`).join(';');
    const filter = `Markdown Files (${pattern})|${pattern}|All Files (*.*)|*.*`;
    const title = url.searchParams.get('title') || 'انتخاب اسناد مارک‌داون';

    runPicker('files', title, filter, (r) => {
      if (r.error) return json(res, { files: [], error: r.error });
      const files = (r.paths || []).filter(Boolean).map((f) => {
        const stat = fs.existsSync(f) ? fs.statSync(f) : { size: 0 };
        return {
          name: path.basename(f),
          path: f.replace(/\\/g, '/'),
          sizeBytes: stat.size,
          sizeStr: `${(stat.size / 1024).toFixed(1)} KB`,
        };
      });
      json(res, { files, cancelled: !!r.cancelled });
    });
  });

  // 3. Recursive folder scan.
  server.middlewares.use('/api/scan-folder', async (req, res) => {
    if (!checkOrigin(req, res)) return;
    try {
      const { folderPath, recursive = true } = JSON.parse((await readBody(req)) || '{}');
      if (!folderPath || !fs.existsSync(folderPath)) {
        // A missing folder is a failure, not an empty result: never report it as
        // "no markdown found", which is what made the button look dead.
        return json(res, { files: [], error: 'Folder does not exist' }, 404);
      }

      const entries = fs.readdirSync(folderPath, {
        recursive: Boolean(recursive),
        withFileTypes: true,
      });
      const files = entries
        .filter((e) => e.isFile() && isMarkdownPath(e.name))
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
      json(res, { files });
    } catch (e: any) {
      json(res, { files: [], error: e.message }, 500);
    }
  });

  // 4. Reveal in Windows Explorer with foreground activation and path resolution.
  server.middlewares.use('/api/open-folder', async (req, res) => {
    if (!checkOrigin(req, res)) return;
    try {
      const { targetPath } = JSON.parse((await readBody(req)) || '{}');
      openInExplorerNative(targetPath, (err) => {
        if (err) {
          json(res, { success: false, error: err }, 500);
        } else {
          json(res, { success: true });
        }
      });
    } catch (e: any) {
      json(res, { success: false, error: e.message }, 500);
    }
  });

  // 5. Raw markdown text for the source view.
  server.middlewares.use('/api/read-file', async (req, res) => {
    if (!checkOrigin(req, res)) return;
    try {
      const { filePath } = JSON.parse((await readBody(req)) || '{}');
      if (filePath && fs.existsSync(filePath)) {
        const bytes = fs.readFileSync(filePath);
        let content: string;
        try { content = new TextDecoder('utf-8', { fatal: true }).decode(bytes); }
        catch { content = new TextDecoder('windows-1256').decode(bytes); }
        json(res, { ok: true, content });
      } else {
        json(res, { ok: false, error: 'File not found' }, 404);
      }
    } catch (e: any) {
      json(res, { ok: false, error: e.message }, 500);
    }
  });

  // 5a. Binary preview assets (images/fonts) referenced by file:// in the generated HTML.
  server.middlewares.use('/api/asset', (req, res) => {
    const url = new URL(req.url || '', 'http://localhost');
    const p = url.searchParams.get('path') || decodeURIComponent((req.url || '').split('?')[0].slice(1));
    if (!p || !fs.existsSync(p) || !fs.statSync(p).isFile()) {
      res.statusCode = 404;
      res.end('Not found');
      return;
    }
    if (!ASSET_ALLOWLIST.has(path.extname(p).toLowerCase())) {
      res.statusCode = 403;
      res.end('Forbidden');
      return;
    }
    const type = path.extname(p).toLowerCase() === '.svg' ? 'image/svg+xml' : 'application/octet-stream';
    res.setHeader('Content-Type', type);
    res.setHeader('Cache-Control', 'no-cache');
    fs.createReadStream(p).pipe(res);
  });

  // Only the explicitly requested file belongs to this open request; never replay a launch environment.
  server.middlewares.use('/api/initial-items', async (req, res) => {
    type InitialItem = {
      id: string;
      name: string;
      path: string;
      sizeBytes: number;
      sizeStr: string;
      status: string;
      relativePath: string;
    };
    const toItem = (abs: string, id: string): InitialItem => {
      const stat = fs.statSync(abs);
      return {
        id,
        name: path.basename(abs),
        path: abs.replace(/\\/g, '/'),
        sizeBytes: stat.size,
        sizeStr: `${(stat.size / 1024).toFixed(1)} KB`,
        status: 'pending',
        relativePath: path.relative(projectRoot, abs).replace(/\\/g, '/') || path.basename(abs),
      };
    };

    const url = new URL(req.url || '', 'http://localhost');
    const wanted = url.searchParams.get('file');
    if (!wanted) return json(res, { items: [], viewer: false });
    try {
      const file = path.resolve(wanted);
      if (!isMarkdownPath(file) || !fs.statSync(file).isFile()) throw new Error('Not a Markdown file');
      json(res, { items: [toItem(file, `document:${file}`)], viewer: true });
    } catch {
      json(res, { items: [], viewer: false, error: 'فایل یافت نشد یا قابل خواندن نیست.' }, 404);
    }
  });

  let worker: ChildProcessWithoutNullStreams | null = null;
  let workerSequence = 0;
  const pending = new Map<number, { resolve(reply: any): void; reject(error: Error): void; timer: ReturnType<typeof setTimeout> }>();
  const startWorker = () => {
    if (worker) return worker;
    const child = spawn(pythonPath, ['-u', '-m', 'fa_md_pdf.preview_worker', projectRoot],
      { cwd: projectRoot, env: bridgeEnv(), windowsHide: true });
    worker = child;
    let stderr = '';
    child.stderr.on('data', data => { stderr = (stderr + data.toString('utf8')).slice(-4000); });
    const lines = createInterface({ input: child.stdout });
    lines.on('line', line => {
      try {
        const reply = JSON.parse(line);
        const request = pending.get(reply.id);
        if (!request) return;
        pending.delete(reply.id); clearTimeout(request.timer);
        if (reply.error) request.reject(Object.assign(new Error(reply.error), { code: reply.code })); else request.resolve(reply);
      } catch { /* An invalid response is bounded by the request timeout. */ }
    });
    const stopped = () => {
      if (worker !== child) return;
      worker = null;
      for (const request of pending.values()) {
        clearTimeout(request.timer);
        request.reject(new Error(stderr || 'موتور پیش‌نمایش متوقف شد؛ دوباره تلاش کنید.'));
      }
      pending.clear(); lines.close();
    };
    child.once('error', stopped); child.once('exit', stopped);
    child.stdin.on('error', stopped);
    return child;
  };
  const workerRequest = (payload: Record<string, unknown>): Promise<any> => new Promise((resolve, reject) => {
    const child = startWorker();
    const id = ++workerSequence;
    const timer = setTimeout(() => { child.kill(); }, 30000);
    timer.unref();
    pending.set(id, { resolve, reject, timer });
    child.stdin.write(JSON.stringify({ ...payload, id }) + '\n');
  });
  const renderWithWorker = (file: string): Promise<string> => workerRequest({ path: file }).then(reply => reply.html);
  server.middlewares.use('/api/document', async (req, res) => {
    if (req.method !== 'POST') return json(res, { error: 'POST required' }, 405);
    // A different website must not be able to submit writes to the local bridge.
    if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}`) return json(res, { error: 'Origin rejected' }, 403);
    if (!(req.headers['content-type'] || '').startsWith('application/json')) return json(res, { error: 'JSON required' }, 415);
    try {
      const body = JSON.parse(await readBody(req));
      if (body.operation !== 'read' && body.operation !== 'save') return json(res, { error: 'Invalid operation' }, 400);
      const reply = await workerRequest(body);
      json(res, { document: reply.document });
    } catch (error: any) { json(res, { error: error.message, code: error.code || 'IO' }, error.code === 'CONFLICT' ? 409 : 400); }
  });
  server.middlewares.use('/api/preview-draft', async (req, res) => {
    if (req.method !== 'POST') return json(res, { error: 'POST required' }, 405);
    if (!checkOrigin(req, res)) return;
    try {
      const { path: file, text } = JSON.parse(await readBody(req));
      if (typeof text !== 'string') return json(res, { error: 'Text required' }, 400);
      const reply = await workerRequest({ path: file, text });
      json(res, { html: rewriteLocalUrls(reply.html) });
    } catch (error: any) { json(res, { error: error.message }, 400); }
  });
  // Import the renderer while the existing application window starts.
  startWorker();
  const closeWorker = () => worker?.kill();
  process.once('exit', closeWorker);
  server.httpServer?.once('close', () => { process.removeListener('exit', closeWorker); closeWorker(); });

  // Bound the raw HTML cache by both document count and bytes. The file stamp
  // invalidates edits, and sharing the promise coalesces concurrent requests.
  const previews = new Map<string, { stamp: string; html: Promise<string>; bytes: number }>();
  const forget = (key: string) => { previews.delete(key); };
  const renderPreview = (file: string): Promise<string> => {
    const stat = fs.statSync(file, { bigint: true });
    const stamp = `${stat.mtimeNs}:${stat.size}`;
    const hit = previews.get(file);
    if (hit?.stamp === stamp) {
      previews.delete(file); previews.set(file, hit);
      return hit.html;
    }
    forget(file);
    const entry = { stamp, bytes: 0, html: renderWithWorker(file) };
    previews.set(file, entry);
    while (previews.size > 8) forget(previews.keys().next().value!);
    entry.html = entry.html.then((html) => {
      if (previews.get(file) === entry) {
        entry.bytes = Buffer.byteLength(html);
        while ([...previews.values()].reduce((sum, item) => sum + item.bytes, 0) > 8 * 1024 * 1024) {
          forget(previews.keys().next().value!);
        }
      }
      return html;
    }, (err) => { if (previews.get(file) === entry) forget(file); throw err; });
    return entry.html;
  };

  // 5c. Preview HTML rendered by the existing Python engine, with local-only fonts.
  server.middlewares.use('/api/preview-html', (req, res) => {
    const url = new URL(req.url || '', `http://${req.headers.host || 'localhost'}`);
    const targetFile = url.searchParams.get('path');
    const theme = url.searchParams.get('theme') || 'dark';
    const zoomRaw = Number(url.searchParams.get('zoom') || '100');
    const zoom = Number.isFinite(zoomRaw) ? Math.min(250, Math.max(50, Math.round(zoomRaw))) : 100;

    const fail = (status: number, msg: string) => {
      res.statusCode = status;
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.end(
        `<div dir="rtl" style="font-family:sans-serif;padding:24px;color:#b91c1c;">${msg}</div>`
      );
    };
    if (!targetFile || !fs.existsSync(targetFile) || !fs.statSync(targetFile).isFile()) return fail(404, 'فایل یافت نشد.');

    renderPreview(path.resolve(targetFile)).then((html) => {
      const shell = [
        '<style>',
        fontFaceCss(),
        'html { zoom: ' + zoom + '%; }',
        'html, body { margin: 0; padding: 0; }',
        'html, body, .markdown-body, h1, h2, h3, h4, h5, h6, p, li, td, th, blockquote, figcaption, div, span {',
        '  font-family: "Vazirmatn", "Segoe UI", Tahoma, sans-serif !important;',
        '}',
        'pre { font-family: "Cascadia Mono", Consolas, monospace !important; direction: ltr !important; text-align: left !important; unicode-bidi: isolate !important; }',
        'code { font-family: "Cascadia Mono", Consolas, monospace !important; unicode-bidi: isolate !important; }',
        '.markdown-body { padding: 36px 44px !important; max-width: 860px !important;',
        '  margin: 0 auto !important; box-sizing: border-box !important; min-height: 100vh; }',
        'img { max-width: 100%; height: auto; }',
        ':is([dir="ltr"]:not(html, body), [dir="ltr"]:not(html, body) :is(p, li, dd, dt, blockquote, h1, h2, h3, h4, h5, h6, th, td)) {',
        '  direction: ltr !important; text-align: left !important; unicode-bidi: isolate;',
        '}',
        ':is([dir="rtl"]:not(html, body), [dir="rtl"]:not(html, body) :is(p, li, dd, dt, blockquote, h1, h2, h3, h4, h5, h6, th, td)) {',
        '  direction: rtl !important; text-align: right !important; unicode-bidi: isolate;',
        '}',
        'ul[dir="rtl"], ol[dir="rtl"] { padding-inline-start: 1.6em !important; padding-inline-end: 0 !important; direction: rtl !important; }',
        'ul[dir="ltr"], ol[dir="ltr"] { padding-inline-start: 1.6em !important; padding-inline-end: 0 !important; direction: ltr !important; }',
        '</style>',
      ].join('\n');
      let out = rewriteLocalUrls(html);
      out = out.replace('</head>', shell + '<style>' + previewStyles(theme, zoom, DEFAULT_APP_SETTINGS) + '</style></head>');
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Cache-Control', 'no-store');
      res.end(out);
    }).catch((err) => fail(500, `خطا در ساخت پیش‌نمایش: ${String(err.message).replace(/[<>&]/g, '')}`));
  });

  server.middlewares.use('/api/cancel-job', async (req, res) => {
    if (req.method !== 'POST') return json(res, { stopped: false }, 405);
    if (!checkOrigin(req, res)) return;
    try {
      const { id } = JSON.parse(await readBody(req));
      const job = jobs.get(id);
      if (job) await stopJob(job);
      json(res, { stopped: true });
    } catch (error: any) { json(res, { stopped: false, error: error.message }, 500); }
  });

  // 6. Conversion execution with SSE streaming.
  server.middlewares.use('/api/convert-job', async (req, res) => {
    if (!checkOrigin(req, res)) return;
    try {
      const { args, id: requestedId, windowSession } = JSON.parse((await readBody(req)) || '{}');
      if (!Array.isArray(args)) return void ((res.statusCode = 400), res.end('Missing args'));

      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      const id = typeof requestedId === 'string' ? requestedId : randomUUID();
      if (jobs.has(id)) return json(res, { error: 'Duplicate job' }, 409);
      const proc = spawn(pythonPath, ['-u', '-m', 'fa_md_pdf.cli', ...args], {
        cwd: projectRoot,
        env: bridgeEnv(),
        windowsHide: true,
      });
      conversions.add(proc);
      if (args.includes('--watch') || args.includes('-w')) watchJobs.add(proc);
      jobs.set(id, proc);
      jobOwners.set(proc, typeof windowSession === 'string' ? windowSession : '');
      proc.stdout.on('data', (c) =>
        res.write(`data: ${JSON.stringify({ type: 'stdout', text: c.toString('utf-8') })}\n\n`)
      );
      let stderrTail = '';
      proc.stderr.on('data', (c) => {
        const text = c.toString('utf-8');
        stderrTail = (stderrTail + text).slice(-4000);
        res.write(`data: ${JSON.stringify({ type: 'stderr', text })}\n\n`);
      });
      proc.on('close', (code) => {
        jobOwners.delete(proc);
        watchJobs.delete(proc);
        jobs.delete(id);
        conversions.delete(proc);
        if (code) {
          // A raw traceback is not actionable; name the interpreter and the fix.
          const missing = /ModuleNotFoundError: No module named '([^']+)'/.exec(stderrTail);
          if (missing) {
            const hint =
              `محیط پایتونِ «${pythonPath}» ماژول «${missing[1]}» را ندارد. ` +
              `با متغیر PYTHON_EXECUTABLE مسیر محیطِ درست را مشخص کن.\n`;
            res.write(`data: ${JSON.stringify({ type: 'stderr', text: hint })}\n\n`);
          }
        }
        res.write(`data: ${JSON.stringify({ type: 'exit', code })}\n\n`);
        res.end();
      });
      proc.on('error', (err) => {
        jobOwners.delete(proc);
        watchJobs.delete(proc);
        jobs.delete(id);
        conversions.delete(proc);
        res.write(`data: ${JSON.stringify({ type: 'error', error: err.message })}\n\n`);
        res.end();
      });
    } catch (err: any) {
      res.statusCode = 500;
      res.end(err.message);
    }
  });
}
