/** Keep the same visible block when fullscreen changes the document's line wrapping. */
export function capturePreviewPosition(frame: HTMLIFrameElement | null): (() => void) | undefined {
  const doc = frame?.contentDocument;
  const view = doc?.defaultView;
  const body = doc?.querySelector('.markdown-body');
  if (!view || !body || view.scrollY === 0 || !frame?.getClientRects().length) return;

  const bounds = body.getBoundingClientRect();
  const x = Math.max(1, Math.min(view.innerWidth - 2, bounds.left + bounds.width / 2));
  const block = [18, 45, 75, 110].map(y => doc.elementFromPoint(x, y)
    ?.closest('h1,h2,h3,h4,h5,h6,p,pre,li,table,blockquote,figure,hr'))
    .find(element => element && body.contains(element));
  if (!block) return;
  const top = block.getBoundingClientRect().top;
  return () => {
    if (frame.contentDocument === doc && block.isConnected && frame.getClientRects().length) {
      view.scrollBy(0, block.getBoundingClientRect().top - top);
    }
  };
}
