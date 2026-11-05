import React from 'react';

interface StatusBarProps {
  statusMessage: string;
  progressPercent: number; // 0 - 100
  isRunning: boolean;
  isWatching: boolean;
  totalItems: number;
  completedItems: number;
  conversionReady?: boolean;
  onManageConversion?: () => void;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  statusMessage,
  progressPercent,
  isRunning,
  isWatching,
  totalItems,
  completedItems,
  conversionReady, onManageConversion,
}) => {
  return (
    <footer className="h-8 bg-surface border-t border-main flex items-center justify-between px-3 text-[11px] select-none shrink-0 text-muted transition-colors duration-200">
      {/* Left / Status Text & Progress */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`w-2 h-2 rounded-full ${
              isRunning ? `bg-blue-500 ${isWatching ? '' : 'animate-ping'}` : 'bg-emerald-500'
            }`}
          />
          <span className="text-main font-medium truncate" title={statusMessage}>{statusMessage}</span>
        </div>

        {isRunning && !isWatching && (
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
      <div className="hidden md:flex items-center gap-4 text-muted">
        {conversionReady !== undefined && <button type="button" onClick={onManageConversion}
          className="btn flex items-center gap-1.5 rounded hover:text-main" aria-label="مدیریت موتور تبدیل">
          <span className={`w-1.5 h-1.5 rounded-full ${conversionReady ? 'bg-emerald-500' : 'bg-subtle'}`} />
          <span>{conversionReady ? 'موتور تبدیل آماده' : 'موتور تبدیل اختیاری'}</span>
        </button>}
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>فونت وزیرمتن فعال</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>رندر آفلاین Mermaid</span>
        </div>
      </div>
    </footer>
  );
};
