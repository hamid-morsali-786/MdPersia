import React, { useEffect, useRef, useState } from 'react';
import { LogEntry } from '../../types';
import { Copy, Trash2, FolderOpen, Check } from 'lucide-react';

interface TerminalTabProps {
  logs: LogEntry[];
  onClearLogs: () => void;
  onOpenOutputDir?: () => void;
}

export const TerminalTab: React.FC<TerminalTabProps> = ({
  logs,
  onClearLogs,
  onOpenOutputDir,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const handleCopy = () => {
    const text = logs.map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLogColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return 'text-emerald-400';
      case 'error':
        return 'text-rose-400';
      case 'warn':
        return 'text-amber-400';
      case 'summary':
        return 'text-indigo-400 font-semibold';
      default:
        return 'text-slate-300';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#090D16]">
      {/* Terminal Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-main bg-surface transition-colors">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-mono text-main">fa-md-pdf console</span>
          <span className="text-[11px] text-muted font-mono">({logs.length} خط)</span>
        </div>

        <div className="flex items-center gap-1.5">
          {onOpenOutputDir && (
            <button
              onClick={onOpenOutputDir}
              className="flex items-center gap-1 px-2 py-1 rounded bg-subtle hover:bg-hover text-main text-xs transition-colors cursor-pointer"
              title="باز کردن پوشه خروجی"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span>پوشه خروجی</span>
            </button>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 rounded bg-subtle hover:bg-hover text-main text-xs transition-colors cursor-pointer"
            title="کپی لاگ‌ها"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'کپی شد' : 'کپی'}</span>
          </button>

          <button
            onClick={onClearLogs}
            className="flex items-center gap-1 px-2 py-1 rounded bg-subtle hover:bg-hover text-main text-xs transition-colors cursor-pointer"
            title="پاکسازی کنسول"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>پاکسازی</span>
          </button>
        </div>
      </div>

      {/* Terminal Output */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-5 select-text text-left"
        dir="ltr"
      >
        {logs.length === 0 ? (
          <div className="text-slate-500 italic">No output yet. Run a conversion to view logs.</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2 items-start py-0.5 hover:bg-slate-900/50">
              <span className="text-slate-500 select-none shrink-0 font-mono text-[11px]">
                [{log.timestamp}]
              </span>
              <span className={`select-none shrink-0 font-bold uppercase text-[11px] w-14 ${getLogColor(log.level)}`}>
                [{log.level}]
              </span>
              <span className={`whitespace-pre-wrap break-all ${getLogColor(log.level)}`}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
