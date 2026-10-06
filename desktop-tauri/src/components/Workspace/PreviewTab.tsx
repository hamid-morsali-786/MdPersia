import React from 'react';
import { QueueItem } from '../../types';
import { ExternalLink, FileText } from 'lucide-react';

interface PreviewTabProps {
  selectedItem: QueueItem | null;
  markdownContent?: string;
  onOpenInEditor?: (path: string) => void;
}

export const PreviewTab: React.FC<PreviewTabProps> = ({
  selectedItem,
  markdownContent,
  onOpenInEditor,
}) => {
  if (!selectedItem) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-muted">
        <FileText className="w-12 h-12 stroke-[1.5] mb-3 text-dim" />
        <p className="text-sm font-medium text-main">سندی انتخاب نشده است</p>
        <p className="text-xs text-muted mt-1 max-w-[220px]">
          یک فایل را از لیست سمت راست انتخاب کنید تا پیش‌نمایش آن نمایش داده شود.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-card transition-colors duration-200">
      {/* File Info Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-main bg-surface transition-colors">
        <div className="flex items-center gap-2 truncate">
          <FileText className="w-4 h-4 text-blue-500 shrink-0" />
          <span className="text-xs font-mono font-medium text-main truncate">
            {selectedItem.name}
          </span>
          <span className="text-[11px] text-muted font-mono">({selectedItem.sizeStr})</span>
        </div>

        {onOpenInEditor && (
          <button
            onClick={() => onOpenInEditor(selectedItem.path)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-subtle hover:bg-hover text-main text-xs transition-colors cursor-pointer"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>باز کردن در ویرایشگر</span>
          </button>
        )}
      </div>

      {/* Content Rendering Body */}
      <div className="flex-1 overflow-y-auto p-6 font-sans text-main leading-relaxed text-right" dir="rtl">
        {markdownContent ? (
          <div className="prose dark:prose-invert max-w-none text-sm space-y-3 whitespace-pre-wrap font-sans text-main">
            {markdownContent}
          </div>
        ) : (
          <div className="space-y-4">
            <h1 className="text-xl font-bold text-main border-b border-main pb-2">
              {selectedItem.name.replace(/\.[^/.]+$/, '')}
            </h1>
            <p className="text-muted text-xs font-mono" dir="ltr">
              Path: {selectedItem.path}
            </p>
            <div className="p-4 rounded-lg bg-subtle border border-main text-xs text-main leading-6">
              <p>این سند آماده تبدیل با موتور اختصاصی `fa-md-pdf` است.</p>
              <ul className="list-disc list-inside mt-2 text-muted space-y-1">
                <li>پشتیبانی از متون دوزبانه فارسی و انگلیسی بدون به‌هم‌ریختگی</li>
                <li>رندر خودکار نمودارهای Mermaid به صورت برداری</li>
                <li>شماره‌گذاری فارسی صفحات و فونت وزیرمتن</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
