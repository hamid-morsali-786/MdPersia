import { isMarkdownPath } from './documentFormats';
import { documentKey } from './queueState';

const SESSION_KEY = 'mdpersia.reading-session.v1';
export type ReadingPosition = { x: number; y: number; restoreOnOpen?: boolean };

export function readReadingSession() {
  const positions = new Map<string, ReadingPosition>();
  const paths: string[] = [];
  let activePath: string | null = null;
  try {
    const saved = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
    if (Array.isArray(saved?.documents)) {
      for (const item of saved.documents.slice(0, 10000)) {
        if (typeof item?.path !== 'string' || !isMarkdownPath(item.path) || !/^(?:[a-z]:[\\/]|[\\/])/i.test(item.path)) continue;
        const key = documentKey(item.path);
        if (positions.has(key)) continue;
        paths.push(item.path);
        const x = Number.isFinite(item.x) ? item.x : 0;
        const y = Number.isFinite(item.y) ? Math.max(0, item.y) : 0;
        positions.set(key, { x, y });
      }
    }
    if (typeof saved?.activePath === 'string') activePath = saved.activePath;
  } catch { /* An unavailable or unreadable session does not block startup. */ }
  return { paths, positions, activePath };
}

export function writeReadingSession(paths: string[], activePath: string | null, positions: Map<string, ReadingPosition>) {
  try {
    if (!paths.length) localStorage.removeItem(SESSION_KEY);
    else localStorage.setItem(SESSION_KEY, JSON.stringify({
      activePath,
      documents: paths.map(path => {
        const position = positions.get(documentKey(path));
        return { path, x: position?.x, y: position?.y };
      }),
    }));
  } catch { /* Reading and editing remain available when storage is full. */ }
}
