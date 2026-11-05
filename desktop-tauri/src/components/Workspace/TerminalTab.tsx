import React, { memo, useEffect, useMemo, useRef, useState } from 'react';
import type { LogEntry } from '../../types';
import { ArrowDown, Check, CheckCircle2, CircleAlert, Code2, Copy, Download, Eye, FileText, FolderOpen, Info, ListFilter, Loader2, Search, SearchX, Square, Terminal, Trash2, TriangleAlert, X } from 'lucide-react';
import { Tooltip } from '../Tooltip';
import { cleanLogText, filterReportLogs, formatLogReport, reportCounts, type LogFilter } from '../../services/consoleReport';

interface TerminalTabProps {
  logs: LogEntry[];
  isRunning: boolean;
  isWatching: boolean;
  isActive: boolean;
  onClearLogs: () => void;
  onOpenOutputDir?: () => void;
  onStop: () => Promise<void>;
}

const LEVELS = {
  info: { label: 'رویداد', icon: Info },
  success: { label: 'موفق', icon: CheckCircle2 },
  warn: { label: 'هشدار', icon: TriangleAlert },
  error: { label: 'خطا', icon: CircleAlert },
  summary: { label: 'نتیجه', icon: ListFilter },
};
const FILTERS: { value: LogFilter; label: string }[] = [
  { value: 'all', label: 'همه' }, { value: 'error', label: 'خطاها' },
  { value: 'warn', label: 'هشدارها' }, { value: 'success', label: 'موفق‌ها' },
];

const ReportRow = memo(function ReportRow({ entry }: { entry: LogEntry }) {
  const { label, icon: Icon } = LEVELS[entry.level];
  const message = cleanLogText(entry.message);
  return <li className={`report-row report-${entry.level}${entry.kind === 'batch-start' || entry.kind === 'batch-end' ? ' report-boundary' : ''}`} data-log-id={entry.id}>
    <span className="report-marker" aria-hidden="true"><Icon size={15} /></span>
    <div className="report-event">
      <div className="report-meta">
        <span className="report-level">{label}</span>
        {entry.fileName && <Tooltip label={entry.filePath ?? entry.fileName}><span className="report-file"><FileText size={11} aria-hidden="true" /><bdi>{entry.fileName}</bdi></span></Tooltip>}
        <span className="report-time" dir="auto">{entry.timestamp}</span>
      </div>
      {entry.kind === 'command' ? <details className="report-command">
        <summary><Code2 size={14} aria-hidden="true" />فرمان اجرا<span className="text-dim">جزئیات فنی</span></summary>
        <pre dir="ltr">{message}</pre>
      </details> : <p className="report-message" dir="auto">{message}</p>}
    </div>
  </li>;
});

export const TerminalTab: React.FC<TerminalTabProps> = ({ logs, isRunning, isWatching, isActive, onClearLogs, onOpenOutputDir, onStop }) => {
  const scroll = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<LogFilter>('all');
  const [query, setQuery] = useState('');
  const [following, setFollowing] = useState(true);
  const [copyState, setCopyState] = useState<'idle' | 'pending' | 'copied' | 'failed'>('idle');
  const [stopping, setStopping] = useState(false);
  const counts = useMemo(() => reportCounts(logs), [logs]);
  const visible = useMemo(() => filterReportLogs(logs, filter, query), [logs, filter, query]);
  const lastId = logs.at(-1)?.id;

  useEffect(() => {
    if (following && isActive && scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [lastId, following, isActive]);
  useEffect(() => {
    if (copyState !== 'copied' && copyState !== 'failed') return;
    const timer = window.setTimeout(() => setCopyState('idle'), 3000);
    return () => window.clearTimeout(timer);
  }, [copyState]);
  useEffect(() => { setCopyState('idle'); }, [filter, query]);

  const resetFilters = () => { setFilter('all'); setQuery(''); };
  const copy = async () => {
    setCopyState('pending');
    try { await navigator.clipboard.writeText(formatLogReport(visible)); setCopyState('copied'); }
    catch { setCopyState('failed'); }
  };
  const download = () => {
    const url = URL.createObjectURL(new Blob(['\ufeff', formatLogReport(visible)], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url;
    link.download = `MdPersia-report-${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
    link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  const status = isWatching ? 'در انتظار تغییر فایل' : isRunning ? 'در حال تبدیل' : 'آماده';
  const StatusIcon = isWatching ? Eye : isRunning ? Loader2 : Terminal;

  return <section className="console-report" aria-label="گزارش فعالیت" dir="rtl">
    <header className="report-header">
      <div className="report-heading">
        <span className="report-app-icon"><Terminal size={20} aria-hidden="true" /></span>
        <div><h2>گزارش فعالیت</h2><p>رویدادهای برنامه و نتیجهٔ تبدیل اسناد</p></div>
      </div>
      <span className={`report-status${isRunning ? ' report-status-active' : ''}`} role="status"><StatusIcon size={14} className={isRunning && !isWatching ? 'animate-spin' : ''} aria-hidden="true" />{status}</span>
      <div className="report-actions">
        {onOpenOutputDir && <Tooltip label="باز کردن پوشهٔ خروجی"><button type="button" className="btn report-action" onClick={onOpenOutputDir} aria-label="باز کردن پوشه خروجی"><FolderOpen size={15} /><span>خروجی</span></button></Tooltip>}
        <Tooltip label="کپی رویدادهای مطابق جستجو و فیلتر فعلی"><button type="button" className="btn report-action" onClick={() => void copy()} disabled={!visible.length || copyState === 'pending'} aria-label="کپی گزارش‌های نمایش‌داده‌شده">{copyState === 'pending' ? <Loader2 size={15} className="animate-spin" /> : copyState === 'copied' ? <Check size={15} /> : <Copy size={15} />}<span>کپی</span></button></Tooltip>
        <Tooltip label="ذخیرهٔ رویدادهای نمایش‌داده‌شده در فایل متنی"><button type="button" className="btn report-action" onClick={download} disabled={!visible.length} aria-label="ذخیره گزارش"><Download size={15} /><span>ذخیره</span></button></Tooltip>
        <Tooltip label="پاک کردن گزارش‌ها؛ تبدیل و فایل‌ها حفظ می‌شوند"><button type="button" className="btn report-action report-destructive" onClick={() => { onClearLogs(); resetFilters(); setFollowing(true); setCopyState('idle'); }} disabled={!logs.length} aria-label="پاکسازی کنسول"><Trash2 size={15} /><span>پاکسازی</span></button></Tooltip>
      </div>
    </header>

    {isRunning && <div className="report-process-note">
      <div><strong>{isWatching ? 'پایش زنده فعال است' : 'موتور تبدیل در حال اجراست'}</strong><p>{isWatching ? 'مرحلهٔ تبدیل پایان یافته است. با ذخیرهٔ فایل، تبدیل دوباره اجرا می‌شود؛ برای پایان، پایش را متوقف کنید.' : 'خروجی موتور در همین گزارش ثبت می‌شود. تا دریافت نتیجهٔ نهایی، تبدیل ادامه دارد.'}</p></div>
      <button type="button" className="btn report-action" disabled={stopping} onClick={async () => { setStopping(true); try { await onStop(); } finally { setStopping(false); } }}><Square size={13} />{stopping ? 'در حال توقف…' : isWatching ? 'توقف پایش' : 'توقف تبدیل'}</button>
    </div>}

    <div className="report-tools">
      <div className="report-filters" role="group" aria-label="فیلتر گزارش‌ها">
        {FILTERS.map(choice => <button key={choice.value} type="button" className={`btn report-filter${filter === choice.value ? ' is-selected' : ''}`} aria-pressed={filter === choice.value} onClick={() => { setFilter(choice.value); setFollowing(false); if (scroll.current) scroll.current.scrollTop = 0; }}>{choice.label}<span>{counts[choice.value]}</span></button>)}
      </div>
      <div className="report-search"><Search size={15} aria-hidden="true" /><input type="search" value={query} onChange={event => { setQuery(event.target.value); setFollowing(false); if (scroll.current) scroll.current.scrollTop = 0; }} placeholder="جستجو در پیام یا نام فایل…" aria-label="جستجو در گزارش‌ها" />{query && <button type="button" className="btn" aria-label="پاک کردن جستجوی گزارش‌ها" onClick={() => setQuery('')}><X size={14} /></button>}</div>
    </div>

    <div ref={scroll} className="report-scroll" tabIndex={0} aria-label="رویدادهای گزارش" onScroll={event => {
      const element = event.currentTarget;
      // Hidden panels and content shorter than the viewport are not deliberate scrolling.
      if (element.clientHeight && element.scrollHeight > element.clientHeight + 32) setFollowing(element.scrollHeight - element.clientHeight - element.scrollTop < 32);
    }}>
      {visible.length ? <ol className="report-list">{visible.map(entry => <ReportRow key={entry.id} entry={entry} />)}</ol> : <div className="report-empty">
        {logs.length ? <SearchX size={30} aria-hidden="true" /> : <Terminal size={30} aria-hidden="true" />}
        <h3>{logs.length ? 'رویدادی با این فیلتر پیدا نشد' : isRunning ? 'در انتظار خروجی موتور' : 'هنوز گزارشی ثبت نشده است'}</h3>
        <p>{logs.length ? 'عبارت جستجو یا نوع رویداد را تغییر دهید.' : 'پس از اجرای تبدیل، روند کار و نتیجهٔ هر سند در این بخش نمایش داده می‌شود.'}</p>
        {logs.length > 0 && <button type="button" className="btn report-action" onClick={resetFilters}>نمایش همهٔ رویدادها</button>}
      </div>}
    </div>

    <footer className="report-footer">
      <div><span>{visible.length} از {logs.length} رویداد</span><span className="report-retention">۱۰۰۰ رویداد آخر نگه‌داری می‌شود</span></div>
      <button type="button" className={`btn report-follow${following ? ' is-selected' : ''}`} aria-pressed={following} onClick={() => setFollowing(value => !value)}><ArrowDown size={13} />{following ? 'دنبال‌کردن تازه‌ترین‌ها' : 'رفتن به تازه‌ترین‌ها'}</button>
    </footer>
    {copyState === 'copied' || copyState === 'failed' ? <p className={`report-feedback${copyState === 'failed' ? ' report-destructive' : ''}`} role="status">{copyState === 'copied' ? 'رویدادهای نمایش‌داده‌شده کپی شدند.' : 'کپی انجام نشد؛ می‌توانید گزارش را در فایل ذخیره کنید.'}</p> : null}
  </section>;
};
