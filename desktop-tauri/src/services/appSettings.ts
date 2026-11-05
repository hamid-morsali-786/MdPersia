import type { ConvertOptions } from '../types';
import { DEFAULT_CONVERT_OPTIONS } from './cliTranslator';

export type ThemePreference = 'dark' | 'light' | 'system';
export interface AppSettings {
  theme: ThemePreference;
  previewZoom: number;
  lineHeight: number;
  readingWidth: 'page' | 'wide';
  wrapCode: boolean;
  rememberScroll: boolean;
  focusNewFiles: boolean;
  showConversionLogs: boolean;
  confirmClearQueue: boolean;
  rememberConversionOptions: boolean;
}
export type ReadingSettings = Pick<AppSettings, 'lineHeight' | 'readingWidth' | 'wrapCode' | 'rememberScroll'>;

export const SETTINGS_KEY = 'mdpersia.preferences.v1';
export const DEFAULT_APP_SETTINGS: AppSettings = {
  theme: 'dark', previewZoom: 100, lineHeight: 1.8, readingWidth: 'page',
  wrapCode: true, rememberScroll: true, focusNewFiles: true,
  showConversionLogs: true, confirmClearQueue: false, rememberConversionOptions: true,
};

type SettingsStorage = Pick<Storage, 'getItem' | 'setItem'>;
const record = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};

function browserStorage(): SettingsStorage | undefined {
  try { return window.localStorage; } catch { return undefined; }
}

export function normalizeAppSettings(value: unknown): AppSettings {
  const raw = record(value);
  const result = { ...DEFAULT_APP_SETTINGS };
  if (['dark', 'light', 'system'].includes(raw.theme as string)) result.theme = raw.theme as ThemePreference;
  if (raw.readingWidth === 'page' || raw.readingWidth === 'wide') result.readingWidth = raw.readingWidth;
  if (typeof raw.previewZoom === 'number' && Number.isFinite(raw.previewZoom)) {
    result.previewZoom = Math.round(Math.min(200, Math.max(60, raw.previewZoom)) / 10) * 10;
  }
  if (typeof raw.lineHeight === 'number' && Number.isFinite(raw.lineHeight)) {
    result.lineHeight = Math.round(Math.min(2.4, Math.max(1.4, raw.lineHeight)) * 10) / 10;
  }
  for (const key of ['wrapCode', 'rememberScroll', 'focusNewFiles', 'showConversionLogs', 'confirmClearQueue', 'rememberConversionOptions'] as const) {
    if (typeof raw[key] === 'boolean') result[key] = raw[key];
  }
  return result;
}

/** Stored preferences never resume a continuous watch or accept unknown option keys. */
export function normalizeConversionOptions(value: unknown): ConvertOptions {
  const raw = record(value);
  const result = { ...DEFAULT_CONVERT_OPTIONS };
  for (const key of Object.keys(result) as (keyof ConvertOptions)[]) {
    const candidate = raw[key];
    if (typeof result[key] === 'boolean' && typeof candidate === 'boolean') Object.assign(result, { [key]: candidate });
    if (typeof result[key] === 'string' && typeof candidate === 'string' && candidate.length <= 4096) Object.assign(result, { [key]: candidate });
  }
  const enums = {
    format: ['pdf', 'docx', 'wrap-rtl'], pageFormat: ['A4', 'A3', 'Letter', 'Legal'],
    margin: ['10mm', '15mm', '20mm', '25mm', '30mm'],
    mermaidTheme: ['default', 'forest', 'dark', 'neutral', 'base', 'null'],
  };
  for (const key of Object.keys(enums) as (keyof typeof enums)[]) {
    if (!enums[key].includes(result[key])) Object.assign(result, { [key]: DEFAULT_CONVERT_OPTIONS[key] });
  }
  const ranges = { docxImageScale: [0.1, 10], docxImageMinWidth: [0.1, 30], docxImageMaxWidth: [0.1, 30], docxFontSize: [6, 72], mermaidTimeout: [1, 600] };
  for (const key of Object.keys(ranges) as (keyof typeof ranges)[]) {
    const candidate = raw[key];
    if (typeof candidate === 'number' && Number.isFinite(candidate)) result[key] = Math.max(ranges[key][0], Math.min(ranges[key][1], candidate));
  }
  if (result.docxImageMaxWidth < result.docxImageMinWidth) result.docxImageMaxWidth = result.docxImageMinWidth;
  result.watch = false;
  return result;
}

export function readPreferences(storage = browserStorage()): { settings: AppSettings; options: ConvertOptions } {
  const fallback = { settings: { ...DEFAULT_APP_SETTINGS }, options: { ...DEFAULT_CONVERT_OPTIONS } };
  try {
    const saved = storage?.getItem(SETTINGS_KEY);
    if (saved) {
      const data = record(JSON.parse(saved));
      if (data.version !== 1) return fallback;
      const settings = normalizeAppSettings(data.settings);
      return { settings, options: settings.rememberConversionOptions ? normalizeConversionOptions(data.options) : fallback.options };
    }
    const legacyTheme = storage?.getItem('theme');
    if (legacyTheme === 'dark' || legacyTheme === 'light') fallback.settings.theme = legacyTheme;
  } catch { /* Corrupt or unavailable storage must not prevent opening a document. */ }
  return fallback;
}

export function savePreferences(settings: AppSettings, options: ConvertOptions, storage = browserStorage()): boolean {
  try {
    if (!storage) return false;
    storage.setItem(SETTINGS_KEY, JSON.stringify({ version: 1, settings: normalizeAppSettings(settings),
      options: settings.rememberConversionOptions ? normalizeConversionOptions(options) : undefined }));
    return true;
  } catch { return false; }
}
