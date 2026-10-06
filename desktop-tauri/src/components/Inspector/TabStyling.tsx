import React from 'react';
import { ConvertOptions } from '../../types';
import { FolderOpen, FileCode } from 'lucide-react';

interface TabStylingProps {
  options: ConvertOptions;
  onChange: <K extends keyof ConvertOptions>(key: K, value: ConvertOptions[K]) => void;
  onBrowseFile?: (key: keyof ConvertOptions, filter?: string) => void;
  onBrowseDir?: (key: keyof ConvertOptions) => void;
}

export const TabStyling: React.FC<TabStylingProps> = ({
  options,
  onChange,
  onBrowseFile,
  onBrowseDir,
}) => {
  return (
    <div className="space-y-4 text-xs text-main">
      <div>
        <label className="block text-muted mb-1.5 font-medium">قلم پیش‌فرض (Font Family)</label>
        <input
          type="text"
          value={options.fontFamily}
          onChange={(e) => onChange('fontFamily', e.target.value)}
          placeholder="Vazirmatn, Segoe UI, Tahoma"
          className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
          dir="ltr"
        />
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">فایل فونت اختصاصی (@font-face)</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={options.fontFile}
            onChange={(e) => onChange('fontFile', e.target.value)}
            placeholder="مسیر فایل فونت مثلاً Vazirmatn.ttf"
            className="flex-1 px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
            dir="ltr"
          />
          {onBrowseFile && (
            <button
              type="button"
              onClick={() => onBrowseFile('fontFile', 'ttf,otf,woff2')}
              className="px-3 py-2 rounded bg-subtle hover:bg-hover text-main transition-colors cursor-pointer"
            >
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">پوشه فونت‌های آفلاین (Font Dir)</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={options.fontDir}
            onChange={(e) => onChange('fontDir', e.target.value)}
            placeholder="./fonts"
            className="flex-1 px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
            dir="ltr"
          />
          {onBrowseDir && (
            <button
              type="button"
              onClick={() => onBrowseDir('fontDir')}
              className="px-3 py-2 rounded bg-subtle hover:bg-hover text-main transition-colors cursor-pointer"
            >
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">استایل سفارشی (Custom CSS)</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={options.customCss}
            onChange={(e) => onChange('customCss', e.target.value)}
            placeholder="مسیر فایل CSS الحاقی"
            className="flex-1 px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
            dir="ltr"
          />
          {onBrowseFile && (
            <button
              type="button"
              onClick={() => onBrowseFile('customCss', 'css')}
              className="px-3 py-2 rounded bg-subtle hover:bg-hover text-main transition-colors cursor-pointer"
            >
              <FileCode className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
