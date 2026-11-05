import React from 'react';
import { QueueItem } from '../types';
import { ColumnKey } from './Queue/queueTypes';
import { FileText, CheckCircle2, AlertCircle, Loader2, Clock, Eye } from 'lucide-react';

interface QueueItemRowProps {
  item: QueueItem;
  isSelected: boolean;
  visibleColumns: Set<ColumnKey>;
  columnWidths?: Record<ColumnKey, number>;
  /** Last visible column stretches to the panel width so the table never scrolls sideways. */
  fillColumn?: ColumnKey;
  onSelect: (id: string, e: { ctrlKey: boolean; metaKey: boolean }) => void;
  onContextMenu: (e: React.MouseEvent, item: QueueItem) => void;
}

const BADGE = 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap shrink-0';

function StatusBadge({ status, error }: { status: QueueItem['status']; error?: string }) {
  switch (status) {
    case 'watching':
      return <span className={`${BADGE} bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30`}>
        <Eye className="w-3 h-3 shrink-0" /><span>پایش زنده</span>
      </span>;
    case 'running':
      return (
        <span className={`${BADGE} bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30`}>
          <Loader2 className="w-3 h-3 animate-spin shrink-0" />
          <span>در حال تبدیل</span>
        </span>
      );
    case 'success':
      return (
        <span className={`${BADGE} bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30`}>
          <CheckCircle2 className="w-3 h-3 shrink-0" />
          <span>تکمیل شد</span>
        </span>
      );
    case 'error':
      return (
        <span
          className={`${BADGE} bg-rose-500/15 text-rose-600 dark:text-rose-300 border border-rose-500/30`}
          title={error || 'خطا در تبدیل سند'}
        >
          <AlertCircle className="w-3 h-3 shrink-0" />
          <span>خطا</span>
        </span>
      );
    default:
      return (
        <span className={`${BADGE} bg-zinc-500/10 text-zinc-600 dark:text-zinc-300 border border-zinc-500/20`}>
          <Clock className="w-3 h-3 shrink-0" />
          <span>در انتظار</span>
        </span>
      );
  }
}

export const QueueItemRow: React.FC<QueueItemRowProps> = ({
  item,
  isSelected,
  visibleColumns,
  columnWidths,
  fillColumn,
  onSelect,
  onContextMenu,
}) => {
  const widthOf = (key: ColumnKey) =>
    fillColumn === key || !columnWidths ? undefined : `${columnWidths[key]}px`;

  return (
    <tr
      tabIndex={0}
      data-document-id={item.id}
      onClick={(e) => onSelect(item.id, e)}
      onContextMenu={(e) => onContextMenu(e, item)}
      aria-selected={isSelected}
      className={`border-b border-main cursor-pointer select-none transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-blue-500 focus-visible:-outline-offset-2 ${
        isSelected
          ? 'bg-blue-600/15 text-blue-700 dark:text-blue-200'
          : 'hover:bg-subtle text-main'
      }`}
    >
      {visibleColumns.has('name') && (
        <td
          className="px-3 py-2.5"
          style={{ width: widthOf('name') }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-4 h-4 shrink-0 text-muted" />
            {/* Latin filenames need an LTR run: RTL clipping hides the head, not the tail. */}
            <span className="font-mono text-xs truncate min-w-0" dir="ltr" title={item.path}>
              {item.name}
            </span>
            {item.unsaved && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" role="img" aria-label="تغییرات ذخیره‌نشده" title="تغییرات ذخیره‌نشده" />}
          </div>
        </td>
      )}

      {visibleColumns.has('size') && (
        <td
          className="px-2 py-2.5 text-xs text-muted font-mono text-center"
          dir="ltr"
          style={{ width: widthOf('size') }}
        >
          <span className="block truncate whitespace-nowrap">{item.sizeStr || '—'}</span>
        </td>
      )}

      {visibleColumns.has('status') && (
        <td
          className="px-2 py-2.5 text-center"
          style={{ width: widthOf('status') }}
        >
          <div className="flex justify-center overflow-hidden">
            <StatusBadge status={item.status} error={item.error} />
          </div>
        </td>
      )}

      {visibleColumns.has('relativePath') && (
        <td
          className="px-3 py-2.5 text-xs text-muted font-mono"
          dir="ltr"
          style={{ width: widthOf('relativePath') }}
        >
          <div className="truncate" title={item.relativePath || ''}>
            {item.relativePath || '—'}
          </div>
        </td>
      )}
    </tr>
  );
};
