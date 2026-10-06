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

interface InspectorPanelProps {
  options: ConvertOptions;
  isRunning: boolean;
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
    <div className="flex flex-col h-full bg-card border-l border-main transition-colors duration-200">
      {/* Top Controls: Format & Output Directory */}
      <div className="p-4 border-b border-main space-y-3 bg-surface transition-colors">
        <div>
          <label className="block text-xs font-semibold text-main mb-1.5">فرمت خروجی</label>
          <div className="grid grid-cols-3 gap-1.5 p-1 bg-subtle rounded-lg border border-main">
            {FORMATS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => {
                  onOptionsChange('format', f.id);
                  if (f.id === 'docx') setActiveTab('docx');
                }}
                className={`py-1.5 px-2 rounded-md text-xs font-medium transition-all cursor-pointer ${
                  options.format === f.id
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-muted hover:text-main'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-semibold text-main">پوشه خروجی</label>
            <span className="text-[11px] text-muted font-normal">پیش‌فرض: کنار فایل اصلی</span>
          </div>
          <div className="flex gap-1.5">
            <input
              type="text"
              value={options.outputDir}
              onChange={(e) => onOptionsChange('outputDir', e.target.value)}
              placeholder="پیش‌فرض: کنار فایل اصلی"
              className="flex-1 px-3 py-1.5 rounded-md bg-input border border-input text-xs text-main font-mono placeholder:text-dim focus:border-blue-500 focus:outline-none"
              dir="ltr"
            />
            <button
              type="button"
              onClick={onBrowseOutputDir}
              className="px-2.5 py-1.5 rounded-md bg-subtle hover:bg-hover border border-main text-main text-xs flex items-center gap-1 transition-colors cursor-pointer shrink-0"
              title="انتخاب پوشه خروجی"
            >
              <FolderOpen className="w-3.5 h-3.5 text-blue-500" />
              <span>انتخاب...</span>
            </button>
            <button
              type="button"
              onClick={onOpenOutputDir}
              className="px-2.5 py-1.5 rounded-md bg-subtle hover:bg-hover border border-main text-main text-xs flex items-center gap-1 transition-colors cursor-pointer shrink-0"
              title="باز کردن پوشه خروجی در ویندوز اکسپلورر"
            >
              <ExternalLink className="w-3.5 h-3.5 text-amber-500" />
              <span>نمایش در ویندوز</span>
            </button>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-main bg-surface px-2 overflow-x-auto transition-colors">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          const isDisabled = options.format === 'wrap-rtl' && (tab.id === 'doc' || tab.id === 'docx' || tab.id === 'mermaid');
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              disabled={isDisabled}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-500/5'
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
        <div className="flex items-center justify-between px-1">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-main select-none">
            <input
              type="checkbox"
              checked={options.watch}
              onChange={(e) => onOptionsChange('watch', e.target.checked)}
              className="rounded border-input bg-input text-blue-600 focus:ring-0"
            />
            <Eye className="w-3.5 h-3.5 text-blue-500" />
            <span>حالت پایش زنده (Watch Mode)</span>
          </label>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onConvert}
            disabled={isRunning}
            className="flex-1 py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900/60 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>درحال تبدیل...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>شروع تبدیل اسناد</span>
              </>
            )}
          </button>

          <button
            onClick={onCancel}
            disabled={!isRunning}
            className="py-2 px-3 rounded-lg bg-subtle hover:bg-rose-500/15 text-muted hover:text-rose-600 dark:hover:text-rose-400 disabled:opacity-40 disabled:cursor-not-allowed text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            title="توقف فرآیند تبدیل"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>لغو</span>
          </button>
        </div>
      </div>
    </div>
  );
};
