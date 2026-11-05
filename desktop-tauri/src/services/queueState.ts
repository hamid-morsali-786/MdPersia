import type { QueueItem } from '../types';

/** Windows paths are case insensitive; a basename is never a document identity. */
export function documentKey(path: string): string {
  const normalized = path.replace(/\\/g, '/').replace(/\/$/, '');
  return /^[a-z]:\//i.test(normalized) || normalized.startsWith('//')
    ? normalized.toLowerCase() : normalized;
}

export function mergeQueueItems(current: QueueItem[], incoming: QueueItem[]) {
  const items = [...current];
  const positions = new Map(items.map((item, index) => [documentKey(item.path), index]));
  let focusedId: string | null = null;
  let added = 0;
  for (const item of incoming) {
    const key = documentKey(item.path);
    const index = positions.get(key);
    if (index === undefined) {
      const next = { ...item, id: `document:${key}` };
      positions.set(key, items.length);
      items.push(next);
      focusedId = next.id;
      added++;
    } else {
      const previous = items[index];
      items[index] = { ...previous, ...item, id: previous.id,
        status: previous.status, error: previous.error };
      focusedId = previous.id;
    }
  }
  return { items, focusedId, added };
}

export function removeQueueItems(items: QueueItem[], removed: Set<string>, activeId: string | null) {
  const index = items.findIndex(item => item.id === activeId);
  const remaining = items.filter(item => !removed.has(item.id));
  const active = remaining.find(item => item.id === activeId)
    ?? remaining[Math.min(Math.max(0, index), remaining.length - 1)];
  return { items: remaining, activeId: active?.id ?? null };
}

export function linkedMarkdownPath(source: string, href: string): string | null {
  let target = href.split('#')[0].split('?')[0];
  if (!target || /^(https?:|mailto:|javascript:|data:)/i.test(target)) return null;
  try { target = decodeURIComponent(target); } catch { return null; }
  if (target.startsWith('file:')) {
    try { const url = new URL(target); target = url.hostname ? `//${url.hostname}${url.pathname}` : url.pathname.replace(/^\/([a-z]:)/i, '$1'); }
    catch { return null; }
  }
  if (!/\.(md|markdown)$/i.test(target)) return null;
  const current = source.replace(/\\/g, '/');
  target = target.replace(/\\/g, '/');
  if (!target.startsWith('/') && !/^[a-z]:\//i.test(target)) target = current.slice(0, current.lastIndexOf('/') + 1) + target;
  const prefix = target.startsWith('//') ? '//' : target.startsWith('/') ? '/' : '';
  const parts: string[] = [];
  for (const part of target.split('/')) {
    if (!part || part === '.') continue;
    if (part === '..') parts.pop(); else parts.push(part);
  }
  return prefix + parts.join('/');
}
