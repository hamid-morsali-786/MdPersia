import React, { useState } from 'react';
import { QueueItem, LogEntry } from '../types';
import { PreviewTab } from './Workspace/PreviewTab';
import { TerminalTab } from './Workspace/TerminalTab';
import { Eye, Terminal } from 'lucide-react';

interface WorkspacePanelProps {
  selectedItem: QueueItem | null;
  markdownContent?: string;
  logs: LogEntry[];
  isRunning: boolean;
  onClearLogs: () => void;
  onOpenInEditor?: (path: string) => void;
  onOpenOutputDir?: () => void;
}

export const WorkspacePanel: React.FC<WorkspacePanelProps> = ({
  selectedItem,
  markdownContent,
  logs,
  isRunning,
  onClearLogs,
  onOpenInEditor,
  onOpenOutputDir,
}) => {
  const [activeTab, setActiveTab] = useState<'preview' | 'terminal'>('terminal');

  return (
    <div className="flex flex-col h-full bg-card transition-colors duration-200">
      {/* Workspace Tab Header */}
      <div className="flex items-center justify-between px-3 border-b border-main bg-surface transition-colors">
        <div className="flex">
          <button
            onClick={() => setActiveTab('terminal')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'terminal'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-500/5'
                : 'border-transparent text-muted hover:text-main'
            }`}
          >
            <Terminal className="w-4 h-4" />
            <span>کنسول و گزارش‌ها</span>
            {isRunning && <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />}
          </button>

          <button
            onClick={() => setActiveTab('preview')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'preview'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-500/5'
                : 'border-transparent text-muted hover:text-main'
            }`}
          >
            <Eye className="w-4 h-4" />
            <span>پیش‌نمایش سند</span>
          </button>
        </div>
      </div>

      {/* Main Content View */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'terminal' ? (
          <TerminalTab
            logs={logs}
            onClearLogs={onClearLogs}
            onOpenOutputDir={onOpenOutputDir}
          />
        ) : (
          <PreviewTab
            selectedItem={selectedItem}
            markdownContent={markdownContent}
            onOpenInEditor={onOpenInEditor}
          />
        )}
      </div>
    </div>
  );
};
