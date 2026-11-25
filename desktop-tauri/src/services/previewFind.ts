const MATCH_LIMIT = 2000;
const TEXT_BLOCK = 'p,li,dt,dd,h1,h2,h3,h4,h5,h6,td,th,pre,blockquote,div,section,figcaption';
const foldPersian = (text: string) => text.replace(/[يى]/g, 'ی').replace(/ك/g, 'ک');

/** Search rendered text across inline markup, without mutating the document or its selection. */
export function findPreviewMatches(doc: Document, query: string) {
  const root = doc.querySelector('.markdown-body');
  const term = foldPersian(query.trim());
  const ranges: Range[] = [];
  if (!root || !term) return { ranges, capped: false };

  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+');
  const pattern = new RegExp(escaped, 'giu');
  const view = doc.defaultView;
  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, node => {
    if (node.nodeType !== Node.ELEMENT_NODE) return NodeFilter.FILTER_ACCEPT;
    const element = node as Element;
    if (element.matches('script,style,template,[hidden],[aria-hidden="true"]') || view?.getComputedStyle(element).display === 'none') return NodeFilter.FILTER_REJECT;
    return element.localName === 'br' ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
  });
  let block: Element | null = null;
  let pieces: { node: Text; start: number }[] = [];
  let chunks: string[] = [];
  let length = 0;
  const searchBlock = () => {
    let first = 0;
    let last = 0;
    const text = foldPersian(chunks.join(''));
    pattern.lastIndex = 0;
    for (let match = pattern.exec(text); match; match = pattern.exec(text)) {
      if (ranges.length === MATCH_LIMIT) return true;
      const end = match.index + match[0].length;
      while (pieces[first + 1]?.start <= match.index) first++;
      last = Math.max(last, first);
      while (pieces[last + 1]?.start < end) last++;
      const range = doc.createRange();
      range.setStart(pieces[first].node, match.index - pieces[first].start);
      range.setEnd(pieces[last].node, end - pieces[last].start);
      ranges.push(range);
    }
    return false;
  };
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const nextBlock = node.parentElement?.closest(TEXT_BLOCK) ?? root;
    if (nextBlock !== block) {
      if (searchBlock()) return { ranges, capped: true };
      block = nextBlock;
      pieces = [];
      chunks = [];
      length = 0;
    }
    if (node.nodeType === Node.ELEMENT_NODE) {
      chunks.push('\n');
      length++;
    } else if ((node as Text).length) {
      const text = node as Text;
      pieces.push({ node: text, start: length });
      chunks.push(text.data);
      length += text.length;
    }
  }
  return { ranges, capped: searchBlock() };
}

export function highlightPreviewMatches(doc: Document, ranges: Range[], active: Range | undefined) {
  const view = doc.defaultView as (Window & typeof globalThis) | null;
  if (!view?.CSS.highlights || !view.Highlight) return;
  const registry = view.CSS.highlights;
  registry.delete('mdpersia-find');
  registry.delete('mdpersia-find-active');
  if (!active) return;
  registry.set('mdpersia-find', new view.Highlight(...ranges));
  const current = new view.Highlight(active);
  current.priority = 1;
  registry.set('mdpersia-find-active', current);
}

/** A hit inside a long code line or table must be reachable in both directions. */
export function revealPreviewMatch(doc: Document, match: Range) {
  const view = doc.defaultView;
  if (!view) return;
  for (let element = match.startContainer.parentElement; element; element = element.parentElement) {
    if (element.localName === 'details' && !element.querySelector(':scope > summary')?.contains(match.startContainer)) {
      (element as HTMLDetailsElement).open = true;
    }
  }
  for (let element = match.startContainer.parentElement; element && element !== doc.body; element = element.parentElement) {
    if (element.scrollWidth <= element.clientWidth + 1 || !/auto|scroll/.test(view.getComputedStyle(element).overflowX)) continue;
    const rect = match.getBoundingClientRect();
    const bounds = element.getBoundingClientRect();
    const zoom = bounds.width / (element.offsetWidth || bounds.width) || 1;
    if (rect.left < bounds.left) element.scrollBy((rect.left - bounds.left - 12) / zoom, 0);
    else if (rect.right > bounds.right) element.scrollBy((rect.right - bounds.right + 12) / zoom, 0);
  }
  const rect = match.getBoundingClientRect();
  if (rect.top < 64 || rect.bottom > view.innerHeight - 32) view.scrollBy(0, rect.top - view.innerHeight / 3);
}
