import React from 'react';
import { ConvertOptions } from '../../types';

interface TabDocxProps {
  options: ConvertOptions;
  onChange: <K extends keyof ConvertOptions>(key: K, value: ConvertOptions[K]) => void;
}

const SCALE_OPTIONS = [1, 2, 3, 4];

export const TabDocx: React.FC<TabDocxProps> = ({ options, onChange }) => {
  return (
    <div className="space-y-4 text-xs text-main">
      <div>
        <label className="block text-muted mb-1.5 font-medium">کیفیت رندر تصاویر دیاگرام (Scale)</label>
        <div className="grid grid-cols-4 gap-2">
          {SCALE_OPTIONS.map((scale) => (
            <button
              key={scale}
              type="button"
              onClick={() => onChange('docxImageScale', scale)}
              className={`py-1.5 rounded border text-center font-mono transition-colors cursor-pointer ${
                options.docxImageScale === scale
                  ? 'bg-blue-600/15 border-blue-500 text-blue-600 dark:text-blue-300 font-medium'
                  : 'bg-subtle border-main hover:bg-hover text-muted'
              }`}
            >
              {scale}x
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-muted mb-1.5 font-medium">حداقل عرض تصویر (اینچ)</label>
          <input
            type="number"
            step="0.5"
            min="1.0"
            max="8.0"
            value={options.docxImageMinWidth}
            onChange={(e) => onChange('docxImageMinWidth', parseFloat(e.target.value) || 4.0)}
            className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-muted mb-1.5 font-medium">حداکثر عرض تصویر (اینچ)</label>
          <input
            type="number"
            step="0.5"
            min="2.0"
            max="10.0"
            value={options.docxImageMaxWidth}
            onChange={(e) => onChange('docxImageMaxWidth', parseFloat(e.target.value) || 6.5)}
            className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">اندازه قلم متن بدنه (pt)</label>
        <input
          type="number"
          min="8"
          max="24"
          value={options.docxFontSize}
          onChange={(e) => onChange('docxFontSize', parseInt(e.target.value, 10) || 12)}
          className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
        />
      </div>

      <div className="pt-2 border-t border-main space-y-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.docxHighlightCode}
            onChange={(e) => onChange('docxHighlightCode', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>رنگ‌آمیزی نحوی بلوک‌های کد در ورد (Highlighting)</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.docxPageNumbers}
            onChange={(e) => onChange('docxPageNumbers', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>درج شماره صفحه در پانویس سند ورد</span>
        </label>
      </div>
    </div>
  );
};
