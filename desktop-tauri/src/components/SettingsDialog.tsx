import { useId, type ReactNode } from 'react';
import { BookOpen, Check, Monitor, Moon, RotateCcw, SlidersHorizontal, Sun } from 'lucide-react';
import type { AppSettings } from '../services/appSettings';
import type { OutputFormat } from '../types';
import { AppDialog } from './AppDialog';
import { ConversionRuntimePanel } from './ConversionRuntimePanel';
import type { ConversionRuntime } from '../services/useConversionRuntime';

function Toggle({ title, description, checked, onChange, disabled = false }: {
  title: string; description: string; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean;
}) {
  const descriptionId = useId();
  return <label className={`settings-toggle ${disabled ? 'opacity-50' : ''}`}>
    <span><span className="block text-sm font-medium">{title}</span><span id={descriptionId} className="block text-xs text-muted leading-6 mt-0.5">{description}</span></span>
    <input type="checkbox" role="switch" aria-label={title} checked={checked} disabled={disabled} aria-describedby={descriptionId} onChange={event => onChange(event.target.checked)} className="settings-switch" />
  </label>;
}

function Section({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return <section className="settings-section">
    <h3 className="flex items-center gap-2 text-sm font-bold mb-3">{icon}{title}</h3>
    {children}
  </section>;
}

export default function SettingsDialog({ settings, format, isRunning, storageError, notice, onChange, onFormatChange, onReset, onResetLayout, onClose, conversionRuntime }: {
  settings: AppSettings; format: OutputFormat; isRunning: boolean; storageError: boolean; notice: string;
  onChange: (patch: Partial<AppSettings>) => void; onFormatChange: (format: OutputFormat) => void;
  onReset: () => void; onResetLayout: () => void; onClose: () => void;
  conversionRuntime?: ConversionRuntime;
}) {
  const radioGroup = useId();
  return <AppDialog title="تنظیمات برنامه" description="انتخاب‌ها بلافاصله اعمال می‌شوند و فقط روی همین دستگاه ذخیره می‌شوند." onClose={onClose}
    footer={<>
      <span role="status" className={`flex items-center gap-1.5 text-xs ${storageError ? 'text-rose-600 dark:text-rose-400' : 'text-muted'}`}>
        {!storageError && <Check className="w-3.5 h-3.5" />}
        {storageError ? 'ذخیره ممکن نشد؛ تغییرها تا پایان این اجرا فعال‌اند.' : notice || 'ذخیرهٔ خودکار تنظیمات فعال است'}
      </span>
      <button type="button" onClick={onClose} className="btn rounded-md bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 text-sm">تمام</button>
    </>}>
    <Section title="ظاهر و مطالعه" icon={<BookOpen className="w-4 h-4 text-muted" />}>
      <fieldset className="mb-5">
        <legend className="text-xs text-muted mb-2">پوستهٔ برنامه</legend>
        <div className="settings-choices">
          {([{ value: 'light', label: 'روشن', icon: Sun }, { value: 'dark', label: 'تاریک', icon: Moon }, { value: 'system', label: 'همگام با سیستم', icon: Monitor }] as const).map(choice => <label className="settings-choice" key={choice.value}>
            <input type="radio" name={`${radioGroup}-theme`} value={choice.value} checked={settings.theme === choice.value} onChange={() => onChange({ theme: choice.value })} />
            <choice.icon className="w-4 h-4" /><span>{choice.label}</span>
          </label>)}
        </div>
      </fieldset>
      <div className="grid gap-5 sm:grid-cols-2 mb-5">
        <label className="text-sm">
          <span className="flex justify-between gap-2 mb-3"><span>بزرگ‌نمایی مطالعه</span><output className="font-mono text-xs text-muted" dir="ltr">{settings.previewZoom}%</output></span>
          <input aria-label="بزرگ‌نمایی مطالعه" type="range" min="60" max="200" step="10" value={settings.previewZoom} onChange={event => onChange({ previewZoom: Number(event.target.value) })} className="w-full accent-blue-600" dir="ltr" />
        </label>
        <label className="text-sm">
          <span className="flex justify-between gap-2 mb-3"><span>فاصلهٔ خطوط</span><output className="font-mono text-xs text-muted" dir="ltr">{settings.lineHeight.toFixed(1)}</output></span>
          <input aria-label="فاصلهٔ خطوط" type="range" min="1.4" max="2.4" step="0.1" value={settings.lineHeight} onChange={event => onChange({ lineHeight: Number(event.target.value) })} className="w-full accent-blue-600" dir="ltr" />
        </label>
      </div>
      <fieldset className="mb-2">
        <legend className="text-xs text-muted mb-2">عرض متن در پیش‌نمایش</legend>
        <div className="settings-choices">
          {([{ value: 'page', label: 'ستون خوانا' }, { value: 'wide', label: 'تمام عرض' }] as const).map(choice => <label key={choice.value} className="settings-choice">
            <input type="radio" name={`${radioGroup}-width`} checked={settings.readingWidth === choice.value} onChange={() => onChange({ readingWidth: choice.value })} />{choice.label}
          </label>)}
        </div>
      </fieldset>
      <Toggle title="شکستن خطوط طولانی کد" description="برای خواندن کدها بدون اسکرول افقی؛ متن اصلی فایل تغییری نمی‌کند." checked={settings.wrapCode} onChange={wrapCode => onChange({ wrapCode })} />
      <Toggle title="حفظ محل مطالعهٔ هر سند" description="هنگام جابه‌جایی بین اسناد همین صف، به محل قبلی مطالعه برگردید." checked={settings.rememberScroll} onChange={rememberScroll => onChange({ rememberScroll })} />
      <p className="text-xs text-muted leading-6 mt-3">این گزینه‌ها فقط پیش‌نمایش را تغییر می‌دهند؛ قالب خروجی PDF و Word از پنل تبدیل تنظیم می‌شود.</p>
    </Section>
    <Section title="رفتار برنامه" icon={<SlidersHorizontal className="w-4 h-4 text-muted" />}>
      <Toggle title="نمایش خودکار فایل تازه" description="پس از افزودن فایل، آن را نمایش بده؛ با خاموش‌کردن، مطالعهٔ سند فعلی ادامه می‌یابد." checked={settings.focusNewFiles} onChange={focusNewFiles => onChange({ focusNewFiles })} />
      <Toggle title="نمایش کنسول هنگام تبدیل" description="با شروع تبدیل به گزارش‌ها برو؛ با خاموش‌کردن، پیش‌نمایش باز می‌ماند." checked={settings.showConversionLogs} onChange={showConversionLogs => onChange({ showConversionLogs })} />
      <Toggle title="تأیید پیش از پاک‌کردن صف" description="پیش از حذف همهٔ ردیف‌ها سؤال شود. فایل‌های روی دیسک حذف نمی‌شوند." checked={settings.confirmClearQueue} onChange={confirmClearQueue => onChange({ confirmClearQueue })} />
    </Section>
    <Section title="تبدیل" icon={<SlidersHorizontal className="w-4 h-4 text-muted" />}>
      <Toggle title="به خاطر سپردن تنظیمات تبدیل" description="فرمت، پوشهٔ خروجی و انتخاب‌های پنل تبدیل برای اجرای بعد حفظ شوند. حالت Watch هنگام شروع خاموش است." checked={settings.rememberConversionOptions} disabled={isRunning} onChange={rememberConversionOptions => onChange({ rememberConversionOptions })} />
      <fieldset disabled={isRunning} className="mt-4 disabled:opacity-50">
        <legend className="text-xs text-muted mb-2">فرمت خروجی</legend>
        <div className="settings-choices">
          {([{ value: 'pdf', label: 'PDF' }, { value: 'docx', label: 'Word' }, { value: 'wrap-rtl', label: 'RTL Markdown' }] as const).map(choice => <label key={choice.value} className="settings-choice">
            <input type="radio" name={`${radioGroup}-format`} checked={format === choice.value} onChange={() => onFormatChange(choice.value)} />{choice.label}
          </label>)}
        </div>
      </fieldset>
      {isRunning && <p className="text-xs text-muted mt-3">تنظیمات تبدیل پس از پایان عملیات قابل تغییر است.</p>}
    </Section>
    {conversionRuntime?.native && <ConversionRuntimePanel runtime={conversionRuntime} isRunning={isRunning} />}
    <section className="settings-section">
      <h3 className="text-sm font-bold mb-3">میان‌برهای کاربردی</h3>
      <dl className="grid gap-2 text-xs text-muted">
        {[[ 'Ctrl + O', 'بازکردن فایل' ], [ 'Ctrl + S', 'ذخیرهٔ ویرایش' ], [ 'Ctrl + Shift + S', 'ذخیره با نام دیگر' ], [ 'Ctrl + Z / Ctrl + Y', 'واگرد / انجام دوباره' ], [ 'Ctrl + F', 'جستجو در ویرایشگر' ], [ 'Ctrl + R / F5', 'تازه‌کردن سند' ], [ 'Delete', 'حذف انتخاب از صف' ], [ 'Ctrl + ,', 'تنظیمات برنامه' ], [ 'Esc', 'بستن تنظیمات' ]].map(([keys, label]) => <div key={keys} className="flex items-center justify-between gap-3"><dt>{label}</dt><dd><kbd dir="ltr" className="font-mono bg-subtle px-2 py-1 rounded">{keys}</kbd></dd></div>)}
      </dl>
    </section>
    <div className="flex flex-wrap gap-2">
      <button type="button" onClick={onResetLayout} className="btn px-3 py-2 rounded-md border border-subtle hover:bg-subtle text-xs"><RotateCcw className="w-3.5 h-3.5" />بازنشانی عرض پنل‌ها</button>
      <button type="button" onClick={onReset} disabled={isRunning} className="btn px-3 py-2 rounded-md border border-subtle hover:bg-subtle text-xs">بازگردانی تنظیمات پیش‌فرض</button>
    </div>
    <p className="text-xs text-muted leading-6 mt-2">بازگردانی تنظیمات، صف و فایل‌های شما را حفظ می‌کند.</p>
  </AppDialog>;
}
