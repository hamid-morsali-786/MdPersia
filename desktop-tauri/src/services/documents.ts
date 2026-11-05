import { isTauri } from './tauriBridge';

export interface DocumentSnapshot {
  path: string; text: string; revision: string; encoding: string; newline: string; sizeBytes: number; readOnly: boolean;
}
export class DocumentFailure extends Error {
  constructor(message: string, readonly code = 'IO') { super(message); }
}

async function operation(request: Record<string, unknown>): Promise<DocumentSnapshot> {
  let reply;
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    reply = await invoke<{ document?: DocumentSnapshot; error?: string; code?: string }>('document_io', { request });
  } else {
    const response = await fetch('/api/document', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) });
    reply = await response.json();
  }
  if (!reply.document) throw new DocumentFailure(reply.error || 'عملیات فایل انجام نشد.', reply.code);
  return reply.document;
}

export const readDocument = (path: string) => operation({ operation: 'read', path });
export const writeDocument = (path: string, text: string, revision: string | null, utf8 = false) => operation({ operation: 'save', path, text, revision, utf8 });

export async function pickSaveMarkdown(defaultPath: string): Promise<string | null> {
  if (isTauri()) {
    const { save } = await import('@tauri-apps/plugin-dialog');
    return save({ defaultPath, title: 'ذخیره با نام دیگر', filters: [{ name: 'Markdown', extensions: ['md', 'markdown'] }] });
  }
  const response = await fetch(`/api/pick-save-file?defaultPath=${encodeURIComponent(defaultPath)}`);
  const result = await response.json();
  if (result.error) throw new DocumentFailure(result.error);
  return result.cancelled ? null : result.path || null;
}
