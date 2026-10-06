import React from 'react';

interface StatusBarProps {
  statusMessage: string;
  progressPercent: number; // 0 - 100
  isRunning: boolean;
  totalItems: number;
  completedItems: number;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  statusMessage,
  progressPercent,
  isRunning,
  totalItems,
  completedItems,
}) => {
  return (
    <footer className="h-8 bg-surface border-t border-main flex items-center justify-between px-3 text-[11px] select-none shrink-0 text-muted transition-colors duration-200">
      {/* Left / Status Text & Progress */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isRunning ? 'bg-blue-500 animate-ping' : 'bg-emerald-500'
            }`}
          />
          <span className="text-main font-medium">{statusMessage}</span>
        </div>

        {isRunning && (
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 bg-subtle rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="font-mono text-main">{progressPercent}%</span>
            <span className="font-mono text-muted">
              ({completedItems}/{totalItems})
            </span>
          </div>
        )}
      </div>

      {/* Right / Offline Readiness Badges */}
      <div className="hidden md:flex items-center gap-4 text-dim">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>مرورگر کرومیوم آماده</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>فونت وزیرمتن فعال</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>رندرر آفلاین Mermaid</span>
        </div>
      </div>
    </footer>
  );
};
