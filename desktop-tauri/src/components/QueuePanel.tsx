import React, { useState, useRef, useMemo, useEffect } from 'react';
import { QueueItem } from '../types';
import { QueueItemRow } from './QueueItemRow';
import {
  FilePlus,
  FolderPlus,
  Trash2,
  FolderOpen,
  UploadCloud,
  FileCheck2,
  FolderTree,
  Search,
  X,
  Loader2,
  ListFilter,
} from 'lucide-react';
import { QUEUE_COLUMNS, FILL_COLUMN } from './Queue/queueTypes';
import { useColumnVisibility } from './Queue/useColumnVisibility';
import { useColumnResize } from './Queue/useColumnResize';
import { ResizableHeaderCell } from './Queue/ResizableHeaderCell';
import { ColumnVisibilityPopover } from './Queue/ColumnVisibilityPopover';

/** A queue of one small file must not read as "0.0 MB". */
const formatBytes = (bytes: number) =>
  bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

interface QueuePanelProps {
  items: QueueItem[];
  selectedIds: Set<string>;
  recursive: boolean;
  query: string;
  nativeBusy: 'files' | 'folder' | 'output-dir' | 'explorer' | null;
  isConverting?: boolean;
  onQueryChange: (value: string) => void;
  onRecursiveChange: (value: boolean) => void;
  onSelect: (id: string, e: { ctrlKey: boolean; metaKey: boolean }) => void;
  onAddFiles: (files: FileList | File[]) => void;
  onPickFilesNative?: () => void;
  onAddFolder?: () => void;
  onRemoveSelected: () => void;
  onClearAll: () => void;
  onOpenFile?: (path: string) => void;
  onRevealFolder?: (path: string) => void;
}

export const QueuePanel: React.FC<QueuePanelProps> = ({
  items,
  selectedIds,
  recursive,
  query,
  nativeBusy,
  isConverting = false,
  onQueryChange,
  onRecursiveChange,
  onSelect,
  onAddFiles,
  onPickFilesNative,
  onAddFolder,
  onRemoveSelected,
  onClearAll,
  onOpenFile,
  onRevealFolder,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; item: QueueItem } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const { visibleColumns, toggleColumn, resetVisibility } = useColumnVisibility();
  const { columnWidths, resizingCol, startResize, resetColumnWidth, resetAllWidths } = useColumnResize();

  const handleResetDefaults = () => {
    resetVisibility();
    resetAllWidths();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onAddFiles(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onAddFiles(e.target.files);
      e.target.value = '';
    }
  };

  const handleContextMenu = (e: React.MouseEvent, item: QueueItem) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, item });
  };

  const closeContextMenu = () => setContextMenu(null);

  useEffect(() => {
    if (!contextMenu) return;
    const dismiss = () => setContextMenu(null);
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setContextMenu(null);
    };
    window.addEventListener('scroll', dismiss, true);
    window.addEventListener('keydown', key);
    return () => {
      window.removeEventListener('scroll', dismiss, true);
      window.removeEventListener('keydown', key);
    };
  }, [contextMenu]);

  const trimmed = query.trim();
  const filtered = useMemo(() => {
    if (!trimmed) return items;
    const needle = trimmed.toLowerCase();
    return items.filter(
      (it) =>
        it.name.toLowerCase().includes(needle) ||
        (it.relativePath || '').toLowerCase().includes(needle)
    );
  }, [items, trimmed]);

  // Sized from the rows on screen: a filtered count must not be paired with the full total.
  const totalBytes = filtered.reduce((acc, it) => acc + it.sizeBytes, 0);
  const totalSize = formatBytes(totalBytes);

  const visibleColDefs = QUEUE_COLUMNS.filter((c) => visibleColumns.has(c.id));

  const pickerPending = nativeBusy !== null;

  return (
    <div
      className="flex flex-col h-full min-w-[240px] bg-card border-l border-main select-none relative transition-colors duration-200"
      onClick={closeContextMenu}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        multiple
        accept=".md,.markdown"
        className="hidden"
      />

      {/* Panel Header */}
      <div className="flex items-center justify-between gap-2 px-3 py-2.5 border-b border-main bg-surface transition-colors">
        <div className="flex items-center gap-2 min-w-0">
          <FileCheck2 className="w-4 h-4 text-blue-500 shrink-0" />
          <h2 className="text-sm font-semibold text-main whitespace-nowrap">صف فایل‌ها</h2>
          <span className="text-xs px-2 py-0.5 rounded-full bg-subtle text-muted font-mono whitespace-nowrap shrink-0">
            {filtered.length === items.length ? items.length : `${filtered.length}/${items.length}`}
          </span>
        </div>

        <ColumnVisibilityPopover
          visibleColumns={visibleColumns}
          onToggleColumn={toggleColumn}
          onResetDefaults={handleResetDefaults}
        />
      </div>

      {/* Compact filter bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-main bg-card">
        <div className="relative flex-1 min-w-0">
          <Search className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-dim" />
          <input
            ref={searchRef}
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onQueryChange('');
            }}
            placeholder="جستجوی نام فایل یا مسیر…"
            aria-label="جستجو در صف فایل‌ها"
            className="w-full min-w-0 rounded-md bg-input border border-input py-1 pr-7 pl-7 text-xs text-main font-mono placeholder:text-dim focus:border-blue-500 focus:outline-none transition-colors duration-150"
          />
          {query && (
            <button
              onClick={() => {
                onQueryChange('');
                searchRef.current?.focus();
              }}
              className="btn absolute left-1 top-1/2 -translate-y-1/2 rounded p-1 text-dim hover:text-main hover:bg-subtle"
              title="پاک کردن متن جستجو"
              aria-label="پاک کردن متن جستجو"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <span className="text-[11px] text-dim font-mono whitespace-nowrap shrink-0 flex items-center gap-1">
          <ListFilter className="w-3 h-3" />
          {filtered.length} سند · {totalSize}
        </span>
      </div>

      {/* Main Table / Drop Area */}
      <div className="flex-1 overflow-x-auto overflow-y-auto relative" onKeyDown={(event) => {
        const row = (event.target as HTMLElement).closest<HTMLElement>('[data-document-id]');
        if (!row) return;
        const index = filtered.findIndex(item => item.id === row.dataset.documentId);
        let next = index;
        if (event.key === 'ArrowDown') next = Math.min(filtered.length - 1, index + 1);
        else if (event.key === 'ArrowUp') next = Math.max(0, index - 1);
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = filtered.length - 1;
        else if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        const item = filtered[next];
        if (!item) return;
        onSelect(item.id, event);
        const rows = event.currentTarget.querySelectorAll<HTMLElement>('[data-document-id]');
        [...rows].find(element => element.dataset.documentId === item.id)?.focus();
      }}>
        {items.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center text-muted">
            <div className="w-12 h-12 rounded-xl bg-subtle flex items-center justify-center mb-3 text-muted">
              <UploadCloud className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-main mb-1">هیچ سندی افزوده نشده است</p>
            <p className="text-xs text-muted max-w-[220px] leading-relaxed">
              فایل‌های Markdown خود را به اینجا بکشید یا از دکمه‌های «افزودن فایل» و «افزودن پوشه» استفاده کنید.
            </p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-6 text-center text-muted">
            <p className="text-xs">
              هیچ سندی با «{trimmed}» مطابقت نداشت.
            </p>
            <button
              onClick={() => onQueryChange('')}
              className="btn mt-2 px-2.5 py-1 rounded text-xs bg-subtle hover:bg-hover text-main"
            >
              نمایش همه
            </button>
          </div>
        ) : (
          <table className="w-full text-right text-xs table-fixed">
            <thead className="sticky top-0 bg-surface backdrop-blur border-b border-main text-muted z-10">
              <tr>
                {visibleColDefs.map((col) => (
                  <ResizableHeaderCell
                    key={col.id}
                    column={col}
                    width={columnWidths[col.id] || col.defaultWidth}
                    isResizing={resizingCol === col.id}
                    fill={col.id === FILL_COLUMN}
                    onStartResize={(e) => startResize(col.id, e)}
                    onResetWidth={() => resetColumnWidth(col.id)}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <QueueItemRow
                  key={item.id}
                  item={item}
                  isSelected={selectedIds.has(item.id)}
                  visibleColumns={visibleColumns}
                  columnWidths={columnWidths}
                  fillColumn={FILL_COLUMN}
                  onSelect={onSelect}
                  onContextMenu={handleContextMenu}
                />
              ))}
            </tbody>
          </table>
        )}

        {/* Drag Overlay */}
        {isDragOver && (
          <div className="absolute inset-0 bg-blue-500/10 border-2 border-dashed border-blue-500 backdrop-blur-sm flex flex-col items-center justify-center z-20 pointer-events-none">
            <UploadCloud className="w-10 h-10 text-blue-500 animate-bounce mb-2" />
            <p className="text-sm font-medium text-main">فایل‌ها را اینجا رها کنید</p>
          </div>
        )}
      </div>

      {/* Action Toolbar */}
      <div className="p-2 border-t border-main bg-surface space-y-2 transition-colors">
        <div className="flex items-center justify-between gap-2 px-2 py-1.5 bg-subtle/60 rounded border border-main">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-main select-none min-w-0">
            <input
              type="checkbox"
              checked={recursive}
              onChange={(e) => onRecursiveChange(e.target.checked)}
              className="rounded border-input bg-input text-blue-600 shrink-0"
            />
            <FolderTree className="w-3.5 h-3.5 text-blue-500 shrink-0" />
            <span className="font-medium whitespace-nowrap truncate" title="این گزینه هنگام افزودن پوشه اعمال می‌شود و فایل‌های موجود صف را حذف نمی‌کند.">افزودن زیرپوشه‌ها</span>
          </label>
          <span className="text-[11px] text-muted font-mono whitespace-nowrap shrink-0">
            {recursive ? 'Recursive' : 'Top-only'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-1.5">
          <button
            onClick={onPickFilesNative || (() => fileInputRef.current?.click())}
            disabled={pickerPending}
            className="btn px-2 py-1.5 rounded text-xs bg-subtle hover:bg-hover text-main"
            title="افزودن فایل‌های Markdown با دیالوگ ویندوز"
          >
            {nativeBusy === 'files' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
            ) : (
              <FilePlus className="w-3.5 h-3.5 text-blue-500" />
            )}
            <span>افزودن فایل</span>
          </button>

          <button
            onClick={onAddFolder || (() => fileInputRef.current?.click())}
            disabled={pickerPending}
            className="btn px-2 py-1.5 rounded text-xs bg-subtle hover:bg-hover text-main"
            title="افزودن پوشه حاوی اسناد با دیالوگ ویندوز"
          >
            {nativeBusy === 'folder' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-500" />
            ) : (
              <FolderPlus className="w-3.5 h-3.5 text-amber-500" />
            )}
            <span>افزودن پوشه</span>
          </button>
        </div>

        <div className="grid grid-cols-2 gap-1.5">
          <button
            onClick={onRemoveSelected}
            disabled={selectedIds.size === 0 || pickerPending || isConverting}
            className="btn px-2 py-1.5 rounded text-xs bg-subtle hover:bg-rose-500/15 text-muted hover:text-rose-600 dark:hover:text-rose-400"
            title="حذف فایل‌های انتخاب شده از صف"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-500" />
            <span>حذف انتخاب</span>
          </button>

          <button
            onClick={onClearAll}
            disabled={items.length === 0 || pickerPending || isConverting}
            className="btn px-2 py-1.5 rounded text-xs bg-subtle hover:bg-hover text-muted hover:text-main"
            title="پاکسازی کامل صف"
          >
            <X className="w-3.5 h-3.5" />
            <span>پاک کردن صف</span>
          </button>
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          role="menu"
          className="fixed z-50 bg-card border border-main rounded-lg shadow-2xl py-1 text-xs w-48"
          style={{ top: contextMenu.y, left: contextMenu.x }}
        >
          {onOpenFile && (
            <button
              role="menuitem"
              onClick={() => onOpenFile(contextMenu.item.path)}
              className="btn w-full justify-start px-3 py-1.5 rounded-none hover:bg-subtle text-main"
            >
              <FilePlus className="w-3.5 h-3.5 text-muted" />
              باز کردن فایل در اکسپلورر
            </button>
          )}
          {onRevealFolder && (
            <button
              role="menuitem"
              onClick={() => onRevealFolder(contextMenu.item.path)}
              className="btn w-full justify-start px-3 py-1.5 rounded-none hover:bg-subtle text-main"
            >
              <FolderOpen className="w-3.5 h-3.5 text-muted" />
              نمایش در پوشه مادر
            </button>
          )}
          <button
            role="menuitem"
            onClick={onRemoveSelected}
            className="btn w-full justify-start px-3 py-1.5 rounded-none hover:bg-rose-500/10 text-rose-600 dark:text-rose-400"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-500" />
            حذف از صف
          </button>
        </div>
      )}
    </div>
  );
};
