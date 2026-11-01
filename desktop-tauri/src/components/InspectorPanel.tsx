import React, { useState } from 'react';
import { ConvertOptions, OutputFormat } from '../types';
import { TabDocument } from './Inspector/TabDocument';
import { TabStyling } from './Inspector/TabStyling';
import { TabMermaid } from './Inspector/TabMermaid';
import { TabDocx } from './Inspector/TabDocx';
import { TabAdvanced } from './Inspector/TabAdvanced';
import {
  FolderOpen,
  Play,
  Square,
  Eye,
  FileText,
  Palette,
  Workflow,
  FileType,
  SlidersHorizontal,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { Tooltip } from './Tooltip';

interface InspectorPanelProps {
  options: ConvertOptions;
  isRunning: boolean;
  isWatching: boolean;
  hasDocuments?: boolean;
  /** Waiting on the native folder dialog for the output directory. */
  outputDirBusy?: boolean;
  onOptionsChange: <K extends keyof ConvertOptions>(key: K, value: ConvertOptions[K]) => void;
  onConvert: () => void;
  onCancel: () => void;
  onBrowseOutputDir: () => void;
  onOpenOutputDir: () => void;
  onBrowseFile?: (key: keyof ConvertOptions, filter?: string) => void;
  onBrowseDir?: (key: keyof ConvertOptions) => void;
}

type TabKey = 'doc' | 'style' | 'mermaid' | 'docx' | 'advanced';

const TABS: { id: TabKey; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'doc', label: 'سند', icon: FileText },
  { id: 'style', label: 'استایل', icon: Palette },
  { id: 'mermaid', label: 'مرمید', icon: Workflow },
  { id: 'docx', label: 'ورد', icon: FileType },
  { id: 'advanced', label: 'پیشرفته', icon: SlidersHorizontal },
];

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  options,
  isRunning,
  isWatching,
  hasDocuments = true,
  outputDirBusy = false,
  onOptionsChange,
  onConvert,
  onCancel,
  onBrowseOutputDir,
  onOpenOutputDir,
  onBrowseFile,
  onBrowseDir,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('doc');

  const FORMATS: { id: OutputFormat; label: string }[] = [
    { id: 'pdf', label: 'PDF' },
    { id: 'docx', label: 'DOCX (Word)' },
    { id: 'wrap-rtl', label: 'RTL Markdown' },
  ];

  return (
    <div className="flex flex-col h-full min-w-[300px] bg-card border-l border-main transition-colors duration-200">
      {/* Top Controls: Format & Output Directory */}
      <div className="p-4 border-b border-main space-y-3 bg-surface transition-colors">
        <div>
          <label className="block text-xs font-semibold text-main mb-2">فرمت خروجی</label>
          <div className="grid grid-cols-3 gap-1.5 p-1 bg-subtle rounded-lg border border-main">
            {FORMATS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => {
                  onOptionsChange('format', f.id);
                  if (f.id === 'docx') setActiveTab('docx');
                }}
                aria-pressed={options.format === f.id}
                className={`btn py-1.5 px-2 rounded-md text-xs font-medium ${
                  options.format === f.id
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-muted hover:text-main hover:bg-hover'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5 gap-2">
            <label className="text-xs font-semibold text-main whitespace-nowrap">پوشه خروجی</label>
            <span className="text-[11px] text-muted truncate">پیش‌فرض: کنار فایل اصلی</span>
          </div>
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={options.outputDir}
              onChange={(e) => onOptionsChange('outputDir', e.target.value)}
              placeholder="پوشه خروجی (اختیاری)"
              aria-label="پوشه خروجی"
              className="flex-1 min-w-0 px-3 py-1.5 rounded-md bg-input border border-input text-xs text-main font-mono placeholder:text-dim focus:border-blue-500 focus:outline-none transition-colors duration-150"
              dir="ltr"
            />
            <Tooltip label="انتخاب پوشه خروجی با دیالوگ ویندوز">
              <button
                type="button"
                onClick={onBrowseOutputDir}
                disabled={outputDirBusy}
                aria-label="انتخاب پوشه خروجی"
                className="btn p-1.5 rounded-md bg-subtle hover:bg-hover border border-main text-main shrink-0"
              >
                {outputDirBusy ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
                ) : (
                  <FolderOpen className="w-3.5 h-3.5 text-blue-500" />
                )}
              </button>
            </Tooltip>
            <Tooltip label="باز کردن پوشه خروجی در ویندوز اکسپلورر">
              <button
                type="button"
                onClick={onOpenOutputDir}
                aria-label="باز کردن پوشه خروجی در اکسپلورر"
                className="btn p-1.5 rounded-md bg-subtle hover:bg-hover border border-main text-main shrink-0"
              >
                <ExternalLink className="w-3.5 h-3.5 text-amber-500" />
              </button>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div
        className="flex border-b border-main bg-surface px-2 overflow-x-auto transition-colors"
        role="tablist"
        aria-label="پارامترهای تبدیل"
      >
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          const isDisabled =
            options.format === 'wrap-rtl' &&
            (tab.id === 'doc' || tab.id === 'docx' || tab.id === 'mermaid');
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab.id)}
              disabled={isDisabled}
              title={isDisabled ? 'این برگه در حالت RTL Markdown کاربرد ندارد' : tab.label}
              className={`btn relative shrink-0 px-3 py-2.5 text-xs font-medium border-b-2 whitespace-nowrap ${
                isActive
                  ? 'border-blue-500 text-blue-700 dark:text-blue-400 bg-blue-500/5'
                  : 'border-transparent text-muted hover:text-main'
              } ${isDisabled ? 'opacity-30 cursor-not-allowed' : ''}`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Body */}
      <div className="flex-1 overflow-y-auto p-4 bg-card">
        {activeTab === 'doc' && <TabDocument options={options} onChange={onOptionsChange} />}
        {activeTab === 'style' && (
          <TabStyling
            options={options}
            onChange={onOptionsChange}
            onBrowseFile={onBrowseFile}
            onBrowseDir={onBrowseDir}
          />
        )}
        {activeTab === 'mermaid' && (
          <TabMermaid
            options={options}
            onChange={onOptionsChange}
            onBrowseFile={onBrowseFile}
            onBrowseDir={onBrowseDir}
          />
        )}
        {activeTab === 'docx' && <TabDocx options={options} onChange={onOptionsChange} />}
        {activeTab === 'advanced' && <TabAdvanced options={options} onChange={onOptionsChange} />}
      </div>

      {/* Bottom Actions Bar */}
      <div className="p-3 border-t border-main bg-surface space-y-2 transition-colors">
        <label className="flex items-center gap-2 px-1 cursor-pointer text-xs text-main select-none">
          <input
            type="checkbox"
            checked={options.watch}
            aria-describedby={options.watch ? 'watch-mode-hint' : undefined}
            onChange={(e) => onOptionsChange('watch', e.target.checked)}
            className="rounded border-input bg-input text-blue-600 shrink-0"
          />
          <Eye className="w-3.5 h-3.5 text-blue-500 shrink-0" />
          <span className="whitespace-nowrap">حالت پایش زنده (Watch Mode)</span>
        </label>
        {options.watch && <p id="watch-mode-hint" className="text-[11px] text-muted px-1 leading-5">پس از تبدیل، منتظر تغییر فایل می‌ماند؛ برای پایان، توقف را بزنید.</p>}

        <div className="flex gap-2">
          <button
            onClick={onConvert}
            disabled={isRunning || !hasDocuments}
            className="btn flex-1 py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs shadow-lg shadow-blue-600/20"
            title="اجرای تبدیل روی همهٔ اسناد صف"
          >
            {isWatching ? <><Eye className="w-4 h-4" /><span>پایش زنده فعال</span></> : isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>درحال تبدیل…</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>شروع تبدیل اسناد</span>
              </>
            )}
          </button>

          <Tooltip label="توقف فرآیند تبدیل">
            <button
              onClick={onCancel}
              disabled={!isRunning}
              aria-label="توقف تبدیل"
              className="btn py-2 px-3 rounded-lg bg-subtle hover:bg-rose-500/15 text-muted hover:text-rose-600 dark:hover:text-rose-400 text-xs"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>لغو</span>
            </button>
          </Tooltip>
        </div>
      </div>
    </div>
  );
};
