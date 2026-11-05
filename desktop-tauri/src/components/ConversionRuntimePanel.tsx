import { Check, Download, ExternalLink, FolderOpen, Loader2, Square, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { ConversionRuntime } from '../services/useConversionRuntime';
import { openExternalUrl } from '../services/tauriBridge';

export const runtimePhase = (phase: string) => ({ checking: 'در حال بررسی موتور', starting: 'آماده‌سازی دریافت',
  selecting: 'در انتظار انتخاب فایل', downloading: 'دریافت موتور تبدیل', copying: 'خواندن بسته از فایل',
  verifying: 'بررسی سلامت بسته', installing: 'نصب موتور تبدیل', cancelling: 'در حال توقف دریافت',
  removing: 'حذف موتور تبدیل' }[phase] || 'موتور تبدیل');
const size = (bytes: number) => `${(bytes / 1048576).toFixed(1)} MiB`;

export function ConversionRuntimePanel({ runtime, isRunning = false }: { runtime: ConversionRuntime; isRunning?: boolean }) {
  const { info, busy } = runtime;
  const [linkError, setLinkError] = useState('');
  useEffect(() => { if (info.installed) setLinkError(''); }, [info.installed]);
  const percent = info.totalBytes ? Math.min(100, Math.floor(info.downloadedBytes * 100 / info.totalBytes)) : 0;
  const button = 'btn rounded-md px-3 py-2 text-sm border border-subtle hover:bg-subtle disabled:opacity-50 disabled:cursor-not-allowed';
  return <section className="settings-section" aria-label="موتور تبدیل اختیاری">
    <h3 className="text-sm font-bold mb-2">موتور خروجی PDF و Word</h3>
    <p className="text-xs text-muted leading-6 mb-3">مطالعه، پیش‌نمایش، ویرایش و ذخیره بدون دریافت این بسته فعال‌اند. برای PDF و Word، موتور را یک‌بار دریافت کنید؛ پس از نصب، تبدیل هم آفلاین کار می‌کند.</p>
    {info.phase === 'checking' ? <p role="status" className="flex items-center gap-2 text-sm"><Loader2 className="w-4 h-4 animate-spin" />در حال بررسی موتور</p> : info.installed && !busy ? <>
      <p role="status" className="flex items-center gap-2 text-sm mb-3"><Check className="w-4 h-4" />موتور تبدیل آماده است</p>
      <button type="button" className={`${button} text-rose-600 dark:text-rose-300`} disabled={busy || isRunning}
        onClick={() => void runtime.remove()}><Trash2 className="w-4 h-4" />حذف موتور و آزادکردن فضا</button>
      <p className="text-xs text-muted leading-6 mt-2">حذف این بسته، فایل‌های شما و قابلیت ویرایش را حفظ می‌کند.</p>
    </> : busy ? <>
      <p role="status" aria-live="polite" className="flex items-center gap-2 text-sm mb-2">
        <Loader2 className="w-4 h-4 animate-spin" />{runtimePhase(info.phase)}
      </p>
      {['downloading', 'copying'].includes(info.phase) && <>
        <progress className="w-full h-2 accent-blue-600" max={Math.max(1, info.totalBytes)} value={info.downloadedBytes}
          aria-label="پیشرفت دریافت موتور تبدیل" />
        <p className="text-xs text-muted mt-2 mb-3" dir="ltr">{size(info.downloadedBytes)} / {size(info.totalBytes)} ({percent}%)</p>
      </>}
      {!['removing', 'selecting'].includes(info.phase) && <button type="button" className={button} onClick={() => void runtime.cancel()}
        disabled={info.phase === 'cancelling'}><Square className="w-3.5 h-3.5" />توقف دریافت</button>}
      <p className="text-xs text-muted leading-6 mt-2">می‌توانید به مطالعه ادامه دهید. بستن برنامه، دریافت جاری را متوقف می‌کند.</p>
    </> : <>
      <p className="text-xs text-muted leading-6 mb-3">حجم دریافت: <bdi dir="ltr">{info.totalBytes ? size(info.totalBytes) : '…'}</bdi>. سلامت و سازگاری فایل پیش از نصب بررسی می‌شود.</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={info.phase === 'checking' || !info.totalBytes || isRunning}
          onClick={() => void runtime.install()} className="btn rounded-md px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed">
          <Download className="w-4 h-4" />{info.phase === 'error' ? 'تلاش دوباره برای دریافت' : 'دریافت موتور تبدیل'}
        </button>
        <button type="button" className={button} disabled={info.phase === 'checking' || isRunning}
          onClick={() => void runtime.importFile()}><FolderOpen className="w-4 h-4" />نصب از فایل ZIP</button>
        {info.downloadUrl && <button type="button" className={button} onClick={() => {
          setLinkError(''); void openExternalUrl(info.downloadUrl).catch(() => setLinkError('بازکردن مرورگر انجام نشد؛ دوباره تلاش کنید یا دریافت درون برنامه را انتخاب کنید.'));
        }}>
          <ExternalLink className="w-4 h-4" />دریافت با مرورگر</button>}
      </div>
      {info.phase === 'cancelled' && <p role="status" className="text-xs text-muted mt-3">دریافت متوقف شد. هر زمان خواستید می‌توانید دوباره دریافت کنید.</p>}
    </>}
    {info.error && <p role="alert" className="text-sm text-rose-600 dark:text-rose-300 leading-6 mt-3">{info.error}</p>}
    {linkError && <p role="alert" className="text-sm text-rose-600 dark:text-rose-300 leading-6 mt-3">{linkError}</p>}
  </section>;
}
