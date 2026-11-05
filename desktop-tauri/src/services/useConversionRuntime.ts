import { useCallback, useEffect, useRef, useState } from 'react';
import { isTauri } from './tauriBridge';

export interface ConversionRuntimeInfo {
  installed: boolean; phase: string; downloadedBytes: number; totalBytes: number;
  version: string; downloadUrl: string; sha256: string; directory: string; error: string | null;
}
const BUSY = new Set(['starting', 'selecting', 'downloading', 'copying', 'verifying', 'installing', 'cancelling', 'removing']);
const initial = (): ConversionRuntimeInfo => ({ installed: !isTauri(), phase: isTauri() ? 'checking' : 'ready',
  downloadedBytes: 0, totalBytes: 0, version: '', downloadUrl: '', sha256: '', directory: '', error: null });

export function useConversionRuntime() {
  const [info, setInfo] = useState(initial);
  const mounted = useRef(true);
  const cancelled = useRef(false);
  const refresh = useCallback(async (): Promise<ConversionRuntimeInfo> => {
    if (!isTauri()) return initial();
    const { invoke } = await import('@tauri-apps/api/core');
    const value = await invoke<ConversionRuntimeInfo>('conversion_runtime_status');
    if (mounted.current) setInfo(value);
    return value;
  }, []);
  useEffect(() => {
    mounted.current = true;
    if (!isTauri()) return;
    let disposed = false; let stop: (() => void) | undefined;
    void (async () => {
      const { listen } = await import('@tauri-apps/api/event');
      const { invoke } = await import('@tauri-apps/api/core');
      const dispose = await listen<ConversionRuntimeInfo>('conversion-runtime-progress', event => {
        if (disposed) return;
        setInfo(event.payload);
        // A stop clicked before Rust starts the transfer must not be lost.
        if (cancelled.current && BUSY.has(event.payload.phase) && event.payload.phase !== 'cancelling') {
          void invoke('conversion_runtime_cancel').catch(() => {});
        }
      });
      if (disposed) dispose(); else stop = dispose;
      if (!disposed) await refresh();
    })().catch(error => { if (!disposed) setInfo(value => ({ ...value, phase: 'error', error: String(error) })); });
    return () => { disposed = true; mounted.current = false; stop?.(); };
  }, [refresh]);
  const fail = useCallback((error: unknown) => {
    if (mounted.current) setInfo(value => ({ ...value, phase: 'error', error: String(error) }));
  }, []);
  const install = useCallback(async (sourcePath: string | null = null) => {
    cancelled.current = false;
    setInfo(value => ({ ...value, phase: 'starting', downloadedBytes: 0, error: null }));
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const value = await invoke<ConversionRuntimeInfo>('conversion_runtime_install', { sourcePath });
      if (mounted.current) setInfo(value);
    } catch (error) {
      try { const value = await refresh(); if (value.phase === 'cancelled') return; } catch { /* Use the original error. */ }
      fail(error);
    }
  }, [refresh, fail]);
  const importFile = useCallback(async () => {
    setInfo(value => ({ ...value, phase: 'selecting', error: null }));
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const path = await open({ multiple: false, directory: false, title: 'انتخاب بستهٔ تبدیل MdPersia',
        filters: [{ name: 'MdPersia conversion package', extensions: ['zip'] }] });
      if (typeof path === 'string') await install(path); else await refresh();
    } catch (error) { fail(error); }
  }, [install, refresh, fail]);
  const cancel = useCallback(async () => {
    cancelled.current = true;
    setInfo(value => ({ ...value, phase: 'cancelling' }));
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const value = await invoke<ConversionRuntimeInfo>('conversion_runtime_cancel');
      if (mounted.current) setInfo(value);
    } catch (error) { fail(error); }
  }, [fail]);
  const remove = useCallback(async () => {
    setInfo(value => ({ ...value, phase: 'removing', error: null }));
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const value = await invoke<ConversionRuntimeInfo>('conversion_runtime_remove');
      if (mounted.current) setInfo(value);
    } catch (error) { fail(error); }
  }, [fail]);
  return { info, native: isTauri(), busy: BUSY.has(info.phase), refresh, install, importFile, cancel, remove };
}
export type ConversionRuntime = ReturnType<typeof useConversionRuntime>;
