import { useState, useCallback, useEffect } from 'react';
import {
  ColumnKey,
  QUEUE_COLUMNS,
  DEFAULT_VISIBLE_COLUMNS,
  STORAGE_KEY_VISIBLE_COLUMNS,
} from './queueTypes';

function loadInitialVisibility(): Set<ColumnKey> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_VISIBLE_COLUMNS);
    if (!raw) return new Set(DEFAULT_VISIBLE_COLUMNS);
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return new Set(DEFAULT_VISIBLE_COLUMNS);
    }
    const valid = parsed.filter((col): col is ColumnKey =>
      QUEUE_COLUMNS.some((c) => c.id === col)
    );
    // Ensure required column 'name' is always present
    if (!valid.includes('name')) valid.unshift('name');
    return new Set(valid);
  } catch {
    return new Set(DEFAULT_VISIBLE_COLUMNS);
  }
}

export function useColumnVisibility() {
  const [visibleColumns, setVisibleColumns] = useState<Set<ColumnKey>>(loadInitialVisibility);

  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY_VISIBLE_COLUMNS,
        JSON.stringify(Array.from(visibleColumns))
      );
    } catch {
      // Ignore storage errors in restricted environments
    }
  }, [visibleColumns]);

  const toggleColumn = useCallback((key: ColumnKey) => {
    const colDef = QUEUE_COLUMNS.find((c) => c.id === key);
    if (colDef?.required) return;

    setVisibleColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size <= 1) return prev; // Keep at least one column
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const resetVisibility = useCallback(() => {
    setVisibleColumns(new Set(DEFAULT_VISIBLE_COLUMNS));
  }, []);

  const isVisible = useCallback(
    (key: ColumnKey) => visibleColumns.has(key),
    [visibleColumns]
  );

  return {
    visibleColumns,
    toggleColumn,
    resetVisibility,
    isVisible,
  };
}
