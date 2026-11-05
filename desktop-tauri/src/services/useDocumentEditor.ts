import { useCallback, useEffect, useRef, useState } from 'react';
import { documentKey } from './queueState';
import { DocumentFailure, readDocument, writeDocument, type DocumentSnapshot } from './documents';
import { readRecovery, storeRecovery } from './draftRecovery';

export interface EditorDraft extends DocumentSnapshot {
  savedText: string; saving: boolean; error: string; recovered: boolean; recoveryError: boolean; recoveryReady: boolean;
}
export const draftIsDirty = (draft?: EditorDraft) => !!draft && draft.text !== draft.savedText;

export function useDocumentEditor(onSaved: (document: DocumentSnapshot) => void) {
  const [drafts, setDrafts] = useState<Record<string, EditorDraft>>({});
  const ref = useRef(drafts);
  const opened = useRef(new Map<string, Promise<void>>());
  const generations = useRef(new Map<string, number>());
  const saving = useRef(new Map<string, Promise<boolean>>());
  const onSavedRef = useRef(onSaved); onSavedRef.current = onSaved;
  const update = useCallback((fn: (current: Record<string, EditorDraft>) => Record<string, EditorDraft>) => {
    ref.current = fn(ref.current); setDrafts(ref.current);
  }, []);
  const open = useCallback((path: string): Promise<void> => {
    const key = documentKey(path);
    if (ref.current[key]) return Promise.resolve();
    const pending = opened.current.get(key); if (pending) return pending;
    const generation = generations.current.get(key) || 0;
    const task = (async () => {
      const [snapshot, recovery] = await Promise.all([readDocument(path), readRecovery(path).catch(() => undefined)]);
      if ((generations.current.get(key) || 0) !== generation) return;
      const recovered = !!recovery && recovery.text !== snapshot.text;
      update(current => ({ ...current, [key]: { ...snapshot, text: recovered ? recovery.text : snapshot.text,
        revision: recovered ? recovery.revision : snapshot.revision, savedText: snapshot.text, saving: false,
        error: recovered && recovery.revision !== snapshot.revision ? 'نسخهٔ دیسک پس از این پیش‌نویس تغییر کرده؛ با نام دیگر ذخیره کنید یا نسخهٔ دیسک را بازخوانی کنید.' : '',
        recovered, recoveryError: false, recoveryReady: false } }));
    })().finally(() => { if (opened.current.get(key) === task) opened.current.delete(key); });
    opened.current.set(key, task); return task;
  }, [update]);
  const change = useCallback((path: string, text: string) => {
    const key = documentKey(path);
    update(current => {
      const previous = current[key];
      return !previous || previous.text === text ? current : { ...current, [key]: { ...previous, text, recoveryReady: false } };
    });
  }, [update]);
  const save = useCallback((path: string): Promise<boolean> => {
    const key = documentKey(path);
    const pending = saving.current.get(key); if (pending) return pending;
    const submitted = ref.current[key];
    if (submitted?.saving) return Promise.resolve(false);
    if (!submitted || !draftIsDirty(submitted)) return Promise.resolve(true);
    update(current => ({ ...current, [key]: { ...current[key], saving: true, error: '' } }));
    const task = (async () => {
      try {
        const result = await writeDocument(submitted.path, submitted.text, submitted.revision);
        update(current => ({ ...current, [key]: { ...current[key], ...result, text: current[key].text,
          savedText: submitted.text, saving: false, error: '', recovered: false } }));
        onSavedRef.current(result); return true;
      } catch (error) {
        update(current => ({ ...current, [key]: { ...current[key], saving: false, error: String(error instanceof Error ? error.message : error) } }));
        return false;
      }
    })().finally(() => saving.current.delete(key));
    saving.current.set(key, task); return task;
  }, [update]);
  const forget = useCallback((paths: string[]) => {
    update(current => {
      const next = { ...current };
      for (const path of paths) {
        const key = documentKey(path);
        generations.current.set(key, (generations.current.get(key) || 0) + 1);
        opened.current.delete(key);
        if (next[key]) void storeRecovery(path, null).catch(() => {});
        delete next[key];
      }
      return next;
    });
  }, [update]);
  const reload = useCallback(async (path: string) => {
    const snapshot = await readDocument(path); const key = documentKey(path);
    update(current => ({ ...current, [key]: { ...snapshot, savedText: snapshot.text, saving: false, error: '', recovered: false, recoveryError: false, recoveryReady: false } }));
    await storeRecovery(path, null).catch(() => {}); onSavedRef.current(snapshot);
  }, [update]);
  const refreshClean = useCallback(async (path: string) => {
    const key = documentKey(path); const before = ref.current[key];
    if (!before || draftIsDirty(before) || before.saving) return;
    const snapshot = await readDocument(path);
    if (snapshot.revision === before.revision) return;
    const latest = ref.current[key];
    if (!latest || latest.revision !== before.revision || latest.text !== before.text || latest.saving) return;
    update(current => ({ ...current, [key]: { ...snapshot, savedText: snapshot.text, saving: false, error: '', recovered: false, recoveryError: false, recoveryReady: false } }));
    onSavedRef.current(snapshot);
  }, [update]);
  const saveCopy = useCallback(async (path: string, destination: string, revision: string | null) => {
    const key = documentKey(path); const submitted = ref.current[key];
    if (!submitted) throw new DocumentFailure('سند هنوز بارگذاری نشده است.');
    if (submitted.saving) throw new DocumentFailure('ذخیرهٔ دیگری در حال انجام است.');
    update(current => ({ ...current, [key]: { ...current[key], saving: true, error: '' } }));
    try {
      const result = await writeDocument(destination, submitted.text, revision, true);
      if (ref.current[key]?.text === submitted.text) forget([path]);
      update(current => ({ ...current, ...(current[key] ? { [key]: { ...current[key], saving: false } } : {}),
        [documentKey(result.path)]: { ...result, savedText: result.text, saving: false, error: '', recovered: false, recoveryError: false, recoveryReady: false } }));
      return result;
    } catch (error) {
      update(current => current[key] ? { ...current, [key]: { ...current[key], saving: false } } : current);
      throw error;
    }
  }, [forget, update]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      for (const draft of Object.values(ref.current)) {
        if (draft.recoveryReady) continue;
        const text = draft.text;
        void storeRecovery(draft.path, draftIsDirty(draft) ? { path: draft.path, text, revision: draft.revision, updatedAt: Date.now() } : null)
          .then(() => update(current => {
            const key = documentKey(draft.path); const latest = current[key];
            return !latest || latest.text !== text ? current : { ...current, [key]: { ...latest, recoveryReady: true, recoveryError: false } };
          })).catch(() => update(current => {
            const key = documentKey(draft.path); const latest = current[key];
            return !latest || latest.text !== text ? current : { ...current, [key]: { ...latest, recoveryReady: true, recoveryError: true } };
          }));
      }
    }, 400);
    return () => window.clearTimeout(timer);
  }, [drafts, update]);

  const dirtyPaths = Object.values(drafts).filter(draftIsDirty).map(draft => draft.path);
  const needsExitGuard = dirtyPaths.length > 0 || Object.values(drafts).some(draft => draft.saving);
  useEffect(() => {
    if (!needsExitGuard) return;
    const stop = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', stop);
    return () => window.removeEventListener('beforeunload', stop);
  }, [needsExitGuard]);
  return { drafts, ref, open, change, save, forget, reload, refreshClean, saveCopy, dirtyPaths };
}
export type DocumentEditor = ReturnType<typeof useDocumentEditor>;
