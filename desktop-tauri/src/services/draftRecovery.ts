import { documentKey } from './queueState';

export interface RecoveryDraft { path: string; text: string; revision: string; updatedAt: number }
let database: Promise<IDBDatabase> | undefined;
function openDatabase(): Promise<IDBDatabase> {
  if (!database) database = new Promise((resolve, reject) => {
    const request = indexedDB.open('mdpersia-edit-recovery', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('drafts');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error('نسخهٔ بازیابی محلی در دسترس نیست.'));
  });
  return database;
}

export async function readRecovery(path: string): Promise<RecoveryDraft | undefined> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('drafts', 'readonly');
    const request = transaction.objectStore('drafts').get(documentKey(path));
    request.onsuccess = () => {
      const draft = request.result;
      resolve(draft && typeof draft.text === 'string' && typeof draft.revision === 'string' && draft.text.length <= 16 * 1024 * 1024 ? draft : undefined);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function storeRecovery(path: string, draft: RecoveryDraft | null): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction('drafts', 'readwrite');
    const records = transaction.objectStore('drafts');
    if (draft) records.put(draft, documentKey(path)); else records.delete(documentKey(path));
    transaction.oncomplete = () => resolve();
    transaction.onabort = transaction.onerror = () => reject(transaction.error);
  });
}
