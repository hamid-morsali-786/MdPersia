import React, { useState, useRef } from 'react';
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
} from 'lucide-react';
import { QUEUE_COLUMNS } from './Queue/queueTypes';
import { useColumnVisibility } from './Queue/useColumnVisibility';
import { useColumnResize } from './Queue/useColumnResize';
import { ResizableHeaderCell } from './Queue/ResizableHeaderCell';
import { ColumnVisibilityPopover } from './Queue/ColumnVisibilityPopover';

interface QueuePanelProps {
  items: QueueItem[];
  selectedIds: Set<string>;
  recursive: boolean;
  onRecursiveChange: (value: boolean) => void;
  onSelect: (id: string, e: React.MouseEvent) => void;
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

  const handleDragLeave = () => {
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

  const totalBytes = items.reduce((acc, it) => acc + it.sizeBytes, 0);
  const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);

  const visibleColDefs = QUEUE_COLUMNS.filter((c) => visibleColumns.has(c.id));
  const totalTableWidth = visibleColDefs.reduce(
    (acc, c) => acc + (columnWidths[c.id] || c.defaultWidth),
    0
  );

  return (
    <div
      className="flex flex-col h-full bg-card border-l border-main select-none relative transition-colors duration-200"
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
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-main bg-surface transition-colors">
        <div className="flex items-center gap-2">
          <FileCheck2 className="w-4 h-4 text-blue-500" />
          <h2 className="text-sm font-semibold text-main">صف فایل‌ها</h2>
          <span className="text-xs px-2 py-0.5 rounded-full bg-subtle text-muted font-mono">
            {items.length}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted font-mono">{totalMB} MB</span>
          <ColumnVisibilityPopover
            visibleColumns={visibleColumns}
            onToggleColumn={toggleColumn}
            onResetDefaults={handleResetDefaults}
          />
        </div>
      </div>

      {/* Main Table / Drop Area */}
      <div className="flex-1 overflow-x-auto overflow-y-auto relative">
        {items.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center text-muted">
            <div className="w-12 h-12 rounded-xl bg-subtle flex items-center justify-center mb-3 text-muted">
              <UploadCloud className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-main mb-1">هیچ سندی افزوده نشده است</p>
            <p className="text-xs text-muted max-w-[200px] leading-relaxed">
              فایل‌های Markdown خود را به اینجا بکشید یا دکمه‌های زیر را انتخاب کنید.
            </p>
          </div>
        ) : (
          <table
            className="w-full text-right text-xs table-fixed"
            style={{ minWidth: `${totalTableWidth}px` }}
          >
            <thead className="sticky top-0 bg-surface backdrop-blur border-b border-main text-muted z-10">
              <tr>
                {visibleColDefs.map((col) => (
                  <ResizableHeaderCell
                    key={col.id}
                    column={col}
                    width={columnWidths[col.id] || col.defaultWidth}
                    isResizing={resizingCol === col.id}
                    onStartResize={(e) => startResize(col.id, e)}
                    onResetWidth={() => resetColumnWidth(col.id)}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <QueueItemRow
                  key={item.id}
                  item={item}
                  isSelected={selectedIds.has(item.id)}
                  visibleColumns={visibleColumns}
                  columnWidths={columnWidths}
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
        {/* Recursive Traversal Checkbox */}
        <div className="flex items-center justify-between px-2 py-1.5 bg-subtle/60 rounded border border-main">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-main select-none">
            <input
              type="checkbox"
              checked={recursive}
              onChange={(e) => onRecursiveChange(e.target.checked)}
              className="rounded border-input bg-input text-blue-600 focus:ring-0"
            />
            <FolderTree className="w-3.5 h-3.5 text-blue-500" />
            <span className="font-medium">پیمایش بازگشتی زیرپوشه‌ها</span>
          </label>
          <span className="text-[11px] text-muted font-mono">
            {recursive ? 'Recursive' : 'Top-only'}
          </span>
        </div>

        {/* Buttons Grid */}
        <div className="grid grid-cols-4 gap-1.5">
          <button
            onClick={onPickFilesNative || (() => fileInputRef.current?.click())}
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs bg-subtle hover:bg-hover text-main transition-colors cursor-pointer"
            title="افزودن فایل‌های Markdown با دیالوگ ویندوز"
          >
            <FilePlus className="w-3.5 h-3.5 text-blue-500" />
            <span>+ فایل</span>
          </button>

          <button
            onClick={onAddFolder || (() => fileInputRef.current?.click())}
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs bg-subtle hover:bg-hover text-main transition-colors cursor-pointer"
            title="افزودن پوشه حاوی اسناد با دیالوگ ویندوز"
          >
            <FolderPlus className="w-3.5 h-3.5 text-amber-500" />
            <span>+ پوشه</span>
          </button>

          <button
            onClick={onRemoveSelected}
            disabled={selectedIds.size === 0}
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs bg-subtle hover:bg-rose-500/15 text-muted hover:text-rose-600 dark:hover:text-rose-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            title="حذف فایل‌های انتخاب شده"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-500" />
            <span>حذف</span>
          </button>

          <button
            onClick={onClearAll}
            disabled={items.length === 0}
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs bg-subtle hover:bg-hover text-muted hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            title="پاکسازی کامل صف"
          >
            <span>پاکسازی</span>
          </button>
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-card border border-main rounded-lg shadow-2xl py-1 text-xs w-44"
          style={{ top: contextMenu.y, left: contextMenu.x }}
        >
          {onOpenFile && (
            <button
              onClick={() => onOpenFile(contextMenu.item.path)}
              className="w-full text-right px-3 py-1.5 hover:bg-subtle text-main flex items-center gap-2 cursor-pointer"
            >
              <FilePlus className="w-3.5 h-3.5 text-muted" />
              باز کردن فایل
            </button>
          )}
          {onRevealFolder && (
            <button
              onClick={() => onRevealFolder(contextMenu.item.path)}
              className="w-full text-right px-3 py-1.5 hover:bg-subtle text-main flex items-center gap-2 cursor-pointer"
            >
              <FolderOpen className="w-3.5 h-3.5 text-muted" />
              نمایش در پوشه
            </button>
          )}
          <button
            onClick={onRemoveSelected}
            className="w-full text-right px-3 py-1.5 hover:bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center gap-2 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-500" />
            حذف از صف
          </button>
        </div>
      )}
    </div>
  );
};
