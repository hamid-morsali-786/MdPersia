import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formatQueueBytes, queueDisplayFields } from './queueDisplay';

test('existing column preferences become compact row metadata preferences', () => {
  assert.deepEqual([...queueDisplayFields(null)], ['status', 'size']);
  assert.deepEqual([...queueDisplayFields(['name', 'relativePath', 'relativePath', 'old'])], ['relativePath']);
  assert.deepEqual([...queueDisplayFields(['name'])], []);
  assert.deepEqual([...queueDisplayFields({ size: true })], ['status', 'size']);
});

test('small file sizes retain a meaningful exact value', () => {
  assert.equal(formatQueueBytes(40), '40 B');
  assert.equal(formatQueueBytes(1024), '1.0 KB');
  assert.equal(formatQueueBytes(2 * 1024 ** 2), '2.0 MB');
});
