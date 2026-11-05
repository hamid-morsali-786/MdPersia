import React, { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { QueueItem } from '../../types';
import {
  ExternalLink,
  FileText,
  Eye,
  Code,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Loader2,
  AlertTriangle,
  Pencil, Save, Copy, Check, X,
} from 'lucide-react';
import { Tooltip } from '../Tooltip';
import { openExternalUrl, applyPreviewAppearance, loadPreviewDocument, loadDraftPreview, PreviewSource } from '../../services/tauriBridge';
import { linkedMarkdownPath } from '../../services/queueState';
import type { ReadingSettings } from '../../services/appSettings';
import { draftIsDirty, type DocumentEditor, type EditorDraft } from '../../services/useDocumentEditor';
import { documentKey } from '../../services/queueState';
import { DocumentFailure, pickSaveMarkdown, readDocument, type DocumentSnapshot } from '../../services/documents';
import { AppDialog } from '../AppDialog';

const MarkdownEditor = lazy(() => import('./MarkdownEditor'));

interface PreviewTabProps {
  selectedItem: QueueItem | null;
  markdownContent?: string;
  theme?: 'dark' | 'light';
  zoom: number;
  onZoomChange: (zoom: number) => void;
  previewNonce: number;
  onRefresh: () => void;
  onOpenInEditor?: (path: string) => void;
  onOpenDocument?: (path: string) => void;
  readingSettings: ReadingSettings;
  editor: DocumentEditor;
  isRunning: boolean;
  onSavedCopy: (document: DocumentSnapshot) => void;
}

const ZOOM_MIN = 60;
const ZOOM_MAX = 200;
const ZOOM_STEP = 10;

const PERSIAN_REGEX = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/g;
const LATIN_REGEX = /[a-zA-Z]/g;

function getDirectionLabel(content?: string): string {
  if (!content) return 'وزیرمتن · جهت‌بندی هوشمند';
  const withoutCode = content.replace(/```[\s\S]*?```/g, ' ').replace(/`[^`]+`/g, ' ');
  const faCount = (withoutCode.match(PERSIAN_REGEX) || []).length;
  const enCount = (withoutCode.match(LATIN_REGEX) || []).length;
  if (faCount === 0 && enCount > 0) return 'Latin · چپ‌چین (LTR)';
  if (enCount === 0 && faCount > 0) return 'وزیرمتن · راست‌چین (RTL)';
  if (faCount > 0 && enCount > 0) return 'وزیرمتن · دوزبانه هوشمند (BiDi)';
  return 'جهت‌بندی هوشمند';
}

export const PreviewTab: React.FC<PreviewTabProps> = ({
  selectedItem,
  markdownContent,
  theme = 'dark',
  zoom,
  onZoomChange,
  previewNonce,
  onRefresh,
  onOpenInEditor,
  onOpenDocument,
  readingSettings,
  editor, isRunning, onSavedCopy,
}) => {
  const [viewMode, setViewMode] = useState<'rendered' | 'source'>('rendered');
  const [isLoading, setIsLoading] = useState(true);
  const [preview, setPreview] = useState<PreviewSource | null>(null);
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [livePreview, setLivePreview] = useState(true);
  const [editorError, setEditorError] = useState('');
  const [previewBusy, setPreviewBusy] = useState(false);
  const [copyBusy, setCopyBusy] = useState(false);
  const [copyTarget, setCopyTarget] = useState<{ source: string; path: string; revision: string } | null>(null);
  const [reloadConfirm, setReloadConfirm] = useState(false);
  const draft = selectedItem ? editor.drafts[documentKey(selectedItem.path)] : undefined;
  const dirty = draftIsDirty(draft);
  const lastEditor = useRef<{ path: string; draft: EditorDraft } | null>(null);
  if (draft && selectedItem) lastEditor.current = { path: selectedItem.path, draft };
  const iframe = useRef<HTMLIFrameElement>(null);
  const scrollPositions = useRef(new Map<string, { x: number; y: number }>());
  const readingRef = useRef(readingSettings);
  readingRef.current = readingSettings;

  const updateAppearance = () => {
    const doc = iframe.current?.contentDocument;
    if (doc?.head) applyPreviewAppearance(doc, theme, zoom, readingSettings);
  };

  useEffect(updateAppearance, [theme, zoom, preview, readingSettings.lineHeight, readingSettings.readingWidth, readingSettings.wrapCode]);

  useEffect(() => {
    if (!readingSettings.rememberScroll) scrollPositions.current.clear();
  }, [readingSettings.rememberScroll]);

  useEffect(() => {
    if (!editing || !selectedItem) return;
    let stale = false; setEditorError('');
    editor.open(selectedItem.path).catch(error => { if (!stale) setEditorError(String(error instanceof Error ? error.message : error)); });
    return () => { stale = true; };
  }, [editing, selectedItem?.path, editor.open]);

  useEffect(() => {
    if (!selectedItem) return;
    if (editing && !livePreview) { setPreviewBusy(false); return; }
    let stale = false;
    const controller = new AbortController();
    const file = selectedItem.path;
    if (previewPath !== file) setIsLoading(true);
    const timer = window.setTimeout(() => {
      setPreviewBusy(true);
      const rendered = draft ? loadDraftPreview(file, draft.text, controller.signal) : loadPreviewDocument(file, 'light', 100);
      void rendered.then(src => {
        if (stale) return;
        setPreview(src); setPreviewPath(file);
        if (src.kind === 'error') setIsLoading(false);
      }).catch(() => {}).finally(() => { if (!stale) setPreviewBusy(false); });
    }, draft ? 450 : 0);
    return () => {
      stale = true; window.clearTimeout(timer); controller.abort();
    };
  }, [selectedItem?.path, previewNonce, draft?.text, editing, livePreview]);

  const saveCopy = async (source: string, path: string, revision: string | null) => {
    setCopyBusy(true); setEditorError('');
    try { const result = await editor.saveCopy(source, path, revision); setCopyTarget(null); onSavedCopy(result); }
    catch (error) { setEditorError(error instanceof Error ? error.message : String(error)); }
    finally { setCopyBusy(false); }
  };
  const pickCopy = async () => {
    if (!selectedItem || copyBusy || isRunning) return;
    const source = selectedItem.path;
    setCopyBusy(true); setEditorError('');
    try {
      await editor.open(source);
      let path = await pickSaveMarkdown(source.replace(/(\.(?:md|markdown))$/i, '-copy$1'));
      if (!path) return;
      if (!/\.[^/\\]+$/.test(path)) path += '.md';
      if (documentKey(path) === documentKey(source)) { await editor.save(source); return; }
      if (draftIsDirty(editor.ref.current[documentKey(path)])) throw new DocumentFailure('این فایل در صف تغییرات ذخیره‌نشده دارد؛ ابتدا تغییرات همان سند را ذخیره یا کنار بگذارید.');
      try {
        const existing = await readDocument(path);
        setCopyTarget({ source, path, revision: existing.revision });
      } catch (error) {
        if (error instanceof DocumentFailure && error.code === 'NOT_FOUND') await saveCopy(source, path, null);
        else throw error;
      }
    } catch (error) { setEditorError(error instanceof Error ? error.message : String(error)); }
    finally { setCopyBusy(false); }
  };
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (event.defaultPrevented || document.querySelector('dialog[open]') || !selectedItem || isRunning) return;
      if ((event.ctrlKey || event.metaKey) && (event.code === 'KeyS' || event.key.toLowerCase() === 's')) {
        event.preventDefault();
        if (event.shiftKey) void pickCopy();
        else if (draft) { setEditorError(''); void editor.save(selectedItem.path); }
      }
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [selectedItem?.path, draft, isRunning, copyBusy, editor.save]);

  if (!selectedItem) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-muted">
        <FileText className="w-12 h-12 stroke-[1.5] mb-3 text-dim" />
        <p className="text-sm font-medium text-main">سندی انتخاب نشده است</p>
        <p className="text-xs text-muted mt-1 max-w-[240px] leading-relaxed">
          یک فایل را از لیست صف انتخاب کنید تا پیش‌نمایش آن نمایش داده شود.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-card transition-colors duration-200">
      {/* Slim preview toolbar */}
      <div className="preview-bar flex items-center justify-between gap-3 px-3 h-11 border-b border-main bg-surface transition-colors">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <FileText className="w-4 h-4 text-blue-500 shrink-0" />
          <span
            className="text-xs font-mono font-medium text-main truncate min-w-0"
            dir="ltr"
            title={selectedItem.path}
          >
            {selectedItem.name}
          </span>
          {selectedItem.sizeStr && (
            <span
              className="preview-bar-size text-[11px] text-muted font-mono truncate min-w-0"
              dir="ltr"
              title={selectedItem.sizeStr}
            >
              {selectedItem.sizeStr}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="preview-bar-hint text-[11px] text-dim whitespace-nowrap">
            {getDirectionLabel(markdownContent)}
          </span>

          <div className="h-5 w-px bg-subtle shrink-0" aria-hidden="true" />

          {/* Zoom cluster */}
          <div className="flex items-center bg-subtle rounded border border-main p-0.5 gap-0.5">
            <button
              onClick={() => onZoomChange(Math.max(ZOOM_MIN, zoom - ZOOM_STEP))}
              disabled={zoom <= ZOOM_MIN}
              className="btn p-1 rounded text-muted hover:text-main hover:bg-hover"
              title="کوچک‌نمایی پیش‌نمایش"
              aria-label="کوچک‌نمایی"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span
              className="text-[11px] font-mono text-main w-11 text-center whitespace-nowrap select-none"
              aria-live="polite"
            >
              {zoom}%
            </span>
            <button
              onClick={() => onZoomChange(Math.min(ZOOM_MAX, zoom + ZOOM_STEP))}
              disabled={zoom >= ZOOM_MAX}
              className="btn p-1 rounded text-muted hover:text-main hover:bg-hover"
              title="بزرگ‌نمایی پیش‌نمایش"
              aria-label="بزرگ‌نمایی"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* View mode toggle pill */}
          <div className="flex items-center bg-subtle p-0.5 rounded border border-main text-xs gap-0.5">
            <button
              onClick={() => { setViewMode('rendered'); setEditing(false); }}
              className={`btn px-2 py-0.5 rounded ${
                viewMode === 'rendered'
                  ? 'bg-blue-600 text-white font-medium'
                  : 'text-muted hover:text-main'
              }`}
              title="پیش‌نمایش سند با فونت وزیرمتن و ساختار کامل"
              aria-pressed={viewMode === 'rendered'}
            >
              <Eye className="w-3.5 h-3.5" />
              <span className="preview-bar-label">پیش‌نمایش</span>
            </button>
            <button
              onClick={() => { setViewMode('source'); setEditing(false); }}
              className={`btn px-2 py-0.5 rounded ${
                viewMode === 'source'
                  ? 'bg-blue-600 text-white font-medium'
                  : 'text-muted hover:text-main'
              }`}
              title="مشاهده متن خام مارک‌داون"
              aria-pressed={viewMode === 'source'}
            >
              <Code className="w-3.5 h-3.5" />
              <span className="preview-bar-label">کد منبع</span>
            </button>
          </div>

          <Tooltip label="ویرایش سند در همین پیش‌نمایش">
            <button type="button" aria-label="ویرایش سند" aria-pressed={editing} disabled={isRunning}
              onClick={() => { setViewMode('rendered'); setEditing(value => !value); }}
              className={`btn p-1.5 rounded ${editing ? 'bg-blue-600 text-white' : 'bg-subtle text-muted hover:bg-hover hover:text-main'}`}>
              <Pencil className="w-4 h-4" />
            </button>
          </Tooltip>

          <div className="h-5 w-px bg-subtle shrink-0" aria-hidden="true" />

          <button
            onClick={() => { if (dirty) setReloadConfirm(true); else { if (draft) void editor.reload(selectedItem.path).catch(error => setEditorError(String(error))); onRefresh(); } }}
            disabled={draft?.saving || copyBusy}
            className="btn p-1.5 rounded bg-subtle hover:bg-hover text-muted hover:text-main"
            title="بازسازی پیش‌نمایش"
            aria-label="بازسازی پیش‌نمایش"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>

          {onOpenInEditor && (
            <Tooltip label="باز کردن محل فایل در اکسپلورر">
              <button
                onClick={() => onOpenInEditor(selectedItem.path)}
                className="btn p-1.5 rounded bg-subtle hover:bg-hover text-muted hover:text-main"
                aria-label="باز کردن در اکسپلورر"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </Tooltip>
          )}
        </div>
      </div>

      {(editing || dirty || editorError) && <div className="editor-action-bar bg-surface border-b border-main shrink-0 px-3 py-2">
        <div className="flex items-center flex-wrap gap-2">
          <span role="status" className="flex items-center gap-1.5 text-xs text-muted me-auto">
            {draft?.saving || copyBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : dirty ? <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> : <Check className="w-3.5 h-3.5" />}
            {draft?.saving || copyBusy ? 'در حال ذخیره…' : !draft ? (editorError ? 'ویرایشگر آماده نشد' : 'در حال بارگذاری ویرایشگر…') : dirty ? 'تغییرات ذخیره‌نشده' : 'همهٔ تغییرات ذخیره شده‌اند'}
          </span>
          <button type="button" aria-label="ذخیره سند" disabled={!dirty || draft?.saving || copyBusy || isRunning} onClick={() => { setEditorError(''); void editor.save(selectedItem.path); }}
            className="btn px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs"><Save className="w-3.5 h-3.5" />ذخیره</button>
          <Tooltip label="ذخیره با نام دیگر (Ctrl+Shift+S)"><button type="button" aria-label="ذخیره با نام دیگر" disabled={!draft || draft.saving || copyBusy || isRunning} onClick={() => void pickCopy()}
            className="btn p-1.5 rounded text-muted hover:bg-subtle hover:text-main"><Copy className="w-4 h-4" /></button></Tooltip>
          {editing && <>
            <label className="flex items-center gap-1.5 text-[11px] text-muted cursor-pointer"><input type="checkbox" className="accent-blue-600" checked={livePreview} onChange={event => setLivePreview(event.target.checked)} />پیش‌نمایش زنده</label>
            <button type="button" aria-label="پایان ویرایش" onClick={() => setEditing(false)} className="btn p-1.5 rounded text-muted hover:bg-subtle hover:text-main"><X className="w-4 h-4" /></button>
          </>}
        </div>
        {(draft?.error || editorError) && <p role="alert" className="text-xs leading-6 text-rose-600 dark:text-rose-400 mt-2">{editorError || draft?.error}</p>}
        {draft?.readOnly && <p className="text-xs text-muted leading-6 mt-1">فایل فقط‌خواندنی است؛ ویرایش را با نام دیگری ذخیره کنید.</p>}
        {draft?.recovered && <p className="text-xs text-amber-700 dark:text-amber-300 leading-6 mt-1">پیش‌نویس محلی بازیابی شد؛ برای ثبت در فایل، ذخیره را بزنید.</p>}
        {draft?.recoveryError && dirty && <p role="alert" className="text-xs text-amber-700 dark:text-amber-300 leading-6 mt-1">نسخهٔ بازیابی محلی ذخیره نشد؛ پیش از خروج سند را ذخیره کنید.</p>}
      </div>}

      {/* Content Rendering Body */}
      <div className="flex-1 min-h-0 overflow-hidden relative flex flex-col">
        {(editing || lastEditor.current) && <div className={editing ? `editor-area min-h-0 overflow-hidden ${livePreview ? 'editor-area-split' : 'flex-1'}` : 'hidden'}>
          {lastEditor.current && <div className={draft ? 'h-full' : 'hidden'}><Suspense fallback={<div className="flex items-center justify-center h-full text-muted text-xs">در حال آماده‌سازی ویرایشگر…</div>}>
            <MarkdownEditor path={lastEditor.current.path} text={lastEditor.current.draft.text} theme={theme} readOnly={!draft || draft.saving || copyBusy || isRunning}
              onChange={text => { if (lastEditor.current) editor.change(lastEditor.current.path, text); }} onSave={() => { if (!isRunning && lastEditor.current) void editor.save(lastEditor.current.path); }} />
          </Suspense></div>}
          {!draft && <div className="p-5 text-sm text-muted">{editorError || 'در حال خواندن سند…'}</div>}
        </div>}
        {editing && livePreview && <div className="flex items-center justify-between px-3 py-1 border-y border-main text-[11px] text-muted bg-surface shrink-0"><span>پیش‌نمایش زندهٔ پیش‌نویس</span><span>{previewBusy ? 'در حال به‌روزرسانی…' : 'تغییرات فقط با ذخیره روی فایل نوشته می‌شوند'}</span></div>}
        <div className={viewMode === 'rendered' && (!editing || livePreview) ? 'flex-1 min-h-0 relative' : 'hidden'}>
            {isLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-card text-muted z-10">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                <span className="text-xs">در حال رندر پیش‌نمایش…</span>
              </div>
            )}
            {preview?.kind === 'error' ? (
              <div className="h-full flex flex-col items-center justify-center gap-2 p-8 text-center">
                <AlertTriangle className="w-8 h-8 text-rose-500" />
                <p className="text-sm font-medium text-main">پیش‌نمایش ساخته نشد</p>
                <p className="text-xs text-muted font-mono max-w-[520px] break-words" dir="ltr">
                  {preview.message}
                </p>
                <button onClick={onRefresh} className="btn mt-2 px-3 py-1.5 rounded text-xs bg-subtle hover:bg-hover text-main">
                  تلاش دوباره
                </button>
              </div>
            ) : preview && previewPath === selectedItem.path ? (
              <iframe
                ref={iframe}
                key={`${selectedItem.path}-${previewNonce}`}
                src={preview?.kind === 'url' ? preview.url : undefined}
                srcDoc={preview?.kind === 'document' ? preview.html : undefined}
                onLoad={() => {
                  updateAppearance(); setIsLoading(false);
                  const doc = iframe.current?.contentDocument;
                  const win = doc?.defaultView;
                  if (!doc || !win) return;
                  const path = selectedItem.path;
                  const saved = readingRef.current.rememberScroll ? scrollPositions.current.get(path) : undefined;
                  const headingIds = new Map<string, number>();
                  for (const heading of doc.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
                    if (heading.id) continue;
                    const base = (heading.textContent || '').trim().toLowerCase().replace(/[^\p{L}\p{N}\s_-]/gu, '').replace(/\s+/g, '-');
                    const count = headingIds.get(base) || 0;
                    headingIds.set(base, count + 1);
                    heading.id = base + (count ? `-${count}` : '');
                  }
                  doc.addEventListener('click', event => {
                    const link = (event.target as Element).closest?.('a[href]');
                    const href = link?.getAttribute('href') || '';
                    if (href.startsWith('#')) {
                      event.preventDefault();
                      try { doc.getElementById(decodeURIComponent(href.slice(1)))?.scrollIntoView(); } catch { /* Ignore malformed fragment encoding. */ }
                      return;
                    }
                    const target = link && linkedMarkdownPath(path, link.getAttribute('href') || '');
                    if (target && onOpenDocument) { event.preventDefault(); onOpenDocument(target); }
                    else if (link && /^https?:/i.test(link.getAttribute('href') || '')) {
                      event.preventDefault(); void openExternalUrl(link.getAttribute('href')!).catch(error => console.error(error));
                    }
                  });
                  doc.addEventListener('scroll', () => {
                    if (!readingRef.current.rememberScroll) return;
                    scrollPositions.current.set(path, { x: win.scrollX, y: win.scrollY });
                    if (scrollPositions.current.size > 32) scrollPositions.current.delete(scrollPositions.current.keys().next().value!);
                  }, { passive: true });
                  doc.addEventListener('keydown', event => {
                    if (!['Comma', 'KeyO', 'KeyW', 'KeyR', 'KeyS'].includes(event.code) && !['o', 'w', 'r', 's', 'Delete', 'F5'].includes(event.key.length === 1 ? event.key.toLowerCase() : event.key)) return;
                    const forwarded = new KeyboardEvent('keydown', { key: event.key, code: event.code, ctrlKey: event.ctrlKey, metaKey: event.metaKey, shiftKey: event.shiftKey, cancelable: true });
                    if (!window.dispatchEvent(forwarded)) event.preventDefault();
                  });
                  if (saved) void doc.fonts.ready.then(() => {
                    if (iframe.current?.contentDocument === doc) win.scrollTo(saved.x, saved.y);
                  });
                }}
                className="w-full h-full border-0 bg-transparent"
                title={`پیش‌نمایش ${selectedItem.name}`}
              />
            ) : null}
        </div>
          <div
            className={`${viewMode === 'source' ? '' : 'hidden'} h-full overflow-y-auto p-6 font-mono text-xs text-main leading-relaxed text-left whitespace-pre-wrap selection:bg-blue-500/30`}
            dir="ltr"
          >
            {(draft ? draft.text : markdownContent) || 'این فایل خالی است.'}
          </div>
      </div>
      {reloadConfirm && <AppDialog title="بازخوانی نسخهٔ دیسک" description="تغییرات ذخیره‌نشدهٔ این سند کنار گذاشته می‌شوند." onClose={() => setReloadConfirm(false)}
        footer={<><button type="button" className="btn px-3 py-2 rounded border border-subtle hover:bg-subtle text-sm" onClick={() => setReloadConfirm(false)}>انصراف</button>
          <button type="button" className="btn px-3 py-2 rounded bg-red-600 hover:bg-red-700 text-white text-sm" onClick={() => { void editor.reload(selectedItem.path).then(() => { setReloadConfirm(false); setEditorError(''); }).catch(error => setEditorError(String(error))); }}>کنارگذاشتن تغییرات و بازخوانی</button></>}>
        <p className="text-sm text-muted break-all" dir="auto">{selectedItem.name}</p>
      </AppDialog>}
      {copyTarget && <AppDialog title="جایگزینی فایل موجود" description="فایلی با این نام وجود دارد؛ ذخیره، محتوای آن را جایگزین می‌کند." onClose={() => { if (!copyBusy) setCopyTarget(null); }}
        footer={<><button type="button" disabled={copyBusy} className="btn px-3 py-2 rounded border border-subtle hover:bg-subtle text-sm" onClick={() => setCopyTarget(null)}>انصراف</button>
          <button type="button" disabled={copyBusy} className="btn px-3 py-2 rounded bg-red-600 hover:bg-red-700 text-white text-sm" onClick={() => void saveCopy(copyTarget.source, copyTarget.path, copyTarget.revision)}>ذخیره و جایگزینی</button></>}>
        <p className="text-sm text-muted break-all" dir="ltr">{copyTarget.path}</p>
        {editorError && <p role="alert" className="text-xs text-rose-600 dark:text-rose-400 mt-3">{editorError}</p>}
      </AppDialog>}
    </div>
  );
};
