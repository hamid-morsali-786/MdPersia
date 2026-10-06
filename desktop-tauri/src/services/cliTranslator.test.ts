import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCliArgs, DEFAULT_CONVERT_OPTIONS } from './cliTranslator';
import { QueueItem } from '../types';

const mockItem: QueueItem = {
  id: 'test-1',
  name: 'test.md',
  path: 'E:/docs/test.md',
  sizeBytes: 1024,
  sizeStr: '1.0 KB',
  status: 'pending',
};

test('translates default options to PDF arguments correctly', () => {
  const args = buildCliArgs(mockItem, DEFAULT_CONVERT_OPTIONS);
  assert.equal(args[0], 'E:/docs/test.md');
  assert.ok(args.includes('--format'));
  assert.equal(args[args.indexOf('--format') + 1], 'pdf');
  assert.ok(args.includes('--page-format'));
  assert.equal(args[args.indexOf('--page-format') + 1], 'A4');
  assert.ok(args.includes('--recursive'));
});

test('translates docx format and specific docx options', () => {
  const options = {
    ...DEFAULT_CONVERT_OPTIONS,
    format: 'docx' as const,
    docxImageScale: 4,
    docxFontSize: 14,
  };
  const args = buildCliArgs(mockItem, options);
  assert.ok(args.includes('--format'));
  assert.equal(args[args.indexOf('--format') + 1], 'docx');
  assert.ok(args.includes('--docx-image-scale'));
  assert.equal(args[args.indexOf('--docx-image-scale') + 1], '4');
  assert.ok(args.includes('--docx-font-size'));
  assert.equal(args[args.indexOf('--docx-font-size') + 1], '14');
});

test('translates wrap-rtl options with suffix and omits PDF/DOCX flags', () => {
  const options = {
    ...DEFAULT_CONVERT_OPTIONS,
    format: 'wrap-rtl' as const,
    wrapRtlSuffix: '.persian.md',
  };
  const args = buildCliArgs(mockItem, options);
  assert.ok(args.includes('--wrap-rtl'));
  assert.ok(args.includes('--wrap-rtl-suffix'));
  assert.equal(args[args.indexOf('--wrap-rtl-suffix') + 1], '.persian.md');
  assert.ok(!args.includes('--page-format'));
  assert.ok(!args.includes('--margin'));
  assert.ok(!args.includes('--docx-image-scale'));
});

test('handles output directory, extensions and flags', () => {
  const options = {
    ...DEFAULT_CONVERT_OPTIONS,
    outputDir: 'E:/output',
    recursive: false,
    keepHtml: true,
    stripEmojis: true,
    extensions: '.md, .txt',
  };
  const args = buildCliArgs(mockItem, options);
  assert.ok(args.includes('--output'));
  assert.equal(args[args.indexOf('--output') + 1], 'E:/output');
  assert.ok(args.includes('--no-recursive'));
  assert.ok(args.includes('--keep-html'));
  assert.ok(args.includes('--strip-emojis'));
  assert.ok(args.includes('--extensions'));
  assert.ok(args.includes('.md'));
  assert.ok(args.includes('.txt'));
});
