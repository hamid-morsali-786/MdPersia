import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

/** Native modal semantics provide focus containment and make the workbench inert. */
export function AppDialog({ title, description, children, footer, onClose }: {
  title: string; description?: string; children: ReactNode; footer?: ReactNode; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  useEffect(() => {
    const element = dialog.current!;
    const previous = document.activeElement as HTMLElement | null;
    element.showModal();
    return () => { element.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  return (
    <dialog ref={dialog} className="app-dialog bg-surface text-main" dir="rtl"
      aria-labelledby={titleId} aria-describedby={description ? descriptionId : undefined}
      onCancel={event => { event.preventDefault(); onClose(); }}
      onKeyDown={event => {
        if (event.key !== 'Tab') return;
        const controls = [...event.currentTarget.querySelectorAll<HTMLElement>('button, input, select, textarea, a[href], [tabindex]')]
          .filter(element => element.tabIndex >= 0 && !element.matches(':disabled') && element.getClientRects().length);
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }}
      onClick={event => {
        if (event.target !== dialog.current) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
      }}>
      <header className="flex items-start justify-between gap-4 border-b border-main px-5 py-4 shrink-0">
        <div className="min-w-0">
          <h2 id={titleId} className="text-lg font-bold">{title}</h2>
          {description && <p id={descriptionId} className="text-xs text-muted mt-1 leading-6">{description}</p>}
        </div>
        <button type="button" onClick={onClose} className="btn p-2 rounded-md text-muted hover:bg-subtle hover:text-main" aria-label={`بستن ${title}`}>
          <X className="w-4 h-4" />
        </button>
      </header>
      <div className="app-dialog-body px-5 py-4">{children}</div>
      {footer && <footer className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-t border-main bg-surface shrink-0">{footer}</footer>}
    </dialog>
  );
}
