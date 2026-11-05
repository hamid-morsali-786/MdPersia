import type { LogEntry } from '../types';

export type LogFilter = 'all' | 'error' | 'warn' | 'success';

// Terminal escape sequences belong to the transport, never to the report or its export.
export function cleanLogText(text: string): string {
  return text.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, '')
    .replace(/\u001b\][^\u0007\u001b]*(?:\u0007|\u001b\\)/g, '')
    .replace(/\r\n?/g, '\n');
}

export function stderrLogLevel(text: string): 'error' | 'warn' {
  // These are the CLI's explicit error prefixes. Ordinary stderr is not proof of failure.
  return /(?:^|\n)(?:ERR(?:\s|:)|Error:|Traceback \(most recent call last\):)/.test(cleanLogText(text)) ? 'error' : 'warn';
}

export function filterReportLogs(logs: LogEntry[], filter: LogFilter, query: string): LogEntry[] {
  const needle = query.trim().toLocaleLowerCase();
  return logs.filter(entry => (filter === 'all' || entry.level === filter) &&
    (!needle || cleanLogText(`${entry.message}\n${entry.fileName ?? ''}\n${entry.filePath ?? ''}`)
      .toLocaleLowerCase().includes(needle)));
}

export function reportCounts(logs: LogEntry[]): Record<LogFilter, number> {
  const counts = { all: logs.length, error: 0, warn: 0, success: 0 };
  for (const entry of logs) {
    if (entry.level === 'error' || entry.level === 'warn' || entry.level === 'success') counts[entry.level]++;
  }
  return counts;
}

export function formatLogReport(logs: LogEntry[]): string {
  return logs.map(entry => `[${entry.timestamp}] [${entry.level.toUpperCase()}]${entry.filePath ? ` [${entry.filePath}]` : ''}\n${cleanLogText(entry.message)}`).join('\n\n');
}

/** Watch is an open process, not completion. Observe the CLI's explicit phase markers
 * across arbitrary stdout chunks; incidental words in paths do not change the phase. */
export function createWatchObserver(onPhase: (watching: boolean) => void) {
  let pending = '';
  return (chunk: string) => {
    const lines = (pending + chunk).split(/\r\n|\n|\r/);
    pending = lines.pop()!.slice(-8192);
    for (const raw of lines) {
      const line = cleanLogText(raw);
      if (line.startsWith('[fa-md-pdf] Watching for changes in ') || line === '[fa-md-pdf] Waiting for changes.') onPhase(true);
      else if (line.startsWith('[fa-md-pdf] Detected changes in ')) onPhase(false);
    }
  };
}
