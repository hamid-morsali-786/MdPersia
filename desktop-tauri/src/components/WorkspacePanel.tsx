import React, { useEffect, useLayoutEffect, useRef, type RefObject } from 'react';
import { QueueItem, LogEntry } from '../types';
import { PreviewTab } from './Workspace/PreviewTab';
import { TerminalTab } from './Workspace/TerminalTab';
import { Eye, Maximize, Minimize, Terminal, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import type { AppSettings } from '../services/appSettings';
import type { DocumentEditor } from '../services/useDocumentEditor';
import type { DocumentSnapshot } from '../services/documents';
import type { ReadingPosition } from '../services/readingSession';

interface WorkspacePanelProps {
  readingFullscreen: boolean;
  fullscreenError: string;
  onToggleFullscreen: () => void;
  previewFrame: RefObject<HTMLIFrameElement | null>;
  readingPositions: Map<string, ReadingPosition>;
  onReadingPositionChange: () => void;
  inspectorOpen: boolean;
  onToggleInspector: () => void;
  selectedItem: QueueItem | null;
  markdownContent?: string;
  logs: LogEntry[];
  isRunning: boolean;
  isWatching: boolean;
  onStopConversion: () => Promise<void>;
  theme?: 'dark' | 'light';
  activeTab: 'preview' | 'terminal';
  onTabChange: (tab: 'preview' | 'terminal') => void;
  zoom: number;
  onZoomChange: (zoom: number) => void;
  previewNonce: number;
  onRefreshPreview: () => void;
  onClearLogs: () => void;
  onOpenInEditor?: (path: string) => void;
  onOpenOutputDir?: () => void;
  onOpenDocument?: (path: string) => void;
  readingSettings: AppSettings;
  editor: DocumentEditor;
  onSavedCopy: (document: DocumentSnapshot) => void;
}

export const WorkspacePanel: React.FC<WorkspacePanelProps> = ({
  selectedItem,
  markdownContent,
  logs,
  isRunning,
  isWatching, onStopConversion,
  theme = 'dark',
  activeTab,
  onTabChange,
  zoom,
  onZoomChange,
  previewNonce,
  onRefreshPreview,
  onClearLogs,
  onOpenInEditor,
  onOpenOutputDir,
  onOpenDocument,
  readingSettings,
  editor, onSavedCopy,
  inspectorOpen, onToggleInspector, readingFullscreen, fullscreenError, onToggleFullscreen,
  previewFrame, readingPositions, onReadingPositionChange,
}) => {
  const fullscreenButton = useRef<HTMLButtonElement>(null);
  const wasFullscreen = useRef(false);
  useLayoutEffect(() => {
    if (wasFullscreen.current && !readingFullscreen) fullscreenButton.current?.focus({ preventScroll: true });
    wasFullscreen.current = readingFullscreen;
  }, [readingFullscreen]);
  // Surface live process output while a batch runs, then hand control back.
  useEffect(() => {
    if (isRunning && readingSettings.showConversionLogs) onTabChange('terminal');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning, readingSettings.showConversionLogs, onTabChange]);

  const tabClass = (active: boolean) =>
    `btn relative shrink-0 px-4 py-3 text-xs font-medium transition-colors duration-150 ${
      active ? 'text-blue-600 dark:text-blue-400' : 'text-muted hover:text-main'
    }`;

  const showingPreview = readingFullscreen || activeTab === 'preview';
  const fullscreenLabel = readingFullscreen ? 'خروج از مطالعهٔ تمام‌صفحه' : 'مطالعهٔ تمام‌صفحه';

  return (
    <div className="relative flex flex-col h-full bg-card transition-colors duration-200">
      <div className={readingFullscreen ? 'absolute top-3 left-5 z-20' : 'flex items-stretch justify-between gap-2 px-3 border-b border-main bg-surface transition-colors'}>
        <div hidden={readingFullscreen} className="flex min-w-0 overflow-x-auto" role="tablist" aria-label="نمای کاری">
          <button
            role="tab"
            aria-selected={activeTab === 'preview'}
            onClick={() => onTabChange('preview')}
            className={tabClass(activeTab === 'preview')}
          >
            <Eye className="w-4 h-4" />
            <span>پیش‌نمایش سند</span>
            {activeTab === 'preview' && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-blue-500" />
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'terminal'}
            onClick={() => onTabChange('terminal')}
            className={tabClass(activeTab === 'terminal')}
          >
            <Terminal className="w-4 h-4" />
            <span>کنسول و گزارش‌ها</span>
            {isRunning && (
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shrink-0" />
            )}
            {activeTab === 'terminal' && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-blue-500" />
            )}
          </button>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button hidden={readingFullscreen} type="button" className="btn px-2 h-8 shrink-0 rounded text-muted hover:bg-subtle hover:text-main"
            onClick={onToggleInspector} aria-expanded={inspectorOpen} aria-controls="output-inspector"
            aria-label={inspectorOpen ? 'پنهان‌کردن تنظیمات خروجی' : 'نمایش تنظیمات خروجی'}
            title={inspectorOpen ? 'پنهان‌کردن تنظیمات خروجی' : 'نمایش تنظیمات خروجی'}>
            {inspectorOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
          </button>
          {showingPreview && (selectedItem || readingFullscreen) && <button ref={fullscreenButton} type="button"
            className={`btn h-8 w-8 justify-center rounded text-muted hover:text-main ${readingFullscreen ? 'border border-main bg-surface hover:bg-hover' : 'hover:bg-subtle'}`}
            onClick={onToggleFullscreen} aria-label={fullscreenLabel} aria-pressed={readingFullscreen}
            title={readingFullscreen ? `${fullscreenLabel} (Esc)` : fullscreenLabel}>
            {readingFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
          </button>}
        </div>
      </div>
      {fullscreenError && <p role="alert" className="absolute top-12 left-3 z-20 max-w-[calc(100%-1.5rem)] bg-surface border border-main rounded px-3 py-2 text-sm text-main">{fullscreenError}</p>}

      <div className="flex-1 overflow-hidden">
        <div className={showingPreview ? 'hidden' : 'h-full'}>
          <TerminalTab logs={logs} isRunning={isRunning} isWatching={isWatching} isActive={!showingPreview} onStop={onStopConversion} onClearLogs={onClearLogs} onOpenOutputDir={onOpenOutputDir} />
        </div>
        <div className={showingPreview ? 'h-full' : 'hidden'}>
          <PreviewTab
            active={showingPreview}
            readingFullscreen={readingFullscreen}
            previewFrame={previewFrame}
            readingPositions={readingPositions}
            onReadingPositionChange={onReadingPositionChange}
            selectedItem={selectedItem}
            markdownContent={markdownContent}
            theme={theme}
            zoom={zoom}
            onZoomChange={onZoomChange}
            previewNonce={previewNonce}
            onRefresh={onRefreshPreview}
            onOpenInEditor={onOpenInEditor}
            onOpenDocument={onOpenDocument}
            readingSettings={readingSettings}
            editor={editor} isRunning={isRunning} onSavedCopy={onSavedCopy}
          />
        </div>
      </div>
    </div>
  );
};
