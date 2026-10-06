import React from 'react';
import { QueueItem } from '../types';
import { ColumnKey } from './Queue/queueTypes';
import { FileText, CheckCircle2, AlertCircle, Loader2, Clock } from 'lucide-react';

interface QueueItemRowProps {
  item: QueueItem;
  isSelected: boolean;
  visibleColumns: Set<ColumnKey>;
  columnWidths?: Record<ColumnKey, number>;
  onSelect: (id: string, e: React.MouseEvent) => void;
  onContextMenu: (e: React.MouseEvent, item: QueueItem) => void;
}

function StatusBadge({ status, error }: { status: QueueItem['status']; error?: string }) {
  switch (status) {
    case 'running':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
          <Loader2 className="w-3 h-3 animate-spin" />
          درحال تبدیل
        </span>
      );
    case 'success':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" />
          موفق
        </span>
      );
    case 'error':
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
          title={error || 'خطا در تبدیل سند'}
        >
          <AlertCircle className="w-3 h-3" />
          خطا
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">
          <Clock className="w-3 h-3" />
          در انتظار
        </span>
      );
  }
}

export const QueueItemRow: React.FC<QueueItemRowProps> = ({
  item,
  isSelected,
  visibleColumns,
  columnWidths,
  onSelect,
  onContextMenu,
}) => {
  return (
    <tr
      onClick={(e) => onSelect(item.id, e)}
      onContextMenu={(e) => onContextMenu(e, item)}
      className={`border-b border-main cursor-pointer select-none transition-colors ${
        isSelected
          ? 'bg-blue-600/15 border-blue-500/40 text-blue-600 dark:text-blue-200'
          : 'hover:bg-subtle text-main'
      }`}
    >
      {visibleColumns.has('name') && (
        <td
          className="px-3 py-2.5"
          style={{ width: columnWidths ? `${columnWidths.name}px` : undefined }}
        >
          <div className="flex items-center gap-2 truncate">
            <FileText className="w-4 h-4 shrink-0 text-muted" />
            <span className="font-mono text-xs truncate" title={item.path}>
              {item.name}
            </span>
          </div>
        </td>
      )}

      {visibleColumns.has('size') && (
        <td
          className="px-3 py-2.5 text-xs text-muted font-mono text-left"
          dir="ltr"
          style={{ width: columnWidths ? `${columnWidths.size}px` : undefined }}
        >
          {item.sizeStr}
        </td>
      )}

      {visibleColumns.has('status') && (
        <td
          className="px-3 py-2.5 text-center"
          style={{ width: columnWidths ? `${columnWidths.status}px` : undefined }}
        >
          <StatusBadge status={item.status} error={item.error} />
        </td>
      )}

      {visibleColumns.has('relativePath') && (
        <td
          className="px-3 py-2.5 text-xs text-muted font-mono"
          dir="ltr"
          style={{ width: columnWidths ? `${columnWidths.relativePath}px` : undefined }}
        >
          <div className="truncate" title={item.relativePath || ''}>
            {item.relativePath || '—'}
          </div>
        </td>
      )}
    </tr>
  );
};
