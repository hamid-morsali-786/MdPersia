import React, { useState, useRef, useEffect } from 'react';
import { SlidersHorizontal, Check, RotateCcw, Lock } from 'lucide-react';
import { ColumnKey, QUEUE_COLUMNS } from './queueTypes';

interface ColumnVisibilityPopoverProps {
  visibleColumns: Set<ColumnKey>;
  onToggleColumn: (key: ColumnKey) => void;
  onResetDefaults: () => void;
}

export const ColumnVisibilityPopover: React.FC<ColumnVisibilityPopoverProps> = ({
  visibleColumns,
  onToggleColumn,
  onResetDefaults,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside or pressing Escape
  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    window.addEventListener('mousedown', handlePointerDown);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('mousedown', handlePointerDown);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const visibleCount = visibleColumns.size;
  const totalCount = QUEUE_COLUMNS.length;
  const isCustomized = visibleCount < totalCount;

  return (
    <div className="relative inline-block" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors cursor-pointer border ${
          isOpen
            ? 'bg-hover text-main border-blue-500/50 shadow-sm'
            : isCustomized
            ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30'
            : 'bg-subtle hover:bg-hover text-muted hover:text-main border-main'
        }`}
        title="انتخاب و مدیریت نمایش ستون‌های جدول"
      >
        <SlidersHorizontal className="w-3.5 h-3.5 text-muted" />
        <span className="font-medium">ستون‌ها</span>
        {isCustomized && (
          <span className="text-[10px] px-1 rounded bg-blue-500/20 text-blue-600 dark:text-blue-400 font-mono">
            {visibleCount}/{totalCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          dir="rtl"
          className="absolute left-0 top-full mt-1.5 w-52 bg-card border border-main rounded-lg shadow-xl py-2 z-50 text-xs backdrop-blur-sm animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-3 py-1 flex items-center justify-between border-b border-main pb-2 mb-1">
            <span className="font-semibold text-main">ستون‌های جدول</span>
            <span className="text-[11px] text-muted font-mono">
              {visibleCount} از {totalCount}
            </span>
          </div>

          <div className="py-1 space-y-0.5">
            {QUEUE_COLUMNS.map((col) => {
              const isChecked = visibleColumns.has(col.id);
              return (
                <label
                  key={col.id}
                  className={`flex items-center justify-between px-3 py-1.5 cursor-pointer hover:bg-subtle transition-colors ${
                    col.required ? 'opacity-80 cursor-not-allowed' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={col.required}
                      onChange={() => onToggleColumn(col.id)}
                      className="rounded border-input bg-input text-blue-600 focus:ring-0 cursor-pointer disabled:cursor-not-allowed"
                    />
                    <span className="text-main font-medium">{col.label}</span>
                  </div>

                  {col.required ? (
                    <span
                      className="flex items-center gap-1 text-[10px] text-muted font-medium bg-subtle px-1.5 py-0.5 rounded"
                      title="این ستون ضروری است"
                    >
                      <Lock className="w-2.5 h-2.5" />
                      الزامی
                    </span>
                  ) : (
                    isChecked && <Check className="w-3.5 h-3.5 text-blue-500" />
                  )}
                </label>
              );
            })}
          </div>

          <div className="pt-1.5 mt-1 border-t border-main px-2">
            <button
              type="button"
              onClick={() => {
                onResetDefaults();
                setIsOpen(false);
              }}
              className="w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded hover:bg-subtle text-muted hover:text-main text-xs transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3 h-3 text-muted" />
              <span>بازنشانی پیش‌فرض</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
