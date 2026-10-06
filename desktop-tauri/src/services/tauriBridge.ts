import { QueueItem, ConvertOptions, LogEntry, ProgressEvent } from '../types';
import { buildCliArgs } from './cliTranslator';

export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

let activeCancellation = false;

const getTimestamp = (): string => new Date().toLocaleTimeString();


/**
 * Executes a single conversion job via Vite server streaming endpoint.
 */
async function executeWebConversionJob(
  args: string[],
  onLog: (entry: LogEntry) => void
): Promise<number> {
  const response = await fetch('/api/convert-job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ args }),
  });

  if (!response.body) {
    throw new Error('ReadableStream not supported');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let exitCode = 0;
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
            level: 'warn',
            message: payload.text.trimEnd(),
          });
        } else if (payload.type === 'exit') {
          exitCode = payload.code ?? 0;
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

  return exitCode;
}

/**
 * Executes conversion batch with REAL process execution in both Dev and Tauri modes.
 */
export async function executeConversion(
  items: QueueItem[],
  options: ConvertOptions,
  onProgress: (evt: ProgressEvent) => void,
  onLog: (entry: LogEntry) => void
): Promise<void> {
  activeCancellation = false;
  let successCount = 0;
  let failCount = 0;

  onLog({
    id: `log-${Date.now()}-start`,
    timestamp: getTimestamp(),
    level: 'info',
    message: `[START] Starting batch conversion of ${items.length} file(s) (${options.format.toUpperCase()})...`,
  });

  for (let i = 0; i < items.length; i++) {
    if (activeCancellation) {
      onProgress({ type: 'cancelled' });
      onLog({
        id: `log-${Date.now()}-cancelled`,
        timestamp: getTimestamp(),
        level: 'warn',
        message: 'Conversion batch cancelled by user.',
      });
      return;
    }

    const item = items[i];
    const args = buildCliArgs(item, options);

    onProgress({
      type: 'progress',
      file: item.name,
      total: items.length,
      completed: i,
    });

    onLog({
      id: `log-${Date.now()}-cmd`,
      timestamp: getTimestamp(),
      level: 'info',
      message: `fa-md-pdf ${args.join(' ')}`,
    });

    try {
      let code = 0;
      if (isTauri()) {
        const { Command } = await import('@tauri-apps/plugin-shell');
        const cmd = Command.create('fa-md-pdf', args);

        cmd.stdout.on('data', (line: string) => {
          onLog({
            id: `stdout-${Date.now()}-${Math.random()}`,
            timestamp: getTimestamp(),
            level: 'info',
            message: line,
          });
        });

        cmd.stderr.on('data', (line: string) => {
          onLog({
            id: `stderr-${Date.now()}-${Math.random()}`,
            timestamp: getTimestamp(),
            level: 'warn',
            message: line,
          });
        });

        const output = await cmd.execute();
        code = output.code ?? 0;
      } else {
        code = await executeWebConversionJob(args, onLog);
      }

      if (code === 0) {
        successCount++;
        onProgress({
          type: 'success',
          file: item.name,
          destPath: item.path,
        });
        onLog({
          id: `log-${Date.now()}-ok`,
          timestamp: getTimestamp(),
          level: 'success',
          message: `✓ Converted successfully: ${item.name}`,
        });
      } else {
        failCount++;
        onProgress({
          type: 'error',
          file: item.name,
          error: `Process exited with error code ${code}`,
        });
        onLog({
          id: `log-${Date.now()}-err`,
          timestamp: getTimestamp(),
          level: 'error',
          message: `✗ Failed converting ${item.name} (exit code ${code})`,
        });
      }
    } catch (err: any) {
      failCount++;
      onProgress({
        type: 'error',
        file: item.name,
        error: err.message || String(err),
      });
      onLog({
        id: `log-${Date.now()}-fatal`,
        timestamp: getTimestamp(),
        level: 'error',
        message: `Fatal error on ${item.name}: ${err.message}`,
      });
    }
  }

  onProgress({
    type: 'done',
    total: items.length,
    completed: successCount,
  });

  onLog({
    id: `log-${Date.now()}-summary`,
    timestamp: getTimestamp(),
    level: 'summary',
    message: `Batch finished: ${successCount} succeeded, ${failCount} failed.`,
  });
}

export function cancelActiveConversion(): void {
  activeCancellation = true;
}

/**
 * Read raw markdown text from disk for live preview.
 */
export async function readFileContent(filePath: string): Promise<string> {
  if (isTauri()) {
    try {
      const { readTextFile } = await import('@tauri-apps/plugin-fs');
      return await readTextFile(filePath);
    } catch {
      return '';
    }
  }

  try {
    const res = await fetch('/api/read-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filePath }),
    });
    const data = await res.json();
    return data.ok ? data.content : '';
  } catch {
    return '';
  }
}

/**
 * Pick a directory via native Windows folder dialog.
 */
export async function pickDirectory(title?: string): Promise<string | null> {
  if (isTauri()) {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const selected = await open({
        directory: true,
        multiple: false,
        title: title || 'انتخاب پوشه',
      });
      return typeof selected === 'string' ? selected : null;
    } catch {
      return null;
    }
  }

  try {
    const res = await fetch('/api/pick-folder');
    const data = await res.json();
    return data.path ? String(data.path) : null;
  } catch {
    return null;
  }
}

/**
 * Pick multiple files via native Windows file dialog.
 */
export async function pickFiles(
  filterExts?: string[]
): Promise<Array<{ name: string; path: string; sizeBytes: number; sizeStr: string }>> {
  if (isTauri()) {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const selected = await open({
        directory: false,
        multiple: true,
        filters: filterExts ? [{ name: 'Allowed Files', extensions: filterExts }] : undefined,
      });
      const list = Array.isArray(selected) ? selected : typeof selected === 'string' ? [selected] : [];
      return list.map((f) => ({
        name: f.replace(/^.*[\\/]/, ''),
        path: f.replace(/\\/g, '/'),
        sizeBytes: 1024,
        sizeStr: '1.0 KB',
      }));
    } catch {
      return [];
    }
  }

  try {
    const res = await fetch('/api/pick-files');
    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  } catch {
    return [];
  }
}

/**
 * Scan a folder for Markdown files.
 */
export async function scanFolder(
  folderPath: string,
  recursive: boolean = true
): Promise<Array<{ name: string; path: string; sizeBytes: number; relativePath: string }>> {
  try {
    const res = await fetch('/api/scan-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folderPath, recursive }),
    });
    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  } catch {
    return [];
  }
}

/**
 * Open a directory in Windows Explorer.
 */
export async function openInExplorer(targetPath: string): Promise<void> {
  const p = (targetPath || '').trim() || 'E:/project/fa-md-pdf-project';
  if (isTauri()) {
    try {
      const { Command } = await import('@tauri-apps/plugin-shell');
      await Command.create('explorer', [p.replace(/\//g, '\\')]).execute();
      return;
    } catch {
      // fallback
    }
  }

  try {
    await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targetPath: p }),
    });
  } catch (err) {
    console.error('Failed to open explorer:', err);
  }
}
