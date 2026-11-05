import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cleanLogText, createWatchObserver, filterReportLogs, formatLogReport, reportCounts, stderrLogLevel } from './consoleReport';
import type { LogEntry } from '../types';

const logs: LogEntry[] = [
  { id: '1', timestamp: '10:00:01', level: 'info', message: '\u001b[32mEnglish: engine ready\u001b[0m' },
  { id: '2', timestamp: '10:00:02', level: 'error', message: 'خواندن فایل انجام نشد', fileName: 'سند.md', filePath: 'C:/First/سند.md' },
  { id: '3', timestamp: '10:00:03', level: 'success', message: 'فایل ساخته شد', fileName: 'سند.md', filePath: 'C:/Second/سند.md' },
  { id: '4', timestamp: '10:00:04', level: 'warn', message: 'هشدار موتور' },
  { id: '5', timestamp: '10:00:05', level: 'summary', message: '۱ موفق و ۱ ناموفق' },
];

test('report filters combine level and literal search across messages and full file paths', () => {
  assert.deepEqual(filterReportLogs(logs, 'error', 'سند.md').map(log => log.id), ['2']);
  assert.deepEqual(filterReportLogs(logs, 'all', 'SECOND').map(log => log.id), ['3']);
  assert.deepEqual(filterReportLogs(logs, 'all', 'engine').map(log => log.id), ['1']);
  assert.deepEqual(filterReportLogs(logs, 'all', '['), []);
  assert.deepEqual(filterReportLogs(logs, 'warn', '   ').map(log => log.id), ['4']);
  assert.equal(logs.length, 5);
});

test('report totals count events without inferring successful files from a summary or stdout', () => {
  assert.deepEqual(reportCounts(logs), { all: 5, error: 1, warn: 1, success: 1 });
});

test('export preserves multiline diagnostics and path identity, stripping terminal control sequences', () => {
  const selected = filterReportLogs(logs, 'error', '');
  assert.equal(formatLogReport(selected), '[10:00:02] [ERROR] [C:/First/سند.md]\nخواندن فایل انجام نشد');
  assert.equal(cleanLogText('\u001b]0;window title\u0007\u001b[31mERR\u001b[0m\r\nline 2'), 'ERR\nline 2');
  assert.equal(formatLogReport([]), '');
});

test('watch phases survive arbitrary chunk boundaries and do not treat paths as phase markers', () => {
  const phases: boolean[] = [];
  const observe = createWatchObserver(value => phases.push(value));
  observe('OK C:/Watching for changes in example.md\n');
  observe('[fa-md-pdf] Watch');
  observe('ing for changes in C:/سند.md (Press Ctrl+C to stop)...\r\n');
  observe('[fa-md-pdf] Detected changes in 1 file(s). Re-converting...\n');
  observe('OK C:/سند.md -> C:/سند.pdf\n[fa-md-pdf] Waiting for changes.\n');
  assert.deepEqual(phases, [true, false, true]);
});

test('explicit engine errors remain errors without treating all stderr as process failure', () => {
  assert.equal(stderrLogLevel('Error: Input path does not exist'), 'error');
  assert.equal(stderrLogLevel('\u001b[31mERR C:/file.md\u001b[0m'), 'error');
  assert.equal(stderrLogLevel('Warning: optional font unavailable'), 'warn');
});
