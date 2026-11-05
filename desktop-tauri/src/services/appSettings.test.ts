import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DEFAULT_APP_SETTINGS, SETTINGS_KEY, normalizeAppSettings, normalizeConversionOptions, readPreferences, savePreferences } from './appSettings';
import { DEFAULT_CONVERT_OPTIONS } from './cliTranslator';

function storage() {
  const values = new Map<string, string>();
  return { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value); } };
}

test('preferences migrate the old theme without inventing queued documents', () => {
  const local = storage();
  local.setItem('theme', 'light');
  const prefs = readPreferences(local);
  assert.equal(prefs.settings.theme, 'light');
  assert.deepEqual(prefs.options, DEFAULT_CONVERT_OPTIONS);
  assert.deepEqual(Object.keys(prefs).sort(), ['options', 'settings']);
});

test('reading and behavior preferences round trip and never resume Watch', () => {
  const local = storage();
  const settings = { ...DEFAULT_APP_SETTINGS, theme: 'system' as const, previewZoom: 130, focusNewFiles: false, wrapCode: true };
  const options = { ...DEFAULT_CONVERT_OPTIONS, format: 'docx' as const, outputDir: 'I:/اسناد', watch: true };
  assert.equal(savePreferences(settings, options, local), true);
  assert.deepEqual(readPreferences(local), { settings, options: { ...options, watch: false } });
});

test('turning off conversion persistence removes old values while preserving reading preferences', () => {
  const local = storage();
  savePreferences(DEFAULT_APP_SETTINGS, { ...DEFAULT_CONVERT_OPTIONS, format: 'docx' }, local);
  savePreferences({ ...DEFAULT_APP_SETTINGS, previewZoom: 120, rememberConversionOptions: false }, { ...DEFAULT_CONVERT_OPTIONS, outputDir: 'I:/old' }, local);
  assert.equal(readPreferences(local).settings.previewZoom, 120);
  assert.deepEqual(readPreferences(local).options, DEFAULT_CONVERT_OPTIONS);
  assert.equal(JSON.parse(local.getItem(SETTINGS_KEY)!).options, undefined);
});

test('corrupt, unsupported and unavailable storage cannot stop startup', () => {
  const local = storage();
  for (const invalid of ['{broken', 'null', '[]', '{"version":2,"settings":{"previewZoom":200}}']) {
    local.setItem(SETTINGS_KEY, invalid);
    assert.deepEqual(readPreferences(local).settings, DEFAULT_APP_SETTINGS);
  }
  const unavailable = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('quota'); } };
  assert.deepEqual(readPreferences(unavailable).settings, DEFAULT_APP_SETTINGS);
  assert.equal(savePreferences(DEFAULT_APP_SETTINGS, DEFAULT_CONVERT_OPTIONS, unavailable), false);
});

test('untrusted stored settings are typed, bounded and stripped of unknown keys', () => {
  const result = normalizeAppSettings({ theme: 'invalid', lineHeight: 99, previewZoom: -3, rememberScroll: 'false', queue: ['ghost.md'] });
  assert.equal(result.theme, 'dark');
  assert.equal(result.lineHeight, 2.4);
  assert.equal(result.previewZoom, 60);
  assert.equal(result.rememberScroll, true);
  assert.equal('queue' in result, false);
  assert.equal(normalizeAppSettings({ previewZoom: NaN, lineHeight: Infinity }).previewZoom, 100);
});

test('stored conversion options validate enums, numeric bounds and image geometry', () => {
  const options = normalizeConversionOptions({ format: 'exe', pageFormat: 'huge', margin: '0', mermaidTheme: 'bad', mermaidTimeout: -1,
    docxFontSize: 500, docxImageMinWidth: 9, docxImageMaxWidth: 2, outputDir: 123, watch: true, extra: 'ignored' });
  assert.equal(options.format, 'pdf');
  assert.equal(options.pageFormat, 'A4');
  assert.equal(options.margin, '15mm');
  assert.equal(options.mermaidTheme, 'default');
  assert.equal(options.mermaidTimeout, 1);
  assert.equal(options.docxFontSize, 72);
  assert.equal(options.docxImageMaxWidth, 9);
  assert.equal(options.outputDir, '');
  assert.equal(options.watch, false);
  assert.equal('extra' in options, false);
});
