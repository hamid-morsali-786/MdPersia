import React, { useState, useEffect, useCallback } from 'react';
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
} from './services/tauriBridge';
import { Header } from './components/Header';
import { StatusBar } from './components/StatusBar';
import { QueuePanel } from './components/QueuePanel';
import { InspectorPanel } from './components/InspectorPanel';
import { WorkspacePanel } from './components/WorkspacePanel';
import { PaneSplitter } from './components/PaneSplitter';

const INITIAL_ITEMS: QueueItem[] = [
  {
    id: 'item-1',
    name: 'README.md',
    path: 'E:/project/fa-md-pdf-project/README.md',
    sizeBytes: 15420,
    sizeStr: '15.1 KB',
    status: 'pending',
    relativePath: 'README.md',
  },
  {
    id: 'item-2',
    name: 'architecture.md',
    path: 'E:/project/fa-md-pdf-project/docs/architecture.md',
    sizeBytes: 8320,
    sizeStr: '8.1 KB',
    status: 'pending',
    relativePath: 'docs/architecture.md',
  },
];

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    try {
      const saved = localStorage.getItem('theme');
      return saved === 'light' || saved === 'dark' ? saved : 'dark';
    } catch {
      return 'dark';
    }
  });

  // Resizable column widths in pixels
  const [queueWidth, setQueueWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('pane_queue_width');
      return saved ? parseInt(saved, 10) : 340;
    } catch {
      return 340;
    }
  });

  const [inspectorWidth, setInspectorWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('pane_inspector_width');
      return saved ? parseInt(saved, 10) : 400;
    } catch {
      return 400;
    }
  });

  const [items, setItems] = useState<QueueItem[]>(INITIAL_ITEMS);
  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(['item-1']));
  const [options, setOptions] = useState<ConvertOptions>(DEFAULT_CONVERT_OPTIONS);
  const [markdownContent, setMarkdownContent] = useState<string>('');
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'init-1',
      timestamp: '16:50:00',
      level: 'info',
      message: 'محیط کاری fa-md-pdf با موتور تبدیل واقعی آماده به کار است.',
    },
  ]);
  const [isRunning, setIsRunning] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [statusMessage, setStatusMessage] = useState('آماده به کار');

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    try {
      localStorage.setItem('theme', theme);
    } catch {
      // Ignore
    }
  }, [theme]);

  const selectedItem = items.find((it) => selectedIds.has(it.id)) || null;

  // Load preview content whenever selected item changes
  useEffect(() => {
    if (selectedItem?.path) {
      readFileContent(selectedItem.path).then((text) => {
        setMarkdownContent(text);
      });
    } else {
      setMarkdownContent('');
    }
  }, [selectedItem?.path]);

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleResizeQueue = useCallback((delta: number) => {
    setQueueWidth((prev) => {
      const next = Math.max(220, Math.min(650, prev + delta));
      try {
        localStorage.setItem('pane_queue_width', String(next));
      } catch {
        // Ignore
      }
      return next;
    });
  }, []);

  const handleResizeInspector = useCallback((delta: number) => {
    setInspectorWidth((prev) => {
      const next = Math.max(280, Math.min(750, prev + delta));
      try {
        localStorage.setItem('pane_inspector_width', String(next));
      } catch {
        // Ignore
      }
      return next;
    });
  }, []);

  const handleOptionChange = <K extends keyof ConvertOptions>(
    key: K,
    value: ConvertOptions[K]
  ) => {
    setOptions((prev) => ({ ...prev, [key]: value }));
  };

  /**
   * Reactively update items queue when recursive option toggles.
   */
  const handleRecursiveToggle = async (newRecursive: boolean) => {
    setOptions((prev) => ({ ...prev, recursive: newRecursive }));

    // If a folder was loaded, re-scan and update queue reactively
    if (activeFolder) {
      const scanned = await scanFolder(activeFolder, newRecursive);
      const newItems: QueueItem[] = scanned.map((f, idx) => ({
        id: `scanned-${Date.now()}-${idx}`,
        name: f.name,
        path: f.path,
        sizeBytes: f.sizeBytes,
        sizeStr: `${(f.sizeBytes / 1024).toFixed(1)} KB`,
        status: 'pending',
        relativePath: f.relativePath,
      }));
      setItems(newItems);
      if (newItems.length > 0) {
        setSelectedIds(new Set([newItems[0].id]));
      }
      setStatusMessage(
        newRecursive
          ? `پیمایش بازگشتی فعال شد: ${newItems.length} سند در صف (شامل زیرپوشه‌ها)`
          : `پیمایش زیرپوشه‌ها غیرفعال شد: ${newItems.length} سند در صف (فقط پوشه اصلی)`
      );
    } else if (items.length > 0) {
      // Filter existing items if they have relative paths with subdirectories
      if (!newRecursive) {
        setItems((prev) =>
          prev.filter((it) => !it.relativePath || !it.relativePath.includes('/'))
        );
      }
    }
  };

  const handleSelectItem = (id: string, e: React.MouseEvent) => {
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
    const newItems: QueueItem[] = Array.from(files).map((file, idx) => ({
      id: `file-${Date.now()}-${idx}`,
      name: file.name,
      path: (file as File & { path?: string }).path || file.name,
      sizeBytes: file.size,
      sizeStr: `${(file.size / 1024).toFixed(1)} KB`,
      status: 'pending',
    }));
    setItems((prev) => [...prev, ...newItems]);
  };

  const handlePickFilesNative = async () => {
    const files = await pickFiles(['md', 'markdown']);
    if (files.length === 0) return;
    const newItems: QueueItem[] = files.map((f, idx) => ({
      id: `native-${Date.now()}-${idx}`,
      name: f.name,
      path: f.path,
      sizeBytes: f.sizeBytes,
      sizeStr: f.sizeStr,
      status: 'pending',
      relativePath: f.name,
    }));
    setItems((prev) => [...prev, ...newItems]);
    setStatusMessage(`${files.length} فایل از ویندوز به صف افزوده شد.`);
  };

  const handleAddFolder = async () => {
    const folder = await pickDirectory('انتخاب پوشه حاوی اسناد');
    if (!folder) return;
    setActiveFolder(folder);
    const scanned = await scanFolder(folder, options.recursive);
    if (scanned.length > 0) {
      const newItems: QueueItem[] = scanned.map((f, idx) => ({
        id: `scanned-${Date.now()}-${idx}`,
        name: f.name,
        path: f.path,
        sizeBytes: f.sizeBytes,
        sizeStr: `${(f.sizeBytes / 1024).toFixed(1)} KB`,
        status: 'pending',
        relativePath: f.relativePath,
      }));
      setItems(newItems);
      setSelectedIds(new Set([newItems[0].id]));
      setStatusMessage(`${scanned.length} سند مارک‌داون از پوشه اضافه شدند.`);
    } else {
      setStatusMessage('پوشه انتخاب شد اما فایل مارک‌داونی در آن یافت نشد.');
    }
  };

  const handleBrowseOutputDir = async () => {
    const dir = await pickDirectory('انتخاب پوشه خروجی اسناد');
    if (dir) {
      setOptions((prev) => ({ ...prev, outputDir: dir }));
      setStatusMessage(`پوشه خروجی تنظیم شد: ${dir}`);
    }
  };

  const handleOpenOutputDir = async () => {
    const target =
      options.outputDir ||
      activeFolder ||
      (items.length > 0 ? items[0].path.replace(/[\\/][^\\/]+$/, '') : 'E:/project/fa-md-pdf-project');
    await openInExplorer(target);
    setStatusMessage(`پوشه در ویندوز اکسپلورر باز شد.`);
  };

  const handleBrowseFile = async (key: keyof ConvertOptions, filter?: string) => {
    const exts = filter ? filter.split(',') : undefined;
    const files = await pickFiles(exts);
    if (files.length > 0) {
      setOptions((prev) => ({ ...prev, [key]: files[0].path }));
    }
  };

  const handleBrowseDir = async (key: keyof ConvertOptions) => {
    const dir = await pickDirectory();
    if (dir) {
      setOptions((prev) => ({ ...prev, [key]: dir }));
    }
  };

  const handleRemoveSelected = () => {
    setItems((prev) => prev.filter((it) => !selectedIds.has(it.id)));
    setSelectedIds(new Set());
  };

  const handleClearAll = () => {
    setItems([]);
    setSelectedIds(new Set());
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleConvert = async () => {
    if (items.length === 0 || isRunning) return;
    setIsRunning(true);
    setProgressPercent(0);
    setCompletedCount(0);
    setStatusMessage(`درحال تبدیل ${items.length} سند با موتور fa-md-pdf...`);

    // Reset status to pending
    setItems((prev) => prev.map((it) => ({ ...it, status: 'pending', error: undefined })));

    await executeConversion(
      items,
      options,
      (evt: ProgressEvent) => {
        if (evt.type === 'progress') {
          const comp = evt.completed || 0;
          const tot = evt.total || items.length;
          setCompletedCount(comp);
          setProgressPercent(Math.round((comp / tot) * 100));
          if (evt.file) {
            setItems((prev) =>
              prev.map((it) => (it.name === evt.file ? { ...it, status: 'running' } : it))
            );
          }
        } else if (evt.type === 'success') {
          if (evt.file) {
            setItems((prev) =>
              prev.map((it) => (it.name === evt.file ? { ...it, status: 'success' } : it))
            );
          }
        } else if (evt.type === 'error') {
          if (evt.file) {
            setItems((prev) =>
              prev.map((it) =>
                it.name === evt.file ? { ...it, status: 'error', error: evt.error } : it
              )
            );
          }
        } else if (evt.type === 'done') {
          setProgressPercent(100);
          const succ = evt.completed ?? 0;
          const tot = evt.total ?? items.length;
          setStatusMessage(`فرآیند تبدیل پایان یافت: ${succ} موفق، ${tot - succ} ناموفق.`);
        } else if (evt.type === 'cancelled') {
          setStatusMessage('عملیات تبدیل توسط کاربر لغو گردید.');
        }
      },
      (log: LogEntry) => {
        setLogs((prev) => [...prev, log]);
      }
    );

    setIsRunning(false);
  };

  const handleCancel = () => {
    cancelActiveConversion();
    setIsRunning(false);
    setStatusMessage('توقف درخواست شد.');
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-app text-main transition-colors duration-200">
      <Header theme={theme} onToggleTheme={handleToggleTheme} />

      <main className="flex-1 flex overflow-hidden relative">
        {/* Zone A: Document Batch Queue (Right-most in RTL) */}
        <section
          style={{ width: `${queueWidth}px` }}
          className="h-full shrink-0 overflow-hidden"
        >
          <QueuePanel
            items={items}
            selectedIds={selectedIds}
            recursive={options.recursive}
            onRecursiveChange={handleRecursiveToggle}
            onSelect={handleSelectItem}
            onAddFiles={handleAddFiles}
            onPickFilesNative={handlePickFilesNative}
            onAddFolder={handleAddFolder}
            onRemoveSelected={handleRemoveSelected}
            onClearAll={handleClearAll}
            onOpenFile={(path) => openInExplorer(path)}
            onRevealFolder={(path) => openInExplorer(path.replace(/[\\/][^\\/]+$/, ''))}
          />
        </section>

        {/* Resizer Splitter between Zone A and Zone B */}
        <PaneSplitter
          onResize={handleResizeQueue}
          onReset={() => {
            setQueueWidth(340);
            try { localStorage.setItem('pane_queue_width', '340'); } catch {}
          }}
          title="تغییر عرض ستون صف (بکشید / دوبار کلیک برای ریست)"
        />

        {/* Zone B: 5-Tab Parameters Inspector (Middle in RTL) */}
        <section
          style={{ width: `${inspectorWidth}px` }}
          className="h-full shrink-0 overflow-hidden"
        >
          <InspectorPanel
            options={options}
            isRunning={isRunning}
            onOptionsChange={(key, value) => {
              if (key === 'recursive') {
                handleRecursiveToggle(Boolean(value));
              } else {
                handleOptionChange(key, value);
              }
            }}
            onConvert={handleConvert}
            onCancel={handleCancel}
            onBrowseOutputDir={handleBrowseOutputDir}
            onOpenOutputDir={handleOpenOutputDir}
            onBrowseFile={handleBrowseFile}
            onBrowseDir={handleBrowseDir}
          />
        </section>

        {/* Resizer Splitter between Zone B and Zone C */}
        <PaneSplitter
          onResize={handleResizeInspector}
          onReset={() => {
            setInspectorWidth(400);
            try { localStorage.setItem('pane_inspector_width', '400'); } catch {}
          }}
          title="تغییر عرض پنل تنظیمات (بکشید / دوبار کلیک برای ریست)"
        />

        {/* Zone C: Workspace Preview & Terminal (Left-most in RTL) */}
        <section className="flex-1 min-w-[280px] h-full overflow-hidden">
          <WorkspacePanel
            selectedItem={selectedItem}
            markdownContent={markdownContent}
            logs={logs}
            isRunning={isRunning}
            onClearLogs={handleClearLogs}
            onOpenOutputDir={handleOpenOutputDir}
            onOpenInEditor={(path) => openInExplorer(path)}
          />
        </section>
      </main>

      <StatusBar
        statusMessage={statusMessage}
        progressPercent={progressPercent}
        isRunning={isRunning}
        totalItems={items.length}
        completedItems={completedCount}
      />
    </div>
  );
};

export default App;
