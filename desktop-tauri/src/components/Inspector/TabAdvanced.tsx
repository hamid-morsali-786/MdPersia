import React from 'react';
import { ConvertOptions } from '../../types';

interface TabAdvancedProps {
  options: ConvertOptions;
  onChange: <K extends keyof ConvertOptions>(key: K, value: ConvertOptions[K]) => void;
}

export const TabAdvanced: React.FC<TabAdvancedProps> = ({ options, onChange }) => {
  return (
    <div className="space-y-4 text-xs text-main">
      <div>
        <label className="block text-muted mb-1.5 font-medium">پسوندهای فایل‌های مارک‌داون</label>
        <input
          type="text"
          value={options.extensions}
          onChange={(e) => onChange('extensions', e.target.value)}
          placeholder=".md, .markdown"
          className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
          dir="ltr"
        />
        <span className="text-[11px] text-dim mt-1 block">
          پسوندها را با کاما جدا کنید (پیش‌فرض: .md, .markdown)
        </span>
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">پسوند فایل خروجی RTL Wrap</label>
        <input
          type="text"
          value={options.wrapRtlSuffix}
          onChange={(e) => onChange('wrapRtlSuffix', e.target.value)}
          placeholder=".rtl.md"
          className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
          dir="ltr"
        />
        <span className="text-[11px] text-dim mt-1 block">
          پسوند افزوده‌شده به نام فایل هنگام راست‌چین‌سازی مارک‌داون
        </span>
      </div>

      <div className="pt-2 border-t border-main space-y-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.recursive}
            onChange={(e) => onChange('recursive', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>پویش تو در تو و بازگشتی پوشه‌ها (Recursive)</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.keepHtml}
            onChange={(e) => onChange('keepHtml', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>حفظ فایل‌های واسط HTML بعد از تبدیل</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.failFast}
            onChange={(e) => onChange('failFast', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>توقف فوری دسته تبدیل در اولین خطای رخ داده (Fail Fast)</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.verbose}
            onChange={(e) => onChange('verbose', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>نمایش گزارش کامل و جزئیات دقیق فرآیند در کنسول (Verbose)</span>
        </label>
      </div>
    </div>
  );
};
