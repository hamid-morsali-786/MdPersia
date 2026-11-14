import test from 'node:test';
import assert from 'node:assert/strict';
import { DOCUMENT_EXTENSIONS, copyDocumentPath, isMarkdownPath, saveDocumentExtensions } from './documentFormats';
import { linkedMarkdownPath } from './queueState';
import { buildCliArgs, DEFAULT_CONVERT_OPTIONS } from './cliTranslator';

test('all supported formats retain their extension in Save As, links and legacy conversion options', () => {
  for (const extension of DOCUMENT_EXTENSIONS) {
    const path = 'C:/docs/راهنما.' + extension.toUpperCase();
    assert.equal(isMarkdownPath(path), true);
    assert.equal(copyDocumentPath(path), 'C:/docs/راهنما-copy.' + extension.toUpperCase());
    assert.equal(linkedMarkdownPath('C:/docs/source.md', './راهنما.' + extension + '#section'), 'C:/docs/راهنما.' + extension);
    const args = buildCliArgs({ id: '1', name: 'guide.' + extension, path, status: 'pending', sizeBytes: 0, sizeStr: '0 B' },
      { ...DEFAULT_CONVERT_OPTIONS, extensions: '.md, .markdown' });
    assert.ok(args.slice(args.indexOf('--extensions') + 1).includes('.' + extension));
  }
  for (const path of ['document.txt', 'notes.mdx.exe', 'C:/mdx/file', 'C:/file.md/folder', '.mdx']) {
    assert.equal(isMarkdownPath(path), false);
  }
});

test('native Save As defaults to the original format when the new name has no extension', () => {
  const original = [...DOCUMENT_EXTENSIONS];
  for (const extension of original) {
    const filters = saveDocumentExtensions('C:/docs/guide.' + extension.toUpperCase());
    assert.equal(filters[0], extension);
    assert.deepEqual([...filters].sort(), [...original].sort());
  }
  assert.deepEqual(saveDocumentExtensions('new document'), original);
  assert.deepEqual(DOCUMENT_EXTENSIONS, original);
});
