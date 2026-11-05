import { useEffect, useRef } from 'react';
import { Compartment, EditorSelection, EditorState } from '@codemirror/state';
import { EditorView, keymap, highlightSpecialChars, Decoration, ViewPlugin } from '@codemirror/view';
import { defaultKeymap, history, historyKeymap, undo, redo } from '@codemirror/commands';
import { markdown } from '@codemirror/lang-markdown';
import { defaultHighlightStyle, HighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { tags } from '@lezer/highlight';
import { searchKeymap, openSearchPanel } from '@codemirror/search';
import { Bold, Italic, Heading2, Link, Code2, Undo2, Redo2, Search } from 'lucide-react';
import { Tooltip } from '../Tooltip';

const darkHighlightStyle = HighlightStyle.define([
  { tag: tags.heading, color: '#93c5fd', fontWeight: '600' },
  { tag: tags.strong, fontWeight: '700' }, { tag: tags.emphasis, fontStyle: 'italic' },
  { tag: tags.keyword, color: '#c4b5fd' },
  { tag: [tags.string, tags.url, tags.link], color: '#86efac' },
  { tag: [tags.comment, tags.meta, tags.processingInstruction], color: '#94a3b8' },
  { tag: [tags.number, tags.bool], color: '#fcd34d' },
  { tag: tags.monospace, color: '#e2e8f0' },
]);

const lineDirections = ViewPlugin.define(view => {
  const decorate = (editor: EditorView) => {
    const marks = []; const seen = new Set<number>();
    for (const range of editor.visibleRanges) {
      for (let line = editor.state.doc.lineAt(range.from); line.from <= range.to; ) {
        if (!seen.has(line.from)) { marks.push(Decoration.line({ attributes: { dir: 'auto' } }).range(line.from)); seen.add(line.from); }
        if (line.to >= editor.state.doc.length) break;
        line = editor.state.doc.lineAt(line.to + 1);
      }
    }
    return Decoration.set(marks, true);
  };
  return { decorations: decorate(view), update(update) { if (update.docChanged || update.viewportChanged) this.decorations = decorate(update.view); } };
}, { decorations: plugin => plugin.decorations });

export default function MarkdownEditor({ path, text, theme, readOnly, onChange, onSave }: {
  path: string; text: string; theme: 'light' | 'dark'; readOnly: boolean;
  onChange: (value: string) => void; onSave: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const states = useRef(new Map<string, EditorState>());
  const callbacks = useRef({ onChange, onSave }); callbacks.current = { onChange, onSave };
  const appearance = useRef(new Compartment());
  const editable = useRef(new Compartment());
  const wrap = (before: string, after = before, placeholder = 'متن') => {
    const editor = view.current; if (!editor || editor.state.readOnly) return false;
    const { from, to } = editor.state.selection.main;
    const selected = editor.state.sliceDoc(from, to) || placeholder;
    editor.dispatch({ changes: { from, to, insert: before + selected + after },
      selection: EditorSelection.range(from + before.length, from + before.length + selected.length), userEvent: 'input' });
    editor.focus(); return true;
  };
  const themeExtension = (dark: boolean) => [EditorView.theme({
    '&': { height: '100%', color: 'var(--text-main)', backgroundColor: 'var(--bg-card)', fontSize: '14px' },
    '.cm-scroller': { overflow: 'auto', fontFamily: '"Vazirmatn", Consolas, monospace', lineHeight: '1.9' },
    '.cm-content': { padding: '14px 18px', caretColor: 'var(--text-main)', userSelect: 'text' },
    // Let each line's dir=auto use the same isolated paragraph direction read by CodeMirror.
    '.cm-line': { unicodeBidi: 'isolate', textAlign: 'start' },
    '&.cm-focused': { outline: 'none' },
    '.cm-content::selection, .cm-content ::selection': { backgroundColor: dark ? '#26416a' : '#c7ddff' },
    '.cm-panels': { color: 'var(--text-main)', background: 'var(--bg-surface)', fontFamily: 'var(--font-sans)' },
    '.cm-searchMatch': { backgroundColor: dark ? '#675120' : '#fef08a' },
    '.cm-search input': { color: 'var(--text-main)', background: 'var(--input-bg)', border: '1px solid var(--border-subtle)', padding: '4px', maxWidth: '100%' },
    '.cm-search button': { color: 'var(--text-main)', background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', padding: '4px 8px' },
  }, { dark }), syntaxHighlighting(dark ? darkHighlightStyle : defaultHighlightStyle)];

  useEffect(() => {
    const cached = states.current.get(path);
    const state = cached?.doc.toString() === text ? cached : EditorState.create({ doc: text, extensions: [
      // Use the browser's primary caret/selection so glyph shaping and the caret share one layout.
      history(), highlightSpecialChars(), EditorView.lineWrapping,
      EditorView.perLineTextDirection.of(true), lineDirections, markdown(),
      EditorState.phrases.of({ 'Find': 'جستجو', 'Replace': 'جایگزینی', 'next': 'بعدی', 'previous': 'قبلی', 'all': 'همه', 'match case': 'تطبیق حروف', 'regexp': 'عبارت منظم', 'by word': 'کلمهٔ کامل', 'replace': 'جایگزین', 'replace all': 'جایگزینی همه', 'close': 'بستن' }),
      EditorView.contentAttributes.of({ 'aria-label': 'ویرایش متن Markdown', dir: 'ltr', spellcheck: 'false' }),
      appearance.current.of(themeExtension(theme === 'dark')), editable.current.of([EditorState.readOnly.of(readOnly), EditorView.editable.of(!readOnly)]),
      keymap.of([{ key: 'Mod-s', run: () => { callbacks.current.onSave(); return true; } },
        { key: 'Mod-Shift-z', run: redo, preventDefault: true },
        { key: 'Mod-b', run: () => wrap('**') }, { key: 'Mod-i', run: () => wrap('*') },
        { key: 'Mod-k', run: () => wrap('[', '](https://example.com)', 'عنوان پیوند') }, ...historyKeymap, ...searchKeymap, ...defaultKeymap]),
      EditorView.updateListener.of(update => { if (update.docChanged) callbacks.current.onChange(update.state.doc.toString()); }),
    ] });
    const editor = new EditorView({ state, parent: host.current! });
    view.current = editor; editor.focus();
    const remeasure = () => editor.requestMeasure();
    document.fonts.addEventListener('loadingdone', remeasure);
    return () => {
      document.fonts.removeEventListener('loadingdone', remeasure);
      states.current.set(path, editor.state); editor.destroy(); view.current = null;
    };
    // Each document owns its undo history; ordinary typing must never recreate the editor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);
  useEffect(() => {
    const editor = view.current;
    if (editor && editor.state.doc.toString() !== text) editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: text } });
  }, [text]);
  useEffect(() => { view.current?.dispatch({ effects: appearance.current.reconfigure(themeExtension(theme === 'dark')) }); }, [theme, path]);
  useEffect(() => { view.current?.dispatch({ effects: editable.current.reconfigure([EditorState.readOnly.of(readOnly), EditorView.editable.of(!readOnly)]) }); }, [readOnly, path]);
  return <div className="markdown-editor flex flex-col h-full min-h-0">
    <div role="toolbar" aria-label="قالب‌بندی متن" className="editor-format-bar flex items-center gap-1 px-2 py-1 bg-surface border-b border-main shrink-0 overflow-x-auto">
      {[
        { icon: Bold, label: 'پررنگ (Ctrl+B)', run: () => wrap('**') },
        { icon: Italic, label: 'مورب (Ctrl+I)', run: () => wrap('*') },
        { icon: Heading2, label: 'عنوان', run: () => wrap('\n## ', '\n', 'عنوان') },
        { icon: Link, label: 'پیوند (Ctrl+K)', run: () => wrap('[', '](https://example.com)', 'عنوان پیوند') },
        { icon: Code2, label: 'کد', run: () => wrap('`', '`', 'code') },
        { icon: Undo2, label: 'واگرد (Ctrl+Z)', run: () => { if (view.current) undo(view.current); } },
        { icon: Redo2, label: 'انجام دوباره (Ctrl+Shift+Z)', run: () => { if (view.current) redo(view.current); } },
        { icon: Search, label: 'جستجو در متن (Ctrl+F)', run: () => { if (view.current) openSearchPanel(view.current); } },
      ].map(action => <Tooltip key={action.label} label={action.label}><button type="button" aria-label={action.label} disabled={readOnly && action.icon !== Search}
        className="btn p-1.5 rounded text-muted hover:bg-subtle hover:text-main shrink-0" onMouseDown={event => event.preventDefault()} onClick={action.run}><action.icon className="w-4 h-4" /></button></Tooltip>)}
      <span className="text-[11px] text-muted ms-auto whitespace-nowrap px-1">Markdown · فارسی / English</span>
    </div>
    <div ref={host} className="flex-1 min-h-0 overflow-hidden" />
  </div>;
}
