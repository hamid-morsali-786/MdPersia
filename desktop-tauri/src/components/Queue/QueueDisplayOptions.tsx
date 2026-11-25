import { useEffect, useId, useRef, useState } from 'react';
import { RotateCcw, SlidersHorizontal } from 'lucide-react';
import { Tooltip } from '../Tooltip';
import { DEFAULT_QUEUE_DISPLAY, QUEUE_DISPLAY_FIELDS, QUEUE_DISPLAY_KEY, queueDisplayFields, type QueueDisplayField } from './queueDisplay';

export function useQueueDisplay() {
  const [fields, setFields] = useState(() => {
    try { return queueDisplayFields(JSON.parse(localStorage.getItem(QUEUE_DISPLAY_KEY) || 'null')); }
    catch { return queueDisplayFields(null); }
  });

  useEffect(() => {
    try { localStorage.setItem(QUEUE_DISPLAY_KEY, JSON.stringify(['name', ...fields])); }
    catch { /* Optional preferences must not block the queue. */ }
  }, [fields]);

  const toggle = (field: QueueDisplayField) => setFields(current => {
    const next = new Set(current);
    if (!next.delete(field)) next.add(field);
    return next;
  });
  return { fields, toggle, reset: () => setFields(new Set(DEFAULT_QUEUE_DISPLAY)) };
}

export function QueueDisplayOptions({ fields, toggle, reset }: ReturnType<typeof useQueueDisplay>) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (!wrap.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener('pointerdown', dismiss);
    return () => window.removeEventListener('pointerdown', dismiss);
  }, [open]);

  const close = () => { setOpen(false); trigger.current?.focus(); };
  return (
    <div ref={wrap} className="relative shrink-0" onKeyDown={event => {
      if (event.key === 'Escape' && open) { event.stopPropagation(); close(); }
    }} onBlur={event => {
      if (open && !event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}>
      <Tooltip label="تنظیم نمایش اطلاعات صف">
        <button ref={trigger} type="button" aria-label="نمایش اطلاعات صف" aria-controls={panelId} aria-expanded={open}
          onClick={() => setOpen(previous => !previous)}
          className={`btn w-8 h-8 justify-center rounded-md border border-main text-muted hover:bg-[var(--bg-hover)] hover:text-[var(--text-main)] ${open ? 'bg-subtle' : ''}`}>
          <SlidersHorizontal className="size-4" aria-hidden="true" />
        </button>
      </Tooltip>
      {open && <div id={panelId} className="absolute end-0 top-full mt-2 w-52 rounded-lg border border-subtle bg-surface p-2 shadow-lg z-30 text-xs">
        <fieldset>
          <legend className="px-1 pb-1 font-semibold text-main">اطلاعات هر ردیف</legend>
          {QUEUE_DISPLAY_FIELDS.map(field => (
            <label key={field.id} className="flex min-h-8 items-center gap-2 rounded px-1.5 cursor-pointer hover:bg-[var(--bg-subtle)]">
              <input type="checkbox" className="accent-blue-600" checked={fields.has(field.id)} onChange={() => toggle(field.id)} />
              {field.label}
            </label>
          ))}
        </fieldset>
        <button type="button" onClick={() => { reset(); close(); }}
          className="btn w-full min-h-8 mt-1 px-1.5 rounded text-muted hover:text-[var(--text-main)] hover:bg-[var(--bg-subtle)]">
          <RotateCcw className="size-3.5" aria-hidden="true" />
          بازنشانی نمایش
        </button>
      </div>}
    </div>
  );
}
