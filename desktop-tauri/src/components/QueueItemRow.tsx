import React, { useId, useRef } from 'react';
import { AlertCircle, CheckCircle2, Clock, Eye, Folder, FolderOpen, Info, Loader2, X } from 'lucide-react';
import type { QueueItem } from '../types';
import { formatQueueBytes, type QueueDisplayField } from './Queue/queueDisplay';
import { Tooltip } from './Tooltip';

interface QueueItemRowProps {
  item: QueueItem;
  isSelected: boolean;
  displayFields: ReadonlySet<QueueDisplayField>;
  detailsOpen: boolean;
  onToggleDetails: () => void;
  onSelect: (id: string, e: { ctrlKey: boolean; metaKey: boolean; shiftKey?: boolean }) => void;
  onClose: (id: string) => void;
  closeDisabled: boolean;
  onContextMenu: (e: React.MouseEvent, item: QueueItem) => void;
  onOpenFile?: (path: string) => void;
}

const STATUS = {
  pending: { label: 'در انتظار', icon: Clock, color: 'var(--text-muted)' },
  watching: { label: 'پایش زنده', icon: Eye, color: 'var(--report-accent)' },
  running: { label: 'در حال تبدیل', icon: Loader2, color: 'var(--report-accent)' },
  success: { label: 'تکمیل شد', icon: CheckCircle2, color: 'var(--report-success)' },
  error: { label: 'خطا در تبدیل', icon: AlertCircle, color: 'var(--report-error)' },
} satisfies Record<QueueItem['status'], { label: string; icon: typeof Clock; color: string }>;

export function QueueItemRow({
  item,
  isSelected,
  displayFields,
  detailsOpen,
  onToggleDetails,
  onSelect,
  onClose,
  closeDisabled,
  onContextMenu,
  onOpenFile,
}: QueueItemRowProps) {
  const detailsId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const status = STATUS[item.status];
  const showStatus = displayFields.has('status');
  const StatusIcon = showStatus ? status.icon : Info;
  const size = formatQueueBytes(item.sizeBytes);
  const folderName = item.path.split(/[\\/]/).at(-2);
  const showFolder = displayFields.has('relativePath') && folderName;
  const showSize = displayFields.has('size');
  const extensionAt = item.name.lastIndexOf('.');
  const stem = extensionAt > 0 ? item.name.slice(0, extensionAt) : item.name;
  const extension = extensionAt > 0 ? item.name.slice(extensionAt) : '';
  const label = detailsOpen ? 'بستن جزئیات فایل' : 'جزئیات فایل';

  return (
    <tr
      tabIndex={0}
      data-document-id={item.id}
      onClick={event => onSelect(item.id, event)}
      onContextMenu={event => onContextMenu(event, item)}
      onKeyDown={event => {
        if (event.key === 'Escape' && detailsOpen) {
          event.stopPropagation();
          onToggleDetails();
          trigger.current?.focus({ preventScroll: true });
        }
      }}
      aria-selected={isSelected}
      className="cursor-pointer focus-visible:outline-2 focus-visible:outline-blue-500 focus-visible:-outline-offset-2"
    >
      <td className={`rounded-lg border px-2.5 py-2.5 text-main ${isSelected
        ? 'border-blue-500/35 bg-blue-600/10 dark:bg-blue-500/15'
        : 'border-transparent hover:border-[var(--border-main)] hover:bg-[var(--bg-subtle)]'}`}>
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-1.5">
          <div dir="ltr" className="flex min-w-0 flex-col items-end gap-0.5">
            <span className="queue-file-name text-[13px] leading-5 font-semibold" dir="ltr">
              <bdi dir="auto">{stem}</bdi>{extension && <span className="queue-file-extension">{extension}</span>}
            </span>
            {(showSize || showFolder || item.unsaved) && (
              <div dir="rtl" className="flex max-w-full items-center gap-2 text-xs leading-4 text-muted">
                {item.unsaved && <span className="size-1.5 shrink-0 rounded-full bg-amber-500" role="img" aria-label="تغییرات ذخیره‌نشده" title="تغییرات ذخیره‌نشده" />}
                {showSize && <bdi className="shrink-0 tabular-nums" dir="ltr" aria-label={`حجم فایل ${size}`}>{size}</bdi>}
                {showFolder && <span className="inline-flex min-w-0 items-center gap-1">
                  <Folder className="size-3 shrink-0" aria-hidden="true" />
                  <bdi dir="auto" className="truncate">{folderName}</bdi>
                </span>}
              </div>
            )}
          </div>
          <div className="flex shrink-0 gap-0.5" onClick={event => event.stopPropagation()}>
            <Tooltip label={showStatus ? `${status.label} · ${label}` : label}>
              <button ref={trigger} type="button" aria-expanded={detailsOpen}
                aria-controls={detailsOpen ? detailsId : undefined}
                aria-label={`${label} · ${item.name}${showStatus ? ` · ${status.label}` : ''}`}
                className={`btn size-7 justify-center rounded-md hover:bg-[var(--bg-hover)] ${detailsOpen ? 'bg-subtle' : ''}`}
                style={{ color: showStatus ? status.color : 'var(--text-muted)' }}
                onClick={onToggleDetails}>
                <StatusIcon className={`size-3.5 ${showStatus && item.status === 'running' ? 'motion-safe:animate-spin' : ''}`} aria-hidden="true" />
              </button>
            </Tooltip>
            <Tooltip label="بستن سند">
              <button type="button" disabled={closeDisabled} aria-label={`بستن ${item.name}`}
                className="btn size-7 justify-center rounded-md text-muted hover:bg-rose-500/10 hover:text-[var(--report-error)]"
                onClick={() => onClose(item.id)}>
                <X className="size-3.5" aria-hidden="true" />
              </button>
            </Tooltip>
          </div>
        </div>
        {detailsOpen && (
          <div id={detailsId} className="mt-2 cursor-default rounded-md border border-main bg-surface p-2 text-xs text-muted"
            onClick={event => event.stopPropagation()} onContextMenu={event => event.stopPropagation()}>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span style={{ color: status.color }}>{status.label}</span>
              <bdi className="tabular-nums" dir="ltr">{size}</bdi>
              {item.unsaved && <span className="text-[var(--report-warning)]">تغییرات ذخیره‌نشده</span>}
            </div>
            {item.error && <>
              <p dir="auto" className="mt-1 break-words select-text text-[var(--report-error)]">{item.error}</p>
              <p>علت خطا را در «کنسول و گزارش‌ها» ببینید.</p>
            </>}
            <p className="mt-2 font-medium">مسیر فایل</p>
            <bdi dir="ltr" className="block select-text text-left leading-5 text-main [overflow-wrap:anywhere]">{item.path}</bdi>
            {onOpenFile && (
              <button type="button" className="btn mt-1 min-h-7 gap-1.5 rounded px-1.5 text-[var(--report-accent)] hover:bg-[var(--bg-subtle)]"
                onClick={() => onOpenFile(item.path)}>
                <FolderOpen className="size-3.5" aria-hidden="true" />
                نمایش فایل در پوشه
              </button>
            )}
          </div>
        )}
      </td>
    </tr>
  );
}
