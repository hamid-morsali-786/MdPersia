import { DOCUMENT_ACCEPT } from '../services/documentFormats';
import { filterQueueItems } from '../services/queueState';
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
} from 'lucide-react';
import { QueueDisplayOptions, useQueueDisplay } from './Queue/QueueDisplayOptions';
import { formatQueueBytes } from './Queue/queueDisplay';

interface QueuePanelProps {
  items: QueueItem[];
  selectedIds: Set<string>;
  recursive: boolean;
  query: string;
  nativeBusy: 'files' | 'folder' | 'output-dir' | 'explorer' | null;
  isConverting?: boolean;
  onQueryChange: (value: string) => void;
  onRecursiveChange: (value: boolean) => void;
  onSelect: (id: string, e: { ctrlKey: boolean; metaKey: boolean; shiftKey?: boolean }) => void;
  onAddFiles: (files: FileList | File[]) => void;
  onPickFilesNative?: () => void;
  onAddFolder?: () => void;
  onRemoveSelected: () => void;
  onCloseDocument: (id: string) => void;
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
  onCloseDocument,
  onClearAll,
  onOpenFile,
  onRevealFolder,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [detailsId, setDetailsId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; item: QueueItem; row: HTMLElement } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  const closeFocus = useRef<{ id: string; index: number } | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const display = useQueueDisplay();

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
    const row = e.currentTarget as HTMLElement;
    const rect = row.getBoundingClientRect();
    const x = e.clientX || rect.right;
    const y = e.clientY || rect.top;
    const width = 192;
    const height = 112;
    setContextMenu({
      x: Math.max(8, Math.min(x - width, window.innerWidth - width - 8)),
      y: Math.max(8, Math.min(y, window.innerHeight - height - 8)),
      item,
      row,
    });
  };

  const closeContextMenu = () => setContextMenu(null);
  const clearSearch = () => {
    onQueryChange('');
    searchRef.current?.focus();
  };

  useEffect(() => {
    if (!contextMenu) return;
    menuRef.current?.querySelector<HTMLElement>('button:not(:disabled)')?.focus({ preventScroll: true });
    const scroll = () => {
      if (menuRef.current?.contains(document.activeElement)) contextMenu.row.focus({ preventScroll: true });
      setContextMenu(null);
    };
    const pointerDown = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setContextMenu(null);
    };
    window.addEventListener('scroll', scroll, true);
    window.addEventListener('pointerdown', pointerDown);
    return () => {
      window.removeEventListener('scroll', scroll, true);
      window.removeEventListener('pointerdown', pointerDown);
    };
  }, [contextMenu]);

  const trimmed = query.trim();
  useEffect(() => {
    if (!closeFocus.current || items.some(item => item.id === closeFocus.current?.id)) return;
    const { index } = closeFocus.current;
    closeFocus.current = null;
    if (document.activeElement !== document.body) return;
    const rows = tableRef.current?.querySelectorAll<HTMLElement>('tbody tr');
    const next = rows?.[Math.max(0, Math.min(index, rows.length - 1))] ?? searchRef.current;
    next?.focus({ preventScroll: true });
  }, [items]);
  const filtered = useMemo(() => filterQueueItems(items, trimmed), [items, trimmed]);

  // Sized from the rows on screen: a filtered count must not be paired with the full total.
  const totalBytes = filtered.reduce((acc, it) => acc + it.sizeBytes, 0);
  const totalSize = formatQueueBytes(totalBytes);
  const count = filtered.length === items.length ? items.length : `${filtered.length} از ${items.length}`;

  const pickerPending = nativeBusy !== null;

  return (
    <div
      dir="rtl"
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
        accept={DOCUMENT_ACCEPT}
        className="hidden"
      />

      {/* Panel Header */}
      <div className="flex items-center justify-between gap-2 px-3 py-2.5 border-b border-main bg-surface transition-colors">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="grid size-8 shrink-0 place-items-center rounded-md bg-subtle text-[var(--report-accent)]">
            <FileCheck2 className="size-4" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-main">صف فایل‌ها</h2>
            <p className="flex flex-wrap items-center gap-x-1 text-xs leading-4 text-muted">
              <span>{count} سند</span>
              {filtered.length > 0 && <><span aria-hidden="true">·</span><bdi dir="ltr" className="tabular-nums">{totalSize}</bdi></>}
            </p>
          </div>
        </div>

        <QueueDisplayOptions {...display} />
      </div>

      {/* Compact filter bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-main bg-card">
        <div className="relative flex-1 min-w-0">
          <Search className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted" aria-hidden="true" />
          <input
            ref={searchRef}
            dir={query ? 'auto' : 'rtl'}
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onQueryChange('');
            }}
            placeholder="جستجوی نام فایل یا مسیر…"
            aria-label="جستجو در صف فایل‌ها"
            className="w-full min-w-0 rounded-md bg-input border border-input py-1.5 px-7 text-xs text-main placeholder:text-[var(--text-muted)] focus:border-blue-500 focus:outline-none transition-colors duration-150"
          />
          {query && (
            <button
              onClick={clearSearch}
              className="btn absolute left-1 top-1/2 -translate-y-1/2 rounded p-1 text-dim hover:text-[var(--text-main)] hover:bg-[var(--bg-subtle)]"
              title="پاک کردن متن جستجو"
              aria-label="پاک کردن متن جستجو"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Main Table / Drop Area */}
      <div className="queue-scroll min-h-0 flex-1 overflow-y-auto relative" onKeyDown={(event) => {
        const row = (event.target as HTMLElement).closest<HTMLElement>('[data-document-id]');
        if (!row) return;
        const index = filtered.findIndex(item => item.id === row.dataset.documentId);
        if (event.key === 'Delete' || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'w')) {
          const item = filtered[index];
          if (item && !isConverting) closeFocus.current = { id: item.id, index };
          return;
        }
        if (event.target !== row) return;
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
              هیچ سندی با «<bdi dir="auto" className="[overflow-wrap:anywhere]">{trimmed}</bdi>» مطابقت نداشت.
            </p>
            <button
              onClick={clearSearch}
              className="btn mt-2 px-2.5 py-1 rounded text-xs bg-subtle hover:bg-[var(--bg-hover)] text-main"
            >
              نمایش همه
            </button>
          </div>
        ) : (
          <table ref={tableRef} role="grid" aria-label="فایل‌های صف" aria-multiselectable="true"
            className="w-full border-separate border-spacing-y-1 px-2 table-fixed text-xs">
            <tbody>
              {filtered.map((item, index) => (
                <QueueItemRow
                  key={item.id}
                  item={item}
                  isSelected={selectedIds.has(item.id)}
                  displayFields={display.fields}
                  detailsOpen={detailsId === item.id}
                  onToggleDetails={() => setDetailsId(current => current === item.id ? null : item.id)}
                  onSelect={onSelect}
                  onClose={id => { closeFocus.current = { id, index }; onCloseDocument(id); }}
                  closeDisabled={isConverting}
                  onContextMenu={handleContextMenu}
                  onOpenFile={onOpenFile}
                />
              ))}
            </tbody>
          </table>
        )}

        {/* Drag Overlay */}
        {isDragOver && (
          <div className="absolute inset-0 bg-blue-500/10 border-2 border-dashed border-blue-500 backdrop-blur-sm flex flex-col items-center justify-center z-20 pointer-events-none">
            <UploadCloud className="w-10 h-10 text-blue-500 mb-2" />
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
        </div>

        <div className="grid grid-cols-2 gap-1.5">
          <button
            onClick={onPickFilesNative || (() => fileInputRef.current?.click())}
            disabled={pickerPending}
            className="btn px-2 py-1.5 rounded text-xs bg-subtle hover:bg-[var(--bg-hover)] text-main"
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
            className="btn px-2 py-1.5 rounded text-xs bg-subtle hover:bg-[var(--bg-hover)] text-main"
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
            className="btn px-2 py-1.5 rounded text-xs bg-subtle hover:bg-[var(--bg-hover)] text-muted hover:text-[var(--text-main)]"
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
          ref={menuRef}
          role="menu"
          aria-label="عملیات فایل"
          className="fixed z-50 bg-card border border-main rounded-lg shadow-2xl py-1 text-xs w-48"
          style={{ top: contextMenu.y, left: contextMenu.x }}
          onKeyDown={event => {
            event.stopPropagation();
            if (event.key === 'Escape' || event.key === 'Tab') {
              if (event.key === 'Escape') event.preventDefault();
              contextMenu.row.focus({ preventScroll: true });
              closeContextMenu();
              return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const actions = [...event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')];
            if (!actions.length) return;
            const current = actions.indexOf(event.target as HTMLButtonElement);
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? actions.length - 1
              : (current + (event.key === 'ArrowDown' ? 1 : -1) + actions.length) % actions.length;
            actions[next].focus({ preventScroll: true });
          }}
        >
          {onOpenFile && (
            <button
              role="menuitem"
              onClick={() => { contextMenu.row.focus({ preventScroll: true }); onOpenFile(contextMenu.item.path); }}
              className="btn w-full justify-start px-3 py-1.5 rounded-none hover:bg-[var(--bg-subtle)] text-main"
            >
              <FilePlus className="w-3.5 h-3.5 text-muted" />
              نمایش فایل در پوشه
            </button>
          )}
          {onRevealFolder && (
            <button
              role="menuitem"
              onClick={() => { contextMenu.row.focus({ preventScroll: true }); onRevealFolder(contextMenu.item.path); }}
              className="btn w-full justify-start px-3 py-1.5 rounded-none hover:bg-[var(--bg-subtle)] text-main"
            >
              <FolderOpen className="w-3.5 h-3.5 text-muted" />
              باز کردن پوشهٔ فایل
            </button>
          )}
          <button
            role="menuitem"
            onClick={() => {
              contextMenu.row.focus({ preventScroll: true });
              closeFocus.current = { id: contextMenu.item.id, index: filtered.findIndex(item => item.id === contextMenu.item.id) };
              onCloseDocument(contextMenu.item.id);
            }}
            disabled={isConverting}
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
