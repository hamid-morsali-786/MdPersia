import test from 'node:test';
import assert from 'node:assert/strict';
import {
  QUEUE_COLUMNS,
  DEFAULT_COLUMN_WIDTHS,
  DEFAULT_VISIBLE_COLUMNS,
  ColumnKey,
} from './queueTypes';

test('QUEUE_COLUMNS contains valid column definitions and constraints', () => {
  assert.equal(QUEUE_COLUMNS.length, 4);

  const columnIds = QUEUE_COLUMNS.map((c) => c.id);
  assert.deepEqual(columnIds, ['name', 'size', 'status', 'relativePath']);

  for (const col of QUEUE_COLUMNS) {
    assert.ok(col.minWidth > 0, `${col.id} minWidth must be positive`);
    assert.ok(col.defaultWidth >= col.minWidth, `${col.id} defaultWidth >= minWidth`);
    if (col.maxWidth) {
      assert.ok(col.maxWidth >= col.defaultWidth, `${col.id} maxWidth >= defaultWidth`);
    }
  }

  // 'name' column must be marked as required
  const nameCol = QUEUE_COLUMNS.find((c) => c.id === 'name');
  assert.equal(nameCol?.required, true);
});

test('DEFAULT_VISIBLE_COLUMNS includes all standard columns', () => {
  assert.equal(DEFAULT_VISIBLE_COLUMNS.length, 4);
  assert.ok(DEFAULT_VISIBLE_COLUMNS.includes('name'));
  assert.ok(DEFAULT_VISIBLE_COLUMNS.includes('size'));
  assert.ok(DEFAULT_VISIBLE_COLUMNS.includes('status'));
  assert.ok(DEFAULT_VISIBLE_COLUMNS.includes('relativePath'));
});

test('RTL resize calculation handles leftward drag (expansion) correctly', () => {
  const startX = 300;
  const currentX = 250; // Dragged 50px to the left
  const startWidth = 180;
  const minWidth = 110;
  const maxWidth = 500;

  // RTL formula: moving left decreases clientX, increasing column width
  const deltaX = startX - currentX; // +50
  const nextWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + deltaX));

  assert.equal(deltaX, 50);
  assert.equal(nextWidth, 230);
});

test('RTL resize calculation handles rightward drag (shrinkage) and min-width clamp', () => {
  const startX = 300;
  const currentX = 420; // Dragged 120px to the right
  const startWidth = 180;
  const minWidth = 110;
  const maxWidth = 500;

  const deltaX = startX - currentX; // -120
  const nextWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + deltaX));

  // 180 - 120 = 60, but clamped to minWidth = 110
  assert.equal(deltaX, -120);
  assert.equal(nextWidth, 110);
});

test('DEFAULT_COLUMN_WIDTHS matches defined column defaultWidth values', () => {
  for (const col of QUEUE_COLUMNS) {
    assert.equal(DEFAULT_COLUMN_WIDTHS[col.id as ColumnKey], col.defaultWidth);
  }
});
