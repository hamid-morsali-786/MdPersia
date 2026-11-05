/**
 * Browser-side single instance.
 *
 * The Tauri shell gets this from the native single-instance plugin. On the Vite /
 * browser runtime a second launch is a second tab, so the file is handed over with a
 * BroadcastChannel instead of a process IPC.
 */

const CHANNEL = 'mdpersia:instance';
const ANSWER_TIMEOUT_MS = 250;

type Message =
  | { type: 'who-is-there'; from: string }
  | { type: 'i-am-here'; from: string; to: string }
  | { type: 'open-file'; from: string; path: string };

/** One id per page: two channel objects in the same tab must not answer each other. */
const self = Math.random().toString(36).slice(2);

function connect(): BroadcastChannel | null {
  try {
    return typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(CHANNEL);
  } catch {
    return null;
  }
}

/** Accept files handed over by a later launch. Returns a disposer. */
export function listenForHandoffs(handler: (path: string) => void): () => void {
  const ch = connect();
  if (!ch) return () => {};
  ch.onmessage = (e: MessageEvent<Message>) => {
    const msg = e.data;
    if (!msg || msg.from === self) return;
    if (msg.type === 'who-is-there') {
      ch.postMessage({ type: 'i-am-here', from: self, to: msg.from } satisfies Message);
    } else if (msg.type === 'open-file' && typeof msg.path === 'string') {
      handler(msg.path);
    }
  };
  return () => {
    try {
      ch.close();
    } catch {
      // already closed
    }
  };
}

/**
 * Ask an already-open instance to take the file.
 * Resolves true only when another instance answered and the file was delivered.
 */
export async function handOffToRunningInstance(path: string): Promise<boolean> {
  const ch = connect();
  if (!ch) return false;
  try {
    const answered = new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => resolve(false), ANSWER_TIMEOUT_MS);
      ch.onmessage = (e: MessageEvent<Message>) => {
        const msg = e.data;
        if (msg?.type === 'i-am-here' && msg.to === self && msg.from !== self) {
          clearTimeout(timer);
          resolve(true);
        }
      };
    });
    ch.postMessage({ type: 'who-is-there', from: self } satisfies Message);
    if (!(await answered)) return false;
    ch.postMessage({ type: 'open-file', from: self, path } satisfies Message);
    return true;
  } finally {
    try {
      ch.close();
    } catch {
      // already closed
    }
  }
}
