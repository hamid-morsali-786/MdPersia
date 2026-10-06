import { useState, useCallback, useEffect, useRef } from 'react';
import {
  ColumnKey,
  QUEUE_COLUMNS,
  DEFAULT_COLUMN_WIDTHS,
  STORAGE_KEY_COLUMN_WIDTHS,
} from './queueTypes';

function loadInitialWidths(): Record<ColumnKey, number> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_COLUMN_WIDTHS);
    if (!raw) return { ...DEFAULT_COLUMN_WIDTHS };
    const parsed = JSON.parse(raw);
    const result = { ...DEFAULT_COLUMN_WIDTHS };
    for (const col of QUEUE_COLUMNS) {
      if (typeof parsed[col.id] === 'number' && parsed[col.id] >= col.minWidth) {
        result[col.id] = parsed[col.id];
      }
    }
    return result;
  } catch {
    return { ...DEFAULT_COLUMN_WIDTHS };
  }
}

export function useColumnResize() {
  const [columnWidths, setColumnWidths] = useState<Record<ColumnKey, number>>(loadInitialWidths);
  const [resizingCol, setResizingCol] = useState<ColumnKey | null>(null);
  const resizeStateRef = useRef<{
    colKey: ColumnKey;
    startX: number;
    startWidth: number;
    minWidth: number;
    maxWidth: number;
  } | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_COLUMN_WIDTHS, JSON.stringify(columnWidths));
    } catch {
      // Ignore storage errors in restricted environments
    }
  }, [columnWidths]);

  const handlePointerMove = useCallback((e: MouseEvent) => {
    const state = resizeStateRef.current;
    if (!state) return;

    // RTL calculation: moving left decreases clientX, increasing column width
    const deltaX = state.startX - e.clientX;
    const nextWidth = Math.max(state.minWidth, Math.min(state.maxWidth, state.startWidth + deltaX));

    setColumnWidths((prev) => ({
      ...prev,
      [state.colKey]: nextWidth,
    }));
  }, []);

  const handlePointerUp = useCallback(() => {
    resizeStateRef.current = null;
    setResizingCol(null);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    window.removeEventListener('mousemove', handlePointerMove);
    window.removeEventListener('mouseup', handlePointerUp);
  }, [handlePointerMove]);

  const startResize = useCallback(
    (colKey: ColumnKey, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const colDef = QUEUE_COLUMNS.find((c) => c.id === colKey);
      if (!colDef) return;

      resizeStateRef.current = {
        colKey,
        startX: e.clientX,
        startWidth: columnWidths[colKey] || colDef.defaultWidth,
        minWidth: colDef.minWidth,
        maxWidth: colDef.maxWidth ?? 600,
      };

      setResizingCol(colKey);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';

      window.addEventListener('mousemove', handlePointerMove);
      window.addEventListener('mouseup', handlePointerUp);
    },
    [columnWidths, handlePointerMove, handlePointerUp]
  );

  const resetColumnWidth = useCallback((colKey: ColumnKey) => {
    const colDef = QUEUE_COLUMNS.find((c) => c.id === colKey);
    if (!colDef) return;
    setColumnWidths((prev) => ({
      ...prev,
      [colKey]: colDef.defaultWidth,
    }));
  }, []);

  const resetAllWidths = useCallback(() => {
    setColumnWidths({ ...DEFAULT_COLUMN_WIDTHS });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      window.removeEventListener('mousemove', handlePointerMove);
      window.removeEventListener('mouseup', handlePointerUp);
    };
  }, [handlePointerMove, handlePointerUp]);

  return {
    columnWidths,
    resizingCol,
    startResize,
    resetColumnWidth,
    resetAllWidths,
  };
}
