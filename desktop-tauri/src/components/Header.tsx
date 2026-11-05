import React from 'react';
import { Sparkles, Sun, Moon, Loader2, Settings } from 'lucide-react';
import { Tooltip } from './Tooltip';

interface HeaderProps {
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onOpenSettings: () => void;
  settingsOpen?: boolean;
  onOpenHelp?: () => void;
  isBusy?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ theme, onToggleTheme, onOpenSettings, settingsOpen, onOpenHelp, isBusy }) => {
  return (
    <header className="h-12 bg-surface border-b border-main flex items-center justify-between px-4 select-none shrink-0 gap-3 transition-colors duration-200">
      {/* Brand */}
      <div className="flex items-center gap-3 min-w-0">
        <img src="/mdpersia.svg" alt="" className="w-7 h-7 shrink-0" />
        <div className="flex items-baseline gap-2 min-w-0">
          <h1 className="text-sm font-bold text-main font-mono tracking-tight whitespace-nowrap">
            MdPersia
          </h1>
          <span className="text-[11px] text-muted font-medium hidden sm:inline truncate">
            تبدیل تخصصی مارک‌داون فارسی به PDF و Word
          </span>
        </div>
      </div>

      {/* Window controls cluster — secondary to the primary actions in the inspector */}
      <div className="flex items-center gap-1 shrink-0">
        {isBusy && (
          <span className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-subtle text-[11px] text-muted">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
            <span className="whitespace-nowrap">در حال پردازش…</span>
          </span>
        )}

        <div className="w-px h-5 bg-subtle mx-1" aria-hidden="true" />

        <Tooltip label="تنظیمات برنامه (Ctrl+,)">
          <button onClick={onOpenSettings} className="btn p-1.5 rounded-md hover:bg-subtle text-muted hover:text-main"
            aria-label="تنظیمات برنامه" aria-haspopup="dialog" aria-expanded={settingsOpen}>
            <Settings className="w-4 h-4" />
          </button>
        </Tooltip>

        <Tooltip label={theme === 'dark' ? 'تغییر به حالت روشن' : 'تغییر به حالت تاریک'}>
          <button
            onClick={onToggleTheme}
            className="btn p-1.5 rounded-md hover:bg-subtle text-muted hover:text-main"
            aria-label="تغییر تم"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-blue-600" />
            )}
          </button>
        </Tooltip>

        {onOpenHelp && (
          <Tooltip label="راهنما و اطلاعات نسخه">
            <button
              onClick={onOpenHelp}
              className="btn p-1.5 rounded-md hover:bg-subtle text-muted hover:text-main"
              aria-label="راهنما"
            >
              <Sparkles className="w-4 h-4" />
            </button>
          </Tooltip>
        )}
      </div>
    </header>
  );
};
