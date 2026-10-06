import React from 'react';
import { ConvertOptions, PageFormat, MarginOption } from '../../types';

interface TabDocumentProps {
  options: ConvertOptions;
  onChange: <K extends keyof ConvertOptions>(key: K, value: ConvertOptions[K]) => void;
}

const PAGE_FORMATS: PageFormat[] = ['A4', 'Letter', 'Legal', 'A3'];
const MARGINS: MarginOption[] = ['10mm', '15mm', '20mm', '25mm', '30mm'];

export const TabDocument: React.FC<TabDocumentProps> = ({ options, onChange }) => {
  const isDocx = options.format === 'docx';

  return (
    <div className="space-y-4 text-xs text-main">
      <div>
        <label className="block text-muted mb-1.5 font-medium">قطع صفحه (اندازه کاغذ)</label>
        <div className="grid grid-cols-4 gap-2">
          {PAGE_FORMATS.map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() => onChange('pageFormat', fmt)}
              className={`py-1.5 rounded border text-center transition-colors cursor-pointer ${
                options.pageFormat === fmt
                  ? 'bg-blue-600/15 border-blue-500 text-blue-600 dark:text-blue-300 font-medium'
                  : 'bg-subtle border-main hover:bg-hover text-muted'
              }`}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">حاشیه صفحه (Margins)</label>
        <div className="grid grid-cols-5 gap-1.5">
          {MARGINS.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => onChange('margin', m)}
              className={`py-1.5 rounded border text-center font-mono transition-colors cursor-pointer ${
                options.margin === m
                  ? 'bg-blue-600/15 border-blue-500 text-blue-600 dark:text-blue-300 font-medium'
                  : 'bg-subtle border-main hover:bg-hover text-muted'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="pt-2 border-t border-main space-y-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.recursive}
            onChange={(e) => onChange('recursive', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span className="font-medium">پیمایش بازگشتی تمام زیرپوشه‌ها (Recursive)</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.landscape}
            onChange={(e) => onChange('landscape', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>جهت صفحه افقی (Landscape)</span>
        </label>

        {!isDocx && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={options.pdfPageNumbers}
              onChange={(e) => onChange('pdfPageNumbers', e.target.checked)}
              className="rounded border-input bg-input text-blue-600 focus:ring-0"
            />
            <span>درج شماره صفحه در فوتر PDF</span>
          </label>
        )}

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.stripEmojis}
            onChange={(e) => onChange('stripEmojis', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>حذف اموجی‌ها از خروجی (جهت سازگاری چاپ)</span>
        </label>
      </div>
    </div>
  );
};
