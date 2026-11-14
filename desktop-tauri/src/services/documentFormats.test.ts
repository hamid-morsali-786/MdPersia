import test from 'node:test';
import assert from 'node:assert/strict';
import { DOCUMENT_EXTENSIONS, copyDocumentPath, isMarkdownPath } from './documentFormats';
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
