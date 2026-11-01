import React, { lazy, Suspense, useState, useEffect, useCallback, useRef } from 'react';
import { QueueItem, ConvertOptions, LogEntry, ProgressEvent } from './types';
import { DEFAULT_CONVERT_OPTIONS } from './services/cliTranslator';
import {
  executeConversion,
  cancelActiveConversion,
  pickDirectory,
  pickFiles,
  scanFolder,
  openInExplorer,
  readFileContent,
  fetchInitialItems,
  resolveStartupFiles,
  onOpenFileRequested,
  isTauri,
} from './services/tauriBridge';
import { listenForHandoffs } from './services/singleInstance';
import { documentKey, mergeQueueItems, removeQueueItems } from './services/queueState';
import { DEFAULT_APP_SETTINGS, readPreferences, savePreferences, type AppSettings } from './services/appSettings';
import { draftIsDirty, useDocumentEditor } from './services/useDocumentEditor';
import type { DocumentSnapshot } from './services/documents';
import { AppDialog } from './components/AppDialog';
import { ConversionRuntimePanel, runtimePhase } from './components/ConversionRuntimePanel';
import { useConversionRuntime } from './services/useConversionRuntime';
import { Header } from './components/Header';
import { StatusBar } from './components/StatusBar';
import { QueuePanel } from './components/QueuePanel';
import { InspectorPanel } from './components/InspectorPanel';
import { WorkspacePanel } from './components/WorkspacePanel';
import { PaneSplitter } from './components/PaneSplitter';

type NativeBusy = 'files' | 'folder' | 'output-dir' | 'explorer' | null;
type WorkspaceTab = 'preview' | 'terminal';
const SettingsDialog = lazy(() => import('./components/SettingsDialog'));

const QUEUE_MIN = 300;
const QUEUE_MAX = 640;
const INSPECTOR_MIN = 300;
const INSPECTOR_MAX = 720;

/** Below 1280px the three panes cannot all sit at their comfortable widths. */
const compactViewport = () =>
  typeof window !== 'undefined' && window.innerWidth < 1280;
const queueDefault = () => (compactViewport() ? 320 : 380);
const inspectorDefault = () => (compactViewport() ? 340 : 400);

const storedWidth = (key: string, fallback: number, min: number, max: number): number => {
  try {
    const raw = parseInt(localStorage.getItem(key) || '', 10);
    return Number.isFinite(raw) ? Math.max(min, Math.min(max, raw)) : fallback;
  } catch {
    return fallback;
  }
};

const storeWidth = (key: string, value: number): void => {
  try {
    localStorage.setItem(key, String(value));
  } catch {
    // Storage may be unavailable; the width still applies for this session.
  }
};

export const App: React.FC = () => {
  const conversionRuntime = useConversionRuntime();
  const [runtimeDialogOpen, setRuntimeDialogOpen] = useState(false);
  const [initialPreferences] = useState(readPreferences);
  const [settings, setSettings] = useState(initialPreferences.settings);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches);
  const theme = settings.theme === 'system' ? (systemDark ? 'dark' : 'light') : settings.theme;
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [storageError, setStorageError] = useState(false);
  const [settingsNotice, setSettingsNotice] = useState('');
  const [pendingEdits, setPendingEdits] = useState<{ paths: string[]; next: () => void; allowDiscard: boolean } | null>(null);
  const [savingEdits, setSavingEdits] = useState(false);
  const [pendingError, setPendingError] = useState('');
  const changeSettings = useCallback((patch: Partial<AppSettings>) => {
    setSettings(previous => ({ ...previous, ...patch }));
    setSettingsNotice('');
  }, []);

  const [queueWidth, setQueueWidth] = useState<number>(() =>
    storedWidth('pane_queue_width_v2', queueDefault(), QUEUE_MIN, Math.max(QUEUE_MIN, Math.min(QUEUE_MAX, window.innerWidth - INSPECTOR_MIN - 336)))
  );
  const [inspectorWidth, setInspectorWidth] = useState<number>(() =>
    storedWidth('pane_inspector_width', inspectorDefault(), INSPECTOR_MIN, Math.max(INSPECTOR_MIN, Math.min(INSPECTOR_MAX, window.innerWidth - queueWidth - 336)))
  );

  const [inspectorCollapsed, setInspectorCollapsed] = useState(() => {
    try { return localStorage.getItem('pane_inspector_collapsed') === '1'; } catch { return false; }
  });
  useEffect(() => storeWidth('pane_inspector_collapsed', inspectorCollapsed ? 1 : 0), [inspectorCollapsed]);
  useEffect(() => {
    const fit = () => {
      const queue = Math.min(queueWidth, Math.max(QUEUE_MIN, window.innerWidth - (inspectorCollapsed ? 0 : INSPECTOR_MIN) - 336));
      setQueueWidth(queue);
      setInspectorWidth(previous => Math.max(INSPECTOR_MIN, Math.min(previous, window.innerWidth - queue - 336)));
    };
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, [queueWidth, inspectorCollapsed]);


  const [items, setItems] = useState<QueueItem[]>([]);
  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const activeItemRef = useRef(activeItemId);
  activeItemRef.current = activeItemId;
  const [options, setOptions] = useState<ConvertOptions>(initialPreferences.options);
  const [markdownContent, setMarkdownContent] = useState<string>('');
  const [query, setQuery] = useState('');
  const [nativeBusy, setNativeBusy] = useState<NativeBusy>(null);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>('preview');
  const zoom = settings.previewZoom;
  const [previewNonce, setPreviewNonce] = useState(0);

  const appendLog = useCallback((level: LogEntry['level'], message: string) => {
    setLogs((prev) => [
      ...prev.slice(-999),
      { id: `${level}-${Date.now()}-${Math.random()}`, timestamp: new Date().toLocaleTimeString(), level, message },
    ]);
  }, []);

  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'init-1',
      timestamp: new Date().toLocaleTimeString(),
      level: 'info',
      message: 'محیط کاری MdPersia با موتور تبدیل واقعی آماده به کار است.',
    },
  ]);
  const [isRunning, setIsRunning] = useState(false);
  const [isWatching, setIsWatching] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [statusMessage, setStatusMessage] = useState('آماده به کار');

  const itemsRef = useRef(items);
  itemsRef.current = items;
  const openRequest = useRef(0);
  const queueEpoch = useRef(0);
  const removedRequests = useRef(new Map<string, number>());
  const selectionAnchor = useRef<string | null>(null);
  const updateQueue = useCallback((update: (items: QueueItem[]) => QueueItem[]) => {
    itemsRef.current = update(itemsRef.current);
    setItems(itemsRef.current);
  }, []);
  const editor = useDocumentEditor(useCallback((document: DocumentSnapshot) => {
    updateQueue(current => current.map(item => documentKey(item.path) === documentKey(document.path)
      ? { ...item, sizeBytes: document.sizeBytes, sizeStr: `${(document.sizeBytes / 1024).toFixed(1)} KB`, status: 'pending', error: undefined } : item));
    const active = itemsRef.current.find(item => item.id === activeItemRef.current);
    if (active && documentKey(active.path) === documentKey(document.path)) { setMarkdownContent(document.text); setPreviewNonce(value => value + 1); }
    setStatusMessage('تغییرات سند ذخیره شد.');
  }, [updateQueue]));
  const guardEdits = (paths: string[], next: () => void, allowDiscard = true) => {
    if (paths.some(path => editor.ref.current[documentKey(path)]?.saving)) {
      setStatusMessage('ذخیره در حال انجام است؛ چند لحظه صبر کنید.'); return;
    }
    const dirty = paths.filter(path => draftIsDirty(editor.ref.current[documentKey(path)]));
    if (!dirty.length) { next(); return; }
    setPendingError(''); setPendingEdits({ paths: dirty, next, allowDiscard });
  };

  const appendItems = useCallback((incoming: QueueItem[], message?: string, focus = true, forceFocus = false) => {
    const shouldFocus = focus && (forceFocus || settingsRef.current.focusNewFiles || !activeItemRef.current);
    const merged = mergeQueueItems(itemsRef.current, incoming);
    itemsRef.current = merged.items;
    setItems(merged.items);
    if (shouldFocus && merged.focusedId) {
      activeItemRef.current = merged.focusedId;
      setActiveItemId(merged.focusedId);
      setWorkspaceTab('preview');
      setPreviewNonce(nonce => nonce + 1);
      selectionAnchor.current = merged.focusedId;
      setSelectedIds(new Set([merged.focusedId]));
      setQuery('');
    }
    if (message) setStatusMessage(message);
    return { ...merged, focused: shouldFocus };
  }, []);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  useEffect(() => {
    if (settings.theme !== 'system') return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    setSystemDark(media.matches);
    const update = () => setSystemDark(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [settings.theme]);

  useEffect(() => {
    setStorageError(!savePreferences(settings, options));
  }, [settings, options]);

  /** Every explicit open appends/deduplicates; the last request owns preview focus. */
  const loadDocuments = useCallback(async (file: string | null, viaViewer: boolean) => {
    const request = ++openRequest.current;
    const epoch = queueEpoch.current;
    const { items: initial, viewer } = await fetchInitialItems(file);
    if (epoch !== queueEpoch.current) return;
    if (initial.length === 0) {
      if (request === openRequest.current) setStatusMessage(file ? 'فایل باز نشد؛ وجود فایل و دسترسی به آن را بررسی کنید.' : 'برای شروع یک فایل Markdown باز کنید.');
      return;
    }
    const delivered = initial.filter(item => (removedRequests.current.get(documentKey(item.path)) ?? -1) < request);
    if (!delivered.length) return;
    const merged = appendItems(delivered, undefined, request === openRequest.current);
    if ((viaViewer || viewer) && request === openRequest.current) {
      setStatusMessage(merged.focused ? `«${initial[0].name}» در حالت مشاهده‌گر باز شد.` : `«${initial[0].name}» به صف افزوده شد.`);
    }
  }, [appendItems]);

  useEffect(() => {
    let cancelled = false;
    resolveStartupFiles()
      .then(async (files) => {
        if (cancelled) return;
        // The launcher/server broker handles OS handoffs without a timed browser probe.
        if (files.length) files.forEach(file => loadDocuments(file, true));
        else loadDocuments(null, false);
        const url = new URL(window.location.href);
        url.searchParams.delete('file');
        window.history.replaceState(null, '', url);
      })
      .catch(() => loadDocuments(null, false));
    return () => {
      cancelled = true;
    };
  }, [loadDocuments]);

  /** Single instance: a second launch routes its file into this running window. */
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let disposed = false;
    const disposeBrowser = listenForHandoffs((path) => {
      loadDocuments(path, true);
      appendLog('info', `Open-with handoff: ${path}`);
    });
    onOpenFileRequested((path) => {
      loadDocuments(path, true);
      appendLog('info', `Open-with handoff: ${path}`);
    }).then((dispose) => {
      if (disposed) dispose();
      else unlisten = dispose;
    });
    return () => {
      disposed = true;
      disposeBrowser();
      unlisten?.();
    };
  }, [loadDocuments, appendLog]);

  const selectedItem = items.find((it) => it.id === activeItemId) || null;

  useEffect(() => {
    if (!selectedItem?.path) {
      setMarkdownContent('');
      return;
    }
    let stale = false;
    void editor.refreshClean(selectedItem.path).catch(error => appendLog('warn', `بازخوانی نسخهٔ دیسک انجام نشد: ${String(error)}`));
    readFileContent(selectedItem.path).then((res) => {
      if (stale) return;
      setMarkdownContent(res.value);
      if (res.error) appendLog('warn', `خواندن فایل ناموفق بود (${selectedItem.name}): ${res.error}`);
    });
    return () => {
      stale = true;
    };
  }, [selectedItem?.path, previewNonce, appendLog, editor.refreshClean]);

  const handleToggleTheme = () => changeSettings({ theme: theme === 'dark' ? 'light' : 'dark' });

  const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

  const handleResizeQueue = useCallback((delta: number) => {
    setQueueWidth((prev) => {
      const limit = Math.max(QUEUE_MIN, Math.min(QUEUE_MAX, window.innerWidth - (inspectorCollapsed ? 0 : inspectorWidth) - 336));
      const next = clamp(prev + delta, QUEUE_MIN, limit);
      storeWidth('pane_queue_width_v2', next);
      return next;
    });
  }, [inspectorCollapsed, inspectorWidth]);

  const handleResizeInspector = (delta: number) => {
    const maximum = Math.max(INSPECTOR_MIN, Math.min(INSPECTOR_MAX, window.innerWidth - queueWidth - 336));
    setInspectorWidth(previous => clamp((inspectorCollapsed ? 0 : previous) + delta, 0, maximum));
    if (delta > 0) setInspectorCollapsed(false);
  };
  const finishResizeInspector = () => {
    if (inspectorWidth < 100) {
      setInspectorCollapsed(true);
      setInspectorWidth(storedWidth('pane_inspector_width', inspectorDefault(), INSPECTOR_MIN, INSPECTOR_MAX));
    } else {
      const next = Math.max(INSPECTOR_MIN, inspectorWidth);
      setInspectorWidth(next); storeWidth('pane_inspector_width', next);
    }
  };

  const handleOptionChange = <K extends keyof ConvertOptions>(
    key: K,
    value: ConvertOptions[K]
  ) => {
    setOptions((prev) => ({ ...prev, [key]: value }));
  };

  /** Folder recursion affects future imports; existing documents remain in the queue. */
  const handleRecursiveToggle = (newRecursive: boolean) => {
    setOptions((prev) => ({ ...prev, recursive: newRecursive }));
    setStatusMessage(newRecursive ? 'پوشه‌های بعدی همراه زیرپوشه‌ها افزوده می‌شوند.' : 'از پوشه‌های بعدی فقط فایل‌های سطح اول افزوده می‌شوند.');
  };

  const handleSelectItem = (id: string, e: { ctrlKey: boolean; metaKey: boolean; shiftKey?: boolean }) => {
    activeItemRef.current = id;
    setActiveItemId(id);
    setWorkspaceTab('preview');
    if (e.shiftKey && selectionAnchor.current) {
      const visible = items.filter(item => !query.trim() || `${item.name} ${item.relativePath || ''}`.toLowerCase().includes(query.trim().toLowerCase()));
      const anchor = visible.findIndex(item => item.id === selectionAnchor.current);
      const target = visible.findIndex(item => item.id === id);
      if (anchor >= 0 && target >= 0) {
        const range = visible.slice(Math.min(anchor, target), Math.max(anchor, target) + 1).map(item => item.id);
        setSelectedIds(new Set(e.ctrlKey || e.metaKey ? [...selectedIds, ...range] : range));
        return;
      }
    }
    selectionAnchor.current = id;
    if (e.ctrlKey || e.metaKey) {
      const next = new Set(selectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      setSelectedIds(next);
    } else {
      setSelectedIds(new Set([id]));
    }
  };

  const handleAddFiles = (files: FileList | File[]) => {
    // Browser File objects do not expose original disk paths. Use the native picker
    // instead of fabricating a relative path that opens the wrong or missing file.
    if (Array.from(files).some(file => !(file as File & { path?: string }).path)) {
      void handlePickFilesNative();
      return;
    }
    const newItems: QueueItem[] = Array.from(files).map((file, idx) => ({
      id: `file-${Date.now()}-${idx}`,
      name: file.name,
      path: (file as File & { path?: string }).path || file.name,
      sizeBytes: file.size,
      sizeStr: `${(file.size / 1024).toFixed(1)} KB`,
      status: 'pending',
    }));
    appendItems(newItems, `${newItems.length} فایل کشیده‌شده به صف افزوده شد.`);
  };

  /**
   * Native pickers always end in a visible outcome: added / cancelled / failed.
   * A silent no-op is what made these controls look dead.
   */
  const handlePickFilesNative = async () => {
    if (nativeBusy) return;
    setNativeBusy('files');
    setStatusMessage('در انتظار انتخاب فایل… دیالوگ ویندوز را ببینید');
    try {
      const res = await pickFiles(['md', 'markdown'], 'انتخاب اسناد مارک‌داون');
      if (res.error) {
        appendLog('error', `File picker failed: ${res.error}`);
        setStatusMessage('دیالوگ انتخاب فایل باز نشد؛ جزئیات در کنسول.');
        return;
      }
      if (res.cancelled || res.value.length === 0) {
        setStatusMessage('انتخاب فایل لغو شد.');
        return;
      }
      appendItems(
        res.value.map((f, idx) => ({
          id: `native-${Date.now()}-${idx}`,
          name: f.name,
          path: f.path,
          sizeBytes: f.sizeBytes,
          sizeStr: f.sizeStr,
          status: 'pending' as const,
          relativePath: f.name,
        })),
        `${res.value.length} فایل از ویندوز به صف افزوده شد.`
      );
    } catch (err: any) {
      appendLog('error', `File picker error: ${err.message || String(err)}`);
      setStatusMessage('خطایی در انتخاب فایل رخ داد.');
    } finally {
      setNativeBusy(null);
    }
  };

  const handleAddFolder = async () => {
    if (nativeBusy) return;
    setNativeBusy('folder');
    setStatusMessage('در انتظار انتخاب پوشه… دیالوگ ویندوز را ببینید');
    try {
      const picked = await pickDirectory('انتخاب پوشه حاوی اسناد');
      if (picked.error) {
        appendLog('error', `Folder picker failed: ${picked.error}`);
        setStatusMessage('دیالوگ انتخاب پوشه باز نشد؛ جزئیات در کنسول.');
        return;
      }
      if (!picked.value) {
        setStatusMessage('انتخاب پوشه لغو شد.');
        return;
      }

      // Scanning runs against the local bridge and can take a moment on large trees.
      const folder = picked.value;
      const scan = await scanFolder(folder, options.recursive);
      setActiveFolder(folder);

      if (scan.error) {
        appendLog('error', `Folder scan failed: ${scan.error}`);
        setStatusMessage('پیمایش پوشه انجام نشد؛ جزئیات در کنسول.');
        return;
      }

      const newItems: QueueItem[] = scan.value.map((f, idx) => ({
        id: `scanned-${Date.now()}-${idx}`,
        name: f.name,
        path: f.path,
        sizeBytes: f.sizeBytes,
        sizeStr: `${(f.sizeBytes / 1024).toFixed(1)} KB`,
        status: 'pending',
        relativePath: f.relativePath,
      }));
      if (newItems.length === 0) {
        setStatusMessage('پوشه انتخاب شد اما فایل مارک‌داونی در آن یافت نشد.');
        return;
      }
      const merged = appendItems(newItems);
      setStatusMessage(`${merged.added} سند جدید از پوشه به صف افزوده شد.`);
    } catch (err: any) {
      appendLog('error', `Folder picker error: ${err.message || String(err)}`);
      setStatusMessage('خطایی در انتخاب پوشه رخ داد.');
    } finally {
      setNativeBusy(null);
    }
  };

  const handleBrowseOutputDir = async () => {
    if (nativeBusy) return;
    setNativeBusy('output-dir');
    setStatusMessage('در انتظار انتخاب پوشه خروجی…');
    try {
      const picked = await pickDirectory('انتخاب پوشه خروجی اسناد');
      if (picked.error) {
        appendLog('error', `Output folder picker failed: ${picked.error}`);
        setStatusMessage('دیالوگ انتخاب پوشه خروجی باز نشد.');
        return;
      }
      if (!picked.value) {
        setStatusMessage('انتخاب پوشه خروجی لغو شد.');
        return;
      }
      handleOptionChange('outputDir', picked.value);
      setStatusMessage(`پوشه خروجی تنظیم شد: ${picked.value}`);
    } catch (err: any) {
      appendLog('error', `Output folder picker error: ${err.message || String(err)}`);
      setStatusMessage('خطایی در انتخاب پوشه خروجی رخ داد.');
    } finally {
      setNativeBusy(null);
    }
  };

  const handleOpenOutputDir = async () => {
    let target = options.outputDir || selectedItem?.path || activeFolder || '';
    if (!target) {
      setStatusMessage('پوشه‌ای برای باز کردن وجود ندارد؛ ابتدا یک سند یا پوشه انتخاب کنید.');
      return;
    }
    // If target is a file, reveal its directory
    if (/\.[a-zA-Z0-9]+$/.test(target)) {
      target = target.replace(/[\\/][^\\/]+$/, '') || '.';
      if (/^[A-Za-z]:$/.test(target)) target += '/';
    }
    if (nativeBusy) return;
    setNativeBusy('explorer');
    try {
      const res = await openInExplorer(target);
      if (res.error) {
        appendLog('error', `Explorer failed for ${target}: ${res.error}`);
        setStatusMessage('باز کردن ویندوز اکسپلورر ناموفق بود.');
        return;
      }
      setStatusMessage('در ویندوز اکسپلورر باز شد.');
    } catch (err: any) {
      appendLog('error', `Explorer error: ${err.message || String(err)}`);
      setStatusMessage('خطایی در باز کردن اکسپلورر رخ داد.');
    } finally {
      setNativeBusy(null);
    }
  };

  const handleBrowseFile = async (key: keyof ConvertOptions, filter?: string) => {
    if (nativeBusy) return;
    setNativeBusy('files');
    setStatusMessage('در انتظار انتخاب فایل… دیالوگ ویندوز را ببینید');
    try {
      const exts = filter ? filter.split(',').map((e) => e.trim().replace(/^\./, '')) : undefined;
      const res = await pickFiles(exts && exts.length ? exts : undefined, 'انتخاب فایل');
      if (res.error) {
        appendLog('error', `File picker failed: ${res.error}`);
        setStatusMessage('دیالوگ انتخاب فایل باز نشد.');
        return;
      }
      if (res.cancelled || res.value.length === 0) {
        setStatusMessage('انتخاب فایل لغو شد.');
        return;
      }
      handleOptionChange(key, res.value[0].path);
      setStatusMessage(`«${String(key)}» تنظیم شد: ${res.value[0].name}`);
    } catch (err: any) {
      appendLog('error', `File browse error: ${err.message || String(err)}`);
      setStatusMessage('خطایی در انتخاب فایل رخ داد.');
    } finally {
      setNativeBusy(null);
    }
  };

  const handleBrowseDir = async (key: keyof ConvertOptions) => {
    if (nativeBusy) return;
    setNativeBusy('folder');
    setStatusMessage('در انتظار انتخاب پوشه… دیالوگ ویندوز را ببینید');
    try {
      const picked = await pickDirectory();
      if (picked.error) {
        appendLog('error', `Folder picker failed: ${picked.error}`);
        setStatusMessage('دیالوگ انتخاب پوشه باز نشد.');
        return;
      }
      if (!picked.value) {
        setStatusMessage('انتخاب پوشه لغو شد.');
        return;
      }
      handleOptionChange(key, picked.value);
      setStatusMessage(`پوشه تنظیم شد: ${picked.value}`);
    } catch (err: any) {
      appendLog('error', `Dir browse error: ${err.message || String(err)}`);
      setStatusMessage('خطایی در انتخاب پوشه رخ داد.');
    } finally {
      setNativeBusy(null);
    }
  };

  const removeDocumentsNow = (ids: Set<string>) => {
    if (isRunning) return;
    for (const item of itemsRef.current) if (ids.has(item.id)) removedRequests.current.set(documentKey(item.path), openRequest.current);
    const next = removeQueueItems(itemsRef.current, ids, activeItemRef.current);
    itemsRef.current = next.items;
    setItems(next.items);
    activeItemRef.current = next.activeId;
    setActiveItemId(next.activeId);
    setSelectedIds(new Set(next.activeId ? [next.activeId] : []));
    setStatusMessage(`${ids.size} سند از صف حذف شد.`);
  };
  const removeDocuments = (ids: Set<string>) => {
    if (isRunning) return;
    const paths = itemsRef.current.filter(item => ids.has(item.id)).map(item => item.path);
    guardEdits(paths, () => { editor.forget(paths); removeDocumentsNow(ids); });
  };
  const handleRemoveSelected = () => removeDocuments(selectedIds);

  const clearQueue = () => {
    if (isRunning) return;
    queueEpoch.current++;
    removedRequests.current.clear();
    selectionAnchor.current = null;
    openRequest.current++;
    itemsRef.current = [];
    setItems([]);
    setSelectedIds(new Set());
    activeItemRef.current = null;
    setActiveItemId(null);
    setQuery('');
    setActiveFolder(null);
    setStatusMessage('صف پاک شد.');
  };

  const handleClearAll = () => {
    if (isRunning) return;
    const paths = itemsRef.current.map(item => item.path);
    if (paths.some(path => editor.ref.current[documentKey(path)]?.saving)) {
      setStatusMessage('ذخیره در حال انجام است؛ چند لحظه صبر کنید.'); return;
    }
    if (paths.some(path => draftIsDirty(editor.ref.current[documentKey(path)]))) {
      guardEdits(paths, () => { editor.forget(paths); clearQueue(); });
    } else if (settings.confirmClearQueue && itemsRef.current.length) setConfirmClear(true);
    else { editor.forget(paths); clearQueue(); }
  };

  const handleClearLogs = () => setLogs([]);

  const handleConvert = async () => {
    if (items.length === 0 || isRunning) return;
    if (items.some(item => draftIsDirty(editor.ref.current[documentKey(item.path)]))) {
      guardEdits(items.map(item => item.path), () => { void handleConvert(); }, false); return;
    }
    if (conversionRuntime.native && options.format !== 'wrap-rtl') {
      try {
        if (!(await conversionRuntime.refresh()).installed) { setRuntimeDialogOpen(true); return; }
      } catch (error) { appendLog('error', String(error)); setRuntimeDialogOpen(true); return; }
    }
    setIsRunning(true);
    setIsWatching(false);
    setProgressPercent(0);
    setCompletedCount(0);
    setStatusMessage(`درحال تبدیل ${items.length} سند با موتور MdPersia...`);

    updateQueue((prev) => prev.map((it) => ({ ...it, status: 'pending', error: undefined })));

    await executeConversion(
      items,
      options,
      (evt: ProgressEvent) => {
        if (evt.type === 'progress') {
          setIsWatching(false);
          setStatusMessage(`در حال تبدیل ${evt.file ?? 'سند'}…`);
          const comp = evt.completed || 0;
          const tot = evt.total || items.length;
          setCompletedCount(comp);
          setProgressPercent(Math.round((comp / tot) * 100));
          if (evt.file) {
            updateQueue((prev) =>
              prev.map((it) => (it.id === evt.itemId ? { ...it, status: 'running' } : it))
            );
          }
        } else if (evt.type === 'watching') {
          setIsWatching(true);
          setStatusMessage(`پایش زنده: در انتظار تغییر ${evt.file ?? 'فایل'}؛ برای پایان، توقف تبدیل را بزنید.`);
          updateQueue(prev => prev.map(item => item.id === evt.itemId ? { ...item, status: 'watching' } : item));
        } else if (evt.type === 'success') {
          if (evt.file) {
            updateQueue((prev) =>
              prev.map((it) => (it.id === evt.itemId ? { ...it, status: 'success' } : it))
            );
          }
        } else if (evt.type === 'error') {
          if (evt.file) {
            updateQueue((prev) =>
              prev.map((it) =>
                it.id === evt.itemId ? { ...it, status: 'error', error: evt.error } : it
              )
            );
          }
        } else if (evt.type === 'done') {
          setProgressPercent(100);
          setCompletedCount(evt.completed ?? 0);
          const succ = evt.completed ?? 0;
          const tot = evt.total ?? items.length;
          setStatusMessage(`فرآیند تبدیل پایان یافت: ${succ} موفق، ${tot - succ} ناموفق.`);
        } else if (evt.type === 'cancelled') {
          updateQueue(prev => prev.map(item => item.status === 'running' || item.status === 'watching' ? { ...item, status: 'pending' } : item));
          setStatusMessage('عملیات تبدیل توسط کاربر لغو گردید.');
        }
      },
      (log: LogEntry) => setLogs((prev) => [...prev.slice(-999), log])
    );

    setIsRunning(false);
    setIsWatching(false);
  };

  const handleCancel = async () => {
    setStatusMessage('در حال توقف تبدیل…');
    try { await cancelActiveConversion(); }
    catch (error) { setStatusMessage(String(error)); }
  };

  const revealInExplorer = async (targetPath: string) => {
    const res = await openInExplorer(targetPath);
    if (res.error) {
      appendLog('error', `Explorer failed for ${targetPath}: ${res.error}`);
      setStatusMessage(`باز کردن اکسپلورر ناموفق بود: ${res.error}`);
    } else {
      setStatusMessage('در ویندوز اکسپلورر باز شد.');
    }
  };

  const revealFolderInExplorer = async (filePath: string) => {
    let folder = filePath.replace(/[\\/][^\\/]+$/, '');
    if (!folder || folder === filePath) folder = '.';
    if (/^[A-Za-z]:$/.test(folder)) folder += '/';
    await revealInExplorer(folder);
  };

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (settingsOpen || confirmClear || pendingEdits || document.querySelector('dialog[open]')) return;
      const editing = event.target instanceof HTMLElement &&
        (event.target.matches('input, textarea, select') || event.target.isContentEditable);
      if ((event.ctrlKey || event.metaKey) && event.code === 'Comma') {
        event.preventDefault(); setSettingsOpen(true);
      } else if ((event.ctrlKey || event.metaKey) && (event.code === 'KeyO' || event.key.toLowerCase() === 'o')) {
        event.preventDefault(); handlePickFilesNative();
      } else if (event.key === 'F5' || ((event.ctrlKey || event.metaKey) && (event.code === 'KeyR' || event.key.toLowerCase() === 'r'))) {
        event.preventDefault(); setPreviewNonce(nonce => nonce + 1);
      } else if (!editing && event.key === 'Delete') {
        event.preventDefault(); handleRemoveSelected();
      } else if (!editing && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'w' && activeItemId && !isRunning) {
        event.preventDefault();
        removeDocuments(new Set([activeItemId]));
      }
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [activeItemId, selectedIds, isRunning, nativeBusy, settingsOpen, confirmClear, pendingEdits]);

  const closeGuard = useRef(guardEdits); closeGuard.current = guardEdits;
  useEffect(() => {
    if (!isTauri()) return;
    let disposed = false; let unlisten: (() => void) | undefined;
    void import('@tauri-apps/api/window').then(async ({ getCurrentWindow }) => {
      const window = getCurrentWindow();
      const stop = await window.onCloseRequested(event => {
        const paths = Object.values(editor.ref.current).filter(draft => draftIsDirty(draft) || draft.saving).map(draft => draft.path);
        if (!paths.length) return;
        event.preventDefault();
        closeGuard.current(paths, () => { unlisten?.(); void window.close(); });
      });
      if (disposed) stop(); else unlisten = stop;
    });
    return () => { disposed = true; unlisten?.(); };
  }, [editor.ref]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-app text-main transition-colors duration-200">
      <Header theme={theme} onToggleTheme={handleToggleTheme} onOpenSettings={() => setSettingsOpen(true)} settingsOpen={settingsOpen} isBusy={!!nativeBusy || (isRunning && !isWatching) || conversionRuntime.busy} />
      {runtimeDialogOpen && <AppDialog title="آماده‌سازی خروجی PDF و Word" description="دریافت موتور تبدیل اختیاری است و فقط با انتخاب شما شروع می‌شود."
        onClose={() => setRuntimeDialogOpen(false)} footer={<>
          <button type="button" className="btn px-3 py-2 rounded-md border border-subtle hover:bg-subtle text-sm" onClick={() => setRuntimeDialogOpen(false)}>ادامهٔ مطالعه</button>
          {conversionRuntime.info.installed && <button type="button" className="btn px-3 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-sm"
            onClick={() => { setRuntimeDialogOpen(false); void handleConvert(); }}>شروع تبدیل</button>}
        </>}><ConversionRuntimePanel runtime={conversionRuntime} isRunning={isRunning} /></AppDialog>}

      {pendingEdits && <AppDialog title="تغییرات ذخیره‌نشده" description={pendingEdits.allowDiscard ? 'پیش از کنارگذاشتن اسناد، تغییرات را ذخیره کنید.' : 'برای تبدیل، ابتدا تغییرات اسناد باید روی دیسک ذخیره شوند.'}
        onClose={() => { if (!savingEdits) setPendingEdits(null); }}
        footer={<>
          <button type="button" disabled={savingEdits} className="btn px-3 py-2 rounded border border-subtle hover:bg-subtle text-sm" onClick={() => setPendingEdits(null)}>انصراف</button>
          {pendingEdits.allowDiscard && <button type="button" disabled={savingEdits} className="btn px-3 py-2 rounded text-red-600 dark:text-red-400 hover:bg-subtle text-sm" onClick={() => { editor.forget(pendingEdits.paths); pendingEdits.next(); setPendingEdits(null); }}>کنارگذاشتن تغییرات</button>}
          <button type="button" disabled={savingEdits} className="btn px-3 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white text-sm" onClick={async () => {
            setSavingEdits(true); setPendingError('');
            try {
              for (const path of pendingEdits.paths) { if (!await editor.save(path)) { setPendingError('ذخیره کامل نشد؛ خطای سند را بررسی کنید. پیش‌نویس‌ها حفظ شدند.'); return; } }
              pendingEdits.next(); setPendingEdits(null);
            } finally { setSavingEdits(false); }
          }}>{savingEdits ? 'در حال ذخیره…' : 'ذخیره و ادامه'}</button>
        </>}>
        <ul className="text-sm text-muted space-y-2">{pendingEdits.paths.map(path => <li key={path} dir="auto" className="break-all">{path.split(/[\\/]/).pop()}</li>)}</ul>
        {pendingError && <p role="alert" className="text-xs text-rose-600 dark:text-rose-400 mt-3 leading-6">{pendingError}</p>}
      </AppDialog>}

      {settingsOpen && <Suspense fallback={null}>
        <SettingsDialog settings={settings} format={options.format} isRunning={isRunning} storageError={storageError} notice={settingsNotice} conversionRuntime={conversionRuntime}
          onChange={changeSettings} onFormatChange={format => { handleOptionChange('format', format); setSettingsNotice(''); }} onClose={() => setSettingsOpen(false)}
          onResetLayout={() => {
            setInspectorCollapsed(false);
            setQueueWidth(queueDefault()); setInspectorWidth(inspectorDefault());
            storeWidth('pane_queue_width_v2', queueDefault()); storeWidth('pane_inspector_width', inspectorDefault());
            setSettingsNotice('عرض پنل‌ها به حالت اولیه برگشت.');
          }}
          onReset={() => {
            setSettings({ ...DEFAULT_APP_SETTINGS }); setOptions({ ...DEFAULT_CONVERT_OPTIONS });
            setSettingsNotice('تنظیمات پیش‌فرض اعمال شد؛ اسناد صف حفظ شدند.');
          }} />
      </Suspense>}
      {confirmClear && <AppDialog title="پاک‌کردن صف" description="همهٔ اسناد از صف کنار گذاشته می‌شوند؛ فایل‌های روی دیسک حفظ می‌شوند." onClose={() => setConfirmClear(false)}
        footer={<>
          <button type="button" onClick={() => setConfirmClear(false)} className="btn px-4 py-2 rounded-md border border-subtle hover:bg-subtle text-sm">انصراف</button>
          <button type="button" onClick={() => { editor.forget(itemsRef.current.map(item => item.path)); clearQueue(); setConfirmClear(false); }} className="btn px-4 py-2 rounded-md bg-red-600 hover:bg-red-700 text-white text-sm">پاک‌کردن همهٔ صف</button>
        </>}>
        <p className="text-sm text-muted">{items.length} سند در صف قرار دارد.</p>
      </AppDialog>}

      <main className="flex-1 flex overflow-hidden relative">
        {/* Zone A: Document Batch Queue (Right-most in RTL) */}
        <section
          style={{ width: `${queueWidth}px` }}
          className="h-full shrink-0 overflow-hidden"
        >
          <QueuePanel
            items={items.map(item => item.unsaved === draftIsDirty(editor.drafts[documentKey(item.path)]) ? item : { ...item, unsaved: draftIsDirty(editor.drafts[documentKey(item.path)]) })}
            selectedIds={selectedIds}
            recursive={options.recursive}
            query={query}
            onQueryChange={setQuery}
            nativeBusy={nativeBusy}
            isConverting={isRunning}
            onRecursiveChange={handleRecursiveToggle}
            onSelect={handleSelectItem}
            onAddFiles={handleAddFiles}
            onPickFilesNative={handlePickFilesNative}
            onAddFolder={handleAddFolder}
            onRemoveSelected={handleRemoveSelected}
            onClearAll={handleClearAll}
            onOpenFile={revealInExplorer}
            onRevealFolder={revealFolderInExplorer}
          />
        </section>

        <PaneSplitter
          onResize={handleResizeQueue}
          value={queueWidth} min={QUEUE_MIN} max={QUEUE_MAX}
          onReset={() => {
            const w = queueDefault();
            setQueueWidth(w);
            storeWidth('pane_queue_width_v2', w);
          }}
          title="تغییر عرض ستون صف (بکشید / دوبار کلیک برای ریست)"
        />

        {/* Workspace Preview & Terminal (center) */}
        <section aria-label="محیط مطالعه" className="flex-1 min-w-0 h-full overflow-hidden">
          <WorkspacePanel
            inspectorOpen={!inspectorCollapsed}
            onToggleInspector={() => setInspectorCollapsed(value => !value)}
            selectedItem={selectedItem}
            markdownContent={markdownContent}
            logs={logs}
            isRunning={isRunning}
            isWatching={isWatching}
            onStopConversion={handleCancel}
            theme={theme}
            activeTab={workspaceTab}
            onTabChange={setWorkspaceTab}
            zoom={zoom}
            onZoomChange={previewZoom => changeSettings({ previewZoom })}
            readingSettings={settings}
            editor={editor}
            onSavedCopy={document => {
              const name = document.path.split(/[\\/]/).pop() || document.path;
              appendItems([{ id: '', path: document.path, name, sizeBytes: document.sizeBytes, sizeStr: `${(document.sizeBytes / 1024).toFixed(1)} KB`, status: 'pending' }], 'نسخهٔ جدید ذخیره شد.', true, true);
            }}
            previewNonce={previewNonce}
            onRefreshPreview={() => setPreviewNonce((n) => n + 1)}
            onClearLogs={handleClearLogs}
            onOpenOutputDir={handleOpenOutputDir}
            onOpenInEditor={revealInExplorer}
            onOpenDocument={(path) => loadDocuments(path, true)}
          />
        </section>
        <PaneSplitter
          onResize={handleResizeInspector}
          value={inspectorCollapsed ? 0 : inspectorWidth} min={0} max={INSPECTOR_MAX}
          growTowards="right"
          onResizeEnd={finishResizeInspector}
          onReset={() => {
            setInspectorCollapsed(false);
            const w = inspectorDefault();
            setInspectorWidth(w);
            storeWidth('pane_inspector_width', w);
          }}
          title="تغییر عرض پنل تنظیمات (بکشید / دوبار کلیک برای ریست)"
        />

        {/* Output Inspector (left) */}
        <section
          id="output-inspector" aria-label="تنظیمات خروجی" inert={inspectorCollapsed}
          style={{ width: inspectorCollapsed ? 0 : `${inspectorWidth}px` }}
          className="h-full shrink-0 overflow-hidden"
        >
          <InspectorPanel
            onClose={() => setInspectorCollapsed(true)}
            options={options}
            isRunning={isRunning}
            isWatching={isWatching}
            hasDocuments={items.length > 0}
            outputDirBusy={nativeBusy === 'output-dir'}
            onOptionsChange={(key, value) => {
              if (key === 'recursive') handleRecursiveToggle(Boolean(value));
              else handleOptionChange(key, value);
            }}
            onConvert={handleConvert}
            onCancel={handleCancel}
            onBrowseOutputDir={handleBrowseOutputDir}
            onOpenOutputDir={handleOpenOutputDir}
            onBrowseFile={handleBrowseFile}
            onBrowseDir={handleBrowseDir}
          />
        </section>

      </main>

      <StatusBar
        statusMessage={conversionRuntime.busy && !isRunning ? `${runtimePhase(conversionRuntime.info.phase)}${['downloading', 'copying'].includes(conversionRuntime.info.phase) && conversionRuntime.info.totalBytes ? `: ${Math.floor(conversionRuntime.info.downloadedBytes * 100 / conversionRuntime.info.totalBytes)}%` : ''}` : statusMessage}
        progressPercent={progressPercent}
        isRunning={isRunning}
        isWatching={isWatching}
        totalItems={items.length}
        completedItems={completedCount}
        conversionReady={conversionRuntime.native ? conversionRuntime.info.installed : undefined}
        onManageConversion={() => setRuntimeDialogOpen(true)}
      />
    </div>
  );
};

export default App;
