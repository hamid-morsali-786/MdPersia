import React from 'react';
import { Sparkles, Sun, Moon, HelpCircle } from 'lucide-react';

interface HeaderProps {
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onOpenHelp?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  theme,
  onToggleTheme,
  onOpenHelp,
}) => {
  return (
    <header className="h-12 bg-surface border-b border-main flex items-center justify-between px-4 select-none shrink-0 transition-colors duration-200">
      {/* Brand & Title */}
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
          <Sparkles className="w-4 h-4" />
        </div>
        <div className="flex items-baseline gap-2">
          <h1 className="text-sm font-bold text-main font-mono tracking-tight">MdPersia</h1>
          <span className="text-[11px] text-muted font-medium hidden sm:inline">
            تبدیل تخصصی مارک‌داون فارسی به PDF و Word
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded-md hover:bg-subtle text-muted hover:text-main transition-colors cursor-pointer"
          title={theme === 'dark' ? 'حالت روشن' : 'حالت تاریک'}
          aria-label="تغییر تم"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-blue-600" />
          )}
        </button>

        {onOpenHelp && (
          <button
            onClick={onOpenHelp}
            className="p-1.5 rounded-md hover:bg-subtle text-muted hover:text-main transition-colors cursor-pointer"
            title="راهنما و اطلاعات"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        )}
      </div>
    </header>
  );
};
