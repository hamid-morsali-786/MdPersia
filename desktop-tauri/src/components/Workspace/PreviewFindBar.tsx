import type { RefObject } from 'react';
import { ChevronDown, ChevronUp, Search, X } from 'lucide-react';

export function PreviewFindBar({ input, query, onQuery, count, capped, index, searching, onMove, onClose, fullscreen }: {
  input: RefObject<HTMLInputElement | null>;
  query: string;
  onQuery: (value: string) => void;
  count: number;
  capped: boolean;
  index: number;
  searching: boolean;
  onMove: (direction: number) => void;
  onClose: () => void;
  fullscreen: boolean;
}) {
  const button = 'btn h-8 w-8 shrink-0 justify-center rounded text-muted hover:bg-subtle hover:text-main';
  return (
    <div role="search" aria-label="جست‌وجو در متن سند"
      className={`flex items-center gap-1 px-2 py-1.5 bg-surface border-main shrink-0 ${fullscreen ? 'self-start mr-4 my-2 w-[min(28rem,calc(100%-5rem))] rounded-md border' : 'border-b'}`}>
      <Search className="w-4 h-4 text-muted shrink-0" />
      <input ref={input} type="text" aria-label="جست‌وجو در متن سند" placeholder="جست‌وجو در متن سند"
        className="min-w-0 flex-1 h-8 px-2 rounded border border-input bg-input text-main text-sm" dir="auto"
        value={query} maxLength={1024} onChange={event => onQuery(event.target.value)}
        onKeyDown={event => {
          if (event.key === 'Enter' && !event.nativeEvent.isComposing) {
            event.preventDefault(); onMove(event.shiftKey ? -1 : 1);
          }
        }} />
      <span role="status" className="shrink-0 text-xs text-muted whitespace-nowrap" dir={count ? 'ltr' : 'rtl'}>
        {searching ? 'در حال جست‌وجو…' : count ? `${index + 1} / ${count}${capped ? '+' : ''}` : query.trim() ? 'بدون نتیجه' : ''}
      </span>
      <button type="button" aria-label="نتیجهٔ قبلی" title="نتیجهٔ قبلی (Shift+F3)" disabled={!count} className={button} onClick={() => onMove(-1)}><ChevronUp className="w-4 h-4" /></button>
      <button type="button" aria-label="نتیجهٔ بعدی" title="نتیجهٔ بعدی (F3)" disabled={!count} className={button} onClick={() => onMove(1)}><ChevronDown className="w-4 h-4" /></button>
      <button type="button" aria-label="بستن جست‌وجو" title="بستن جست‌وجو (Esc)" className={button} onClick={onClose}><X className="w-4 h-4" /></button>
    </div>
  );
}
