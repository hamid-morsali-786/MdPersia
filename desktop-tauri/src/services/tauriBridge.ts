import { previewStyles } from './previewStyles';
import { QueueItem, ConvertOptions, LogEntry, ProgressEvent } from '../types';
import { buildCliArgs } from './cliTranslator';
import { DEFAULT_APP_SETTINGS, type ReadingSettings } from './appSettings';
import { createWatchObserver, stderrLogLevel } from './consoleReport';

export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

let activeCancellation = false;
let cancelCurrentJob: (() => Promise<void>) | null = null;
const windowSession = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

const getTimestamp = (): string => new Date().toLocaleTimeString();

const log = (
  onLog: (e: LogEntry) => void,
  level: LogEntry['level'],
  message: string
): void => onLog({ id: `${level}-${Date.now()}-${Math.random()}`, timestamp: getTimestamp(), level, message });

/**
 * Executes a single conversion job via Vite server streaming endpoint.
 */
async function executeWebConversionJob(
  args: string[],
  onLog: (entry: LogEntry) => void,
  observeStdout: (text: string) => void
): Promise<number> {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const response = await fetch('/api/convert-job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ args, id, windowSession }),
  });
  if (!response.ok) throw new Error(`Conversion request failed: HTTP ${response.status}`);
  cancelCurrentJob = async () => {
    const stopped = await fetch('/api/cancel-job', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) });
    if (!stopped.ok) throw new Error('توقف تبدیل انجام نشد؛ دوباره تلاش کنید.');
  };
  if (activeCancellation) await cancelCurrentJob();

  if (!response.body) {
    throw new Error('ReadableStream not supported');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let exitCode: number | null = null;
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const match = line.match(/^data: (.*)$/m);
      if (!match) continue;
      try {
        const payload = JSON.parse(match[1]);
        if (payload.type === 'stdout') {
          observeStdout(payload.text);
          onLog({
            id: `stdout-${Date.now()}-${Math.random()}`,
            timestamp: getTimestamp(),
            level: 'info',
            message: payload.text.trimEnd(),
          });
        } else if (payload.type === 'stderr') {
          onLog({
            id: `stderr-${Date.now()}-${Math.random()}`,
            timestamp: getTimestamp(),
            level: stderrLogLevel(payload.text),
            message: payload.text.trimEnd(),
          });
        } else if (payload.type === 'exit') {
          exitCode = typeof payload.code === 'number' ? payload.code : 1;
        } else if (payload.type === 'error') {
          onLog({
            id: `err-${Date.now()}`,
            timestamp: getTimestamp(),
            level: 'error',
            message: payload.error,
          });
          exitCode = 1;
        }
      } catch {
        // Ignore json parse error
      }
    }
  }

  if (exitCode === null) throw new Error('ارتباط با موتور پیش از دریافت نتیجهٔ تبدیل قطع شد.');
  return exitCode;
}

/**
 * Executes conversion batch with REAL process execution in both Dev and Tauri modes.
 */
export async function executeConversion(
  items: QueueItem[],
  options: ConvertOptions,
  onProgress: (evt: ProgressEvent) => void,
  publishLog: (entry: LogEntry) => void
): Promise<void> {
  activeCancellation = false;
  let successCount = 0;
  let failCount = 0;
  const batchId = `batch-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  let logSequence = 0;
  let currentItem: QueueItem | null = null;
  const onLog = (entry: LogEntry) => publishLog({ ...entry, id: `${batchId}-${logSequence++}`, batchId,
    ...(currentItem ? { fileName: currentItem.name, filePath: currentItem.path } : {}) });
  const cancelled = () => {
    currentItem = null;
    onProgress({ type: 'cancelled' });
    log(onLog, 'warn', options.watch ? 'پایش زنده توسط کاربر متوقف شد.' : 'تبدیل توسط کاربر متوقف شد.');
  };

  onLog({
    id: `log-${Date.now()}-start`,
    timestamp: getTimestamp(),
    level: 'info',
    kind: 'batch-start',
    message: `تبدیل ${items.length} سند به ${options.format === 'wrap-rtl' ? 'Markdown راست‌چین' : options.format.toUpperCase()} آغاز شد.`,
  });

  for (let i = 0; i < items.length; i++) {
    if (activeCancellation) {
      cancelled();
      return;
    }

    const item = items[i];
    currentItem = item;
    const args = buildCliArgs(item, options);
    const observeStdout = options.watch ? createWatchObserver(watching => onProgress({
      type: watching ? 'watching' : 'progress', itemId: item.id, file: item.name,
      total: items.length, completed: i,
    })) : () => {};

    onProgress({
      type: 'progress',
      file: item.name,
      itemId: item.id,
      total: items.length,
      completed: i,
    });

    onLog({
      id: `log-${Date.now()}-cmd`,
      timestamp: getTimestamp(),
      level: 'info',
      kind: 'command',
      message: `fa-md-pdf ${args.join(' ')}`,
    });

    try {
      let code = 0;
      if (isTauri()) {
        const { invoke, Channel } = await import('@tauri-apps/api/core');
        const id = `conversion-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const events = new Channel<{ type: 'stdout' | 'stderr'; text: string }>();
        events.onmessage = event => {
          if (event.type === 'stdout' && !activeCancellation) observeStdout(event.text);
          log(onLog, event.type === 'stderr' ? stderrLogLevel(event.text) : 'info', event.text.trimEnd());
        };
        const pending = invoke<number>('run_conversion', { id, args, events });
        cancelCurrentJob = () => invoke<void>('cancel_conversion', { id });
        if (activeCancellation) await cancelCurrentJob();
        code = await pending;
      } else {
        code = await executeWebConversionJob(args, onLog, observeStdout);
      }

      cancelCurrentJob = null;
      if (activeCancellation) { cancelled(); return; }
      if (code === 0) {
        successCount++;
        onProgress({
          type: 'success',
          file: item.name,
          itemId: item.id,
          destPath: item.path,
        });
        onLog({
          id: `log-${Date.now()}-ok`,
          timestamp: getTimestamp(),
          level: 'success',
          message: 'تبدیل سند با موفقیت انجام شد.',
        });
      } else {
        failCount++;
        onProgress({
          type: 'error',
          file: item.name,
          itemId: item.id,
          error: `Process exited with error code ${code}`,
        });
        onLog({
          id: `log-${Date.now()}-err`,
          timestamp: getTimestamp(),
          level: 'error',
          message: `تبدیل سند با کد خروج ${code} متوقف شد. جزئیات موتور را در رویدادهای بالا ببینید.`,
        });
      }
    } catch (err: any) {
      cancelCurrentJob = null;
      failCount++;
      onProgress({
        type: 'error',
        file: item.name,
        itemId: item.id,
        error: err.message || String(err),
      });
      onLog({
        id: `log-${Date.now()}-fatal`,
        timestamp: getTimestamp(),
        level: 'error',
        message: `تبدیل سند انجام نشد: ${err.message || String(err)}`,
      });
    }
  }

  if (activeCancellation) { cancelled(); return; }
  currentItem = null;
  onProgress({
    type: 'done',
    total: items.length,
    completed: successCount,
  });

  onLog({
    id: `log-${Date.now()}-summary`,
    timestamp: getTimestamp(),
    level: 'summary',
    kind: 'batch-end',
    message: `گزارش تبدیل: ${successCount} سند موفق، ${failCount} سند ناموفق.`,
  });
}

export async function cancelActiveConversion(): Promise<void> {
  activeCancellation = true;
  if (cancelCurrentJob) await cancelCurrentJob();
}

export interface PickedFile {
  name: string;
  path: string;
  sizeBytes: number;
  sizeStr: string;
}

/** Every native call reports *why* nothing came back, so no control can look dead. */
export interface NativeOutcome<T> {
  value: T;
  cancelled: boolean;
  error?: string;
}

export interface InitialLoad {
  items: QueueItem[];
  /** The document was handed over by the OS or the command line, so open in viewer mode. */
  viewer: boolean;
}

export interface ScannedFile {
  name: string;
  path: string;
  sizeBytes: number;
  relativePath: string;
}

const MARKDOWN = /\.(md|markdown)$/i;

/**
 * Markdown file handed to the process on launch (double-click / `mdpersia --gui file.md`).
 * In the dev/web build the launcher passes it as `?file=`.
 */
export async function resolveStartupFiles(): Promise<string[]> {
  const fromQuery = new URLSearchParams(window.location.search).getAll('file').filter(path => MARKDOWN.test(path));
  if (fromQuery.length) return fromQuery;

  if (!isTauri()) return [];
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    const args: string[] = await invoke('startup_arguments');
    return args.filter((a) => MARKDOWN.test(a));
  } catch {
    return [];
  }
}

export async function resolveStartupFile(): Promise<string | null> {
  return (await resolveStartupFiles())[0] ?? null;
}

/**
 * Subscribe to files opened while the app is already running (single instance handoff).
 */
export async function onOpenFileRequested(
  handler: (path: string) => void
): Promise<() => void> {
  if (!isTauri()) {
    const events = new EventSource(`/api/open-files?window=${encodeURIComponent(windowSession)}`);
    events.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (typeof payload.path === 'string' && MARKDOWN.test(payload.path)) handler(payload.path);
      } catch { /* Ignore incomplete events during reconnect. */ }
    };
    return () => events.close();
  }
  try {
    const { listen } = await import('@tauri-apps/api/event');
    const { invoke } = await import('@tauri-apps/api/core');
    const drain = async () => {
      const paths = await invoke<string[]>('startup_arguments');
      for (const path of paths) if (MARKDOWN.test(path)) handler(path);
    };
    const unlisten = await listen('open-files', () => { void drain().catch(error => console.error('Opening document failed', error)); });
    const unlistenDrop = await listen<{ paths: string[] }>('tauri://drag-drop', event => {
      for (const path of event.payload.paths) if (MARKDOWN.test(path)) handler(path);
    });
    // Catch launches delivered between startup and listener registration.
    await drain();
    return () => { unlisten(); unlistenDrop(); };
  } catch {
    return () => {};
  }
}

/**
 * Read raw markdown text from disk for live preview.
 */
export async function readFileContent(filePath: string): Promise<NativeOutcome<string>> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const result = await invoke<{ document?: { text: string }; error?: string }>('document_io', { request: { operation: 'read', path: filePath } });
      if (!result.document) throw new Error(result.error || 'فایل خوانده نشد.');
      return { value: result.document.text, cancelled: false };
    } catch (err: any) {
      return { value: '', cancelled: false, error: err.message || String(err) };
    }
  }

  try {
    const res = await fetch('/api/read-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filePath }),
    });
    const data = await res.json();
    return data.ok
      ? { value: data.content, cancelled: false }
      : { value: '', cancelled: false, error: data.error || 'File not readable' };
  } catch (err: any) {
    return { value: '', cancelled: false, error: err.message || String(err) };
  }
}

async function statFiles(paths: string[]): Promise<PickedFile[]> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<PickedFile[]>('stat_files', { paths });
    } catch { /* An unreadable size must not prevent an explicit file open. */ }
  }
  return paths.map((p) => ({
    name: p.replace(/^.*[\\/]/, ''),
    path: p.replace(/\\/g, '/'),
    sizeBytes: 0,
    sizeStr: '',
  }));
}

/**
 * Pick a directory via native Windows folder dialog.
 */
export async function pickDirectory(title?: string): Promise<NativeOutcome<string | null>> {
  const label = title || 'انتخاب پوشه';
  if (isTauri()) {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const selected = await open({ directory: true, multiple: false, title: label });
      return {
        value: typeof selected === 'string' ? selected : null,
        cancelled: selected === null,
      };
    } catch (err: any) {
      return { value: null, cancelled: false, error: err.message || String(err) };
    }
  }

  try {
    const res = await fetch(`/api/pick-folder?title=${encodeURIComponent(label)}`);
    const data = await res.json();
    if (data.error) return { value: null, cancelled: false, error: data.error };
    return { value: data.path ? String(data.path) : null, cancelled: !!data.cancelled };
  } catch (err: any) {
    return { value: null, cancelled: false, error: err.message || String(err) };
  }
}

/**
 * Pick multiple files via native Windows file dialog.
 */
export async function pickFiles(
  filterExts?: string[],
  title?: string
): Promise<NativeOutcome<PickedFile[]>> {
  if (isTauri()) {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const selected = await open({
        directory: false,
        multiple: true,
        filters: filterExts ? [{ name: 'Allowed Files', extensions: filterExts }] : undefined,
        title: title || 'انتخاب فایل',
      });
      const list = Array.isArray(selected) ? selected : typeof selected === 'string' ? [selected] : [];
      return { value: await statFiles(list), cancelled: list.length === 0 };
    } catch (err: any) {
      return { value: [], cancelled: false, error: err.message || String(err) };
    }
  }

  try {
    const params = new URLSearchParams();
    if (filterExts?.length) params.set('exts', filterExts.join(','));
    if (title) params.set('title', title);
    const res = await fetch(`/api/pick-files?${params.toString()}`);
    const data = await res.json();
    if (data.error) return { value: [], cancelled: false, error: data.error };
    if (Array.isArray(data.files) && data.files.length > 0 && typeof data.files[0].sizeBytes === 'number') {
      return { value: data.files, cancelled: !!data.cancelled };
    }
    return {
      value: await statFiles((data.files || []).map((f: { path: string }) => f.path)),
      cancelled: !!data.cancelled,
    };
  } catch (err: any) {
    return { value: [], cancelled: false, error: err.message || String(err) };
  }
}

/**
 * Scan a folder for Markdown files. A failed scan is reported as an error so the UI
 * never calls it "no markdown in this folder".
 */
export async function scanFolder(
  folderPath: string,
  recursive: boolean = true
): Promise<NativeOutcome<ScannedFile[]>> {
  try {
    if (isTauri()) {
      const { invoke } = await import('@tauri-apps/api/core');
      return { value: await invoke<ScannedFile[]>('scan_folder', { folderPath, recursive }), cancelled: false };
    }
    const res = await fetch('/api/scan-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folderPath, recursive }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return { value: [], cancelled: false, error: data.error || `HTTP ${res.status}` };
    }
    return { value: Array.isArray(data.files) ? data.files : [], cancelled: false };
  } catch (err: any) {
    return { value: [], cancelled: false, error: err.message || String(err) };
  }
}

/**
 * Open a directory (or reveal a file) in Windows Explorer.
 */
export async function openInExplorer(targetPath: string): Promise<NativeOutcome<boolean>> {
  const p = (targetPath || '').trim();
  if (!p) return { value: false, cancelled: false, error: 'مسیر هدف خالی است.' };

  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('reveal_path', { targetPath: p });
      return { value: true, cancelled: false };
    } catch (err: any) {
      return { value: false, cancelled: false, error: err.message || String(err) };
    }
  }

  try {
    const res = await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targetPath: p }),
    });
    const data = await res.json().catch(() => ({}));
    return data.success
      ? { value: true, cancelled: false }
      : { value: false, cancelled: false, error: data.error || 'اکسپلورر باز نشد.' };
  } catch (err: any) {
    return { value: false, cancelled: false, error: err.message || String(err) };
  }
}

/**
 * Fetch initial queue items dynamically from backend.
 * `file` lets the OS double-click handoff target a specific document.
 */
export async function fetchInitialItems(file?: string | null): Promise<InitialLoad> {
  if (isTauri()) {
    // The packaged app has no dev server to ask; the handed path is the whole queue.
    if (!file) return { items: [], viewer: false };
    return { items: [await queueItemFromPath(file)], viewer: true };
  }

  try {
    const q = file ? `?file=${encodeURIComponent(file)}` : '';
    const res = await fetch(`/api/initial-items${q}`);
    const data = await res.json();
    // The dev endpoint marks handoffs passed through the environment instead of the URL,
    // so viewer mode survives `mdpersia --gui file.md` without a second click.
    return { items: Array.isArray(data.items) ? data.items : [], viewer: !!data.viewer };
  } catch {
    return { items: [], viewer: false };
  }
}

async function queueItemFromPath(filePath: string): Promise<QueueItem> {
  const [file] = await statFiles([filePath]);
  const sizeBytes = file?.sizeBytes ?? 0;
  const name = filePath.replace(/^.*[\\/]/, '');
  return {
    id: `document:${filePath}`,
    name,
    path: filePath.replace(/\\/g, '/'),
    sizeBytes,
    sizeStr: `${(sizeBytes / 1024).toFixed(1)} KB`,
    status: 'pending',
    relativePath: name,
  };
}

export const previewEndpointUrl = (path: string, theme: string, zoom: number): string =>
  `/api/preview-html?path=${encodeURIComponent(path)}&theme=${theme}&zoom=${zoom}`;

const VAZIRMATN_WEIGHTS: Record<string, number> = {
  Thin: 100, Light: 300, Regular: 400, Medium: 500, SemiBold: 600, Bold: 700,
};

/** Viewer chrome shared by both runtimes; assets resolve against the app origin. */
function viewerShellCss(zoom: number, theme: string, reading: ReadingSettings = DEFAULT_APP_SETTINGS): string {
  const faces = Object.entries(VAZIRMATN_WEIGHTS)
    .map(
      ([name, weight]) =>
        `@font-face { font-family: "Vazirmatn"; src: url("${window.location.origin}/fonts/Vazirmatn-${name}.ttf") format("truetype"); font-weight: ${weight}; font-style: normal; font-display: swap; }`
    )
    .join('\n');
  return `<style>${faces}\n${previewStyles(theme, zoom, reading)}</style>`;
}

/** Theme and zoom change the current iframe; no Python process or Mermaid reload. */
export function applyPreviewAppearance(doc: Document, theme: 'dark' | 'light', zoom: number, reading?: ReadingSettings): void {
  let style = doc.getElementById('mdpersia-appearance');
  if (!style) {
    style = doc.createElement('style');
    style.id = 'mdpersia-appearance';
    doc.head.append(style);
  }
  style.textContent = viewerShellCss(zoom, theme, reading).replace(/^<style>|<\/style>$/g, '');
}

export type PreviewSource =
  | { kind: 'url'; url: string }
  | { kind: 'document'; html: string }
  | { kind: 'error'; message: string };

/**
 * The dev runtime streams preview HTML from the local bridge; the packaged app has no
 * server, so it asks the Rust command and hands the result to the iframe directly.
 */
function resolvePreviewResources(html: string): string {
  const document = new DOMParser().parseFromString(html, 'text/html');
  const base = document.querySelector('base')?.getAttribute('href');
  if (!base) return html;
  // Tauri encodes a file path as one URL segment. Relative resources cannot be
  // resolved against that URL, so resolve them against the original file base first.
  for (const element of document.querySelectorAll('[src], [poster], link[href]')) {
    for (const attribute of ['src', 'poster', ...(element.tagName === 'LINK' ? ['href'] : [])]) {
      const value = element.getAttribute(attribute);
      if (!value) continue;
      try {
        const resolved = new URL(value, base);
        if (resolved.protocol === 'file:') element.setAttribute(attribute, resolved.href);
      } catch { /* Preserve an invalid author-supplied URL for the browser to reject. */ }
    }
  }
  return '<!doctype html>\n' + document.documentElement.outerHTML;
}

export async function loadPreviewDocument(
  path: string,
  theme: 'dark' | 'light',
  zoom: number
): Promise<PreviewSource> {
  const pct = Math.min(250, Math.max(50, Math.round(zoom)));
  if (!isTauri()) return { kind: 'url', url: previewEndpointUrl(path, theme, pct) };

  try {
    const { invoke, convertFileSrc } = await import('@tauri-apps/api/core');
    const { html } = await invoke<{ html: string }>('preview_html', {
      request: { path, theme, zoom: pct },
    });
    // A webview cannot load file://; route local assets through the asset protocol.
    const mapped = resolvePreviewResources(html).replace(/file:\/\/([^"')\s]+)/g, (_m, raw: string) => {
      const p = decodeURIComponent(raw).replace(/^\/([A-Za-z]:)/, '$1');
      if (/\.(md|markdown)(?:[?#].*)?$/i.test(p)) return `file://${raw}`;
      const name = p.split(/[\\/]/).pop() || '';
      if (/\.ttf$/i.test(name)) return new URL(`/fonts/${name}`, window.location.href).href;
      if (/mermaid.*\.js$/i.test(name)) return new URL(`/vendor/${name}`, window.location.href).href;
      return convertFileSrc(p);
    });
    return { kind: 'document', html: mapped.replace('</head>', `${viewerShellCss(pct, theme)}</head>`) };
  } catch (err: any) {
    return { kind: 'error', message: err?.message || String(err) };
  }
}

/** Render the in-memory draft with the same Python Markdown/BiDi engine, without writing it. */
export async function loadDraftPreview(path: string, text: string, signal?: AbortSignal): Promise<PreviewSource> {
  try {
    if (!isTauri()) {
      const response = await fetch('/api/preview-draft', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path, text }), signal });
      const result = await response.json();
      if (!response.ok || typeof result.html !== 'string') throw new Error(result.error || 'پیش‌نمایش پیش‌نویس ساخته نشد.');
      return { kind: 'document', html: result.html };
    }
    const { invoke, convertFileSrc } = await import('@tauri-apps/api/core');
    const { html } = await invoke<{ html: string }>('preview_html', { request: { path, text, theme: 'light', zoom: 100 } });
    return { kind: 'document', html: resolvePreviewResources(html).replace(/file:\/\/([^"')\s]+)/g, (_match, raw: string) => {
      const p = decodeURIComponent(raw).replace(/^\/([A-Za-z]:)/, '$1');
      if (/\.(md|markdown)(?:[?#].*)?$/i.test(p)) return `file://${raw}`;
      const name = p.split(/[\\/]/).pop() || '';
      if (/\.ttf$/i.test(name)) return new URL(`/fonts/${name}`, window.location.href).href;
      if (/mermaid.*\.js$/i.test(name)) return new URL(`/vendor/${name}`, window.location.href).href;
      return convertFileSrc(p);
    }) };
  } catch (error) {
    if (signal?.aborted) throw error;
    return { kind: 'error', message: error instanceof Error ? error.message : String(error) };
  }
}

export type { LogEntry };
export { log as pushLog };

export async function openExternalUrl(url: string): Promise<void> {
  if (!/^https?:\/\//i.test(url)) throw new Error('فقط پیوند وب قابل بازشدن است.');
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('open_external', { url });
  } else window.open(url, '_blank', 'noopener,noreferrer');
}
