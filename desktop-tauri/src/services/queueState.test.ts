import { test } from 'node:test';
import assert from 'node:assert/strict';
import { documentKey, linkedMarkdownPath, mergeQueueItems, removeQueueItems } from './queueState';
import type { QueueItem } from '../types';

const file = (path: string): QueueItem => ({ id: 'open-0', path,
  name: path.split(/[\\/]/).pop()!, sizeBytes: 10, sizeStr: '10 B', status: 'pending' });

test('local Markdown links keep the source directory and reject remote links', () => {
  assert.equal(linkedMarkdownPath('C:/docs/one/start.md', '../other%20file.md#part'), 'C:/docs/other file.md');
  assert.equal(linkedMarkdownPath('/docs/start.md', './next.md'), '/docs/next.md');
  assert.equal(linkedMarkdownPath('C:/docs/start.md', 'https://example.com/file.md'), null);
  assert.equal(linkedMarkdownPath('C:/docs/start.md', '#section'), null);
});

test('opening A, B, C accumulates files and focuses the newest document', () => {
  let queue: QueueItem[] = [];
  for (const path of ['C:/docs/A.md', 'C:/docs/B.md', 'C:/docs/C.md']) {
    const result = mergeQueueItems(queue, [file(path)]);
    queue = result.items;
    assert.equal(result.focusedId, queue[queue.length - 1].id);
  }
  assert.equal(queue.length, 3);
  assert.equal(new Set(queue.map(item => item.id)).size, 3);
});

test('reopening a Windows path with different casing/separators selects the existing row', () => {
  const first = mergeQueueItems([], [file('C:\\Docs\\یادداشت.MD')]);
  first.items[0].status = 'success';
  const second = mergeQueueItems(first.items, [file('c:/docs/یادداشت.md')]);
  assert.equal(second.items.length, 1);
  assert.equal(second.added, 0);
  assert.equal(second.focusedId, first.focusedId);
  assert.equal(second.items[0].status, 'success');
  assert.equal(documentKey('/docs/A.md'), '/docs/A.md');
});

test('identical basenames in different folders remain distinct', () => {
  const result = mergeQueueItems([], [file('C:/one/README.md'), file('C:/two/README.md')]);
  assert.equal(result.items.length, 2);
  assert.notEqual(result.items[0].id, result.items[1].id);
});

test('concurrent deliveries can merge against the latest queue without replacing prior files', () => {
  const b = mergeQueueItems([], [file('C:/B.md')]);
  const a = mergeQueueItems(b.items, [file('C:/A.md'), file('C:/B.md')]);
  assert.deepEqual(a.items.map(item => item.name), ['B.md', 'A.md']);
});

test('removing the active document chooses its neighbor and clearing leaves no ghost row', () => {
  const { items } = mergeQueueItems([], [file('C:/A.md'), file('C:/B.md'), file('C:/C.md')]);
  const removed = removeQueueItems(items, new Set([items[1].id]), items[1].id);
  assert.equal(removed.activeId, items[2].id);
  const cleared = removeQueueItems(removed.items, new Set(removed.items.map(item => item.id)), removed.activeId);
  assert.equal(cleared.activeId, null);
  assert.deepEqual(cleared.items, []);
});
