import React from 'react';
import { ConvertOptions, MermaidTheme } from '../../types';
import { FolderOpen, FileCode } from 'lucide-react';

interface TabMermaidProps {
  options: ConvertOptions;
  onChange: <K extends keyof ConvertOptions>(key: K, value: ConvertOptions[K]) => void;
  onBrowseFile?: (key: keyof ConvertOptions, filter?: string) => void;
  onBrowseDir?: (key: keyof ConvertOptions) => void;
}

const THEMES: MermaidTheme[] = ['default', 'forest', 'dark', 'neutral', 'base', 'null'];

export const TabMermaid: React.FC<TabMermaidProps> = ({
  options,
  onChange,
  onBrowseFile,
  onBrowseDir,
}) => {
  return (
    <div className="space-y-4 text-xs text-main">
      <div>
        <label className="block text-muted mb-1.5 font-medium">تم نمودارهای Mermaid</label>
        <div className="grid grid-cols-3 gap-1.5">
          {THEMES.map((theme) => (
            <button
              key={theme}
              type="button"
              onClick={() => onChange('mermaidTheme', theme)}
              className={`py-1.5 rounded border text-center font-mono capitalize transition-colors cursor-pointer ${
                options.mermaidTheme === theme
                  ? 'bg-blue-600/15 border-blue-500 text-blue-600 dark:text-blue-300 font-medium'
                  : 'bg-subtle border-main hover:bg-hover text-muted'
              }`}
            >
              {theme}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">مهلت رندر نمودار (ثانیه)</label>
        <input
          type="number"
          min={5}
          max={120}
          value={options.mermaidTimeout}
          onChange={(e) => onChange('mermaidTimeout', Number(e.target.value) || 30)}
          className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
        />
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">فایل آفلاین Mermaid.js</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={options.mermaidJs}
            onChange={(e) => onChange('mermaidJs', e.target.value)}
            placeholder="./vendor/mermaid.min.js"
            className="flex-1 px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
            dir="ltr"
          />
          {onBrowseFile && (
            <button
              type="button"
              onClick={() => onBrowseFile('mermaidJs', 'js')}
              className="px-3 py-2 rounded bg-subtle hover:bg-hover text-main transition-colors cursor-pointer"
            >
              <FileCode className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">آدرس آنلاین CDN Mermaid (اختیاری)</label>
        <input
          type="text"
          value={options.mermaidUrl}
          onChange={(e) => onChange('mermaidUrl', e.target.value)}
          placeholder="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
          className="w-full px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
          dir="ltr"
        />
      </div>

      <div>
        <label className="block text-muted mb-1.5 font-medium">مسیر مرورگر آفلاین Playwright</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={options.browsersPath}
            onChange={(e) => onChange('browsersPath', e.target.value)}
            placeholder="./browsers"
            className="flex-1 px-3 py-2 rounded bg-input border border-input text-main font-mono focus:border-blue-500 focus:outline-none"
            dir="ltr"
          />
          {onBrowseDir && (
            <button
              type="button"
              onClick={() => onBrowseDir('browsersPath')}
              className="px-3 py-2 rounded bg-subtle hover:bg-hover text-main transition-colors cursor-pointer"
            >
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="pt-2 border-t border-main">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={options.ignoreMermaidErrors}
            onChange={(e) => onChange('ignoreMermaidErrors', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 focus:ring-0"
          />
          <span>چشم‌پوشی از خطاهای سینتکس Mermaid حین تبدیل</span>
        </label>
      </div>
    </div>
  );
};
