import React, { useState, useRef, useEffect, useCallback } from 'react';

interface PaneSplitterProps {
  onResize: (deltaX: number) => void;
  onReset?: () => void;
  title?: string;
  growTowards?: 'left' | 'right';
  onResizeEnd?: () => void;
  value?: number;
  min?: number;
  max?: number;
}

export const PaneSplitter: React.FC<PaneSplitterProps> = ({
  onResize,
  onReset,
  title = 'تغییر اندازه بخش (بکشید)',
  growTowards = 'left', onResizeEnd,
  value, min, max,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const onResizeRef = useRef(onResize);
  onResizeRef.current = onResize;
  const lastXRef = useRef<number>(0);
  const dragging = useRef(false);
  const restore = useRef<(() => void) | null>(null);
  const endRef = useRef(onResizeEnd); endRef.current = onResizeEnd;
  const finish = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    restore.current?.(); restore.current = null;
    setIsDragging(false);
    endRef.current?.();
  }, []);
  useEffect(() => {
    window.addEventListener('blur', finish);
    const visibility = () => { if (document.hidden) finish(); };
    document.addEventListener('visibilitychange', visibility);
    return () => {
      window.removeEventListener('blur', finish);
      document.removeEventListener('visibilitychange', visibility);
      restore.current?.();
    };
  }, [finish]);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();

    lastXRef.current = e.clientX;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setIsDragging(true);
    dragging.current = true;

    const cursor = document.body.style.cursor;
    const select = document.body.style.userSelect;
    const frames = [...document.querySelectorAll('iframe')].map(frame => [frame, frame.style.pointerEvents] as const);
    restore.current = () => {
      document.body.style.cursor = cursor;
      document.body.style.userSelect = select;
      frames.forEach(([frame, value]) => { frame.style.pointerEvents = value; });
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    // Disable iframes pointer events so they do not eat mouse events during drag
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach((f) => (f.style.pointerEvents = 'none'));
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current || !e.currentTarget.hasPointerCapture(e.pointerId)) return;
    e.preventDefault();
    const currentX = e.clientX;
    // Queue grows leftwards; the output sidebar grows rightwards.
    const delta = (currentX - lastXRef.current) * (growTowards === 'right' ? 1 : -1);
    if (delta !== 0) {
      onResizeRef.current(delta);
      lastXRef.current = currentX;
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // Ignored if already released
    }
    finish();
  };

  return (
    <>
      {isDragging && (
        <div
          className="fixed inset-0 z-50 cursor-col-resize select-none pointer-events-none"
          aria-hidden="true"
        />
      )}
      <div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onLostPointerCapture={finish}
        role="separator" aria-orientation="vertical" aria-label={title} tabIndex={0}
        aria-valuenow={value} aria-valuemin={min} aria-valuemax={max}
        onKeyDown={event => {
          if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault();
            onResizeRef.current((event.key === 'ArrowRight' ? 24 : -24) * (growTowards === 'right' ? 1 : -1));
          } else if (event.key === 'Home') { event.preventDefault(); onReset?.(); }
        }}
        onKeyUp={event => { if (event.key.startsWith('Arrow')) endRef.current?.(); }}
        onDoubleClick={onReset}
        className={`group relative w-2 -mx-[3px] z-30 h-full cursor-col-resize select-none shrink-0 transition-colors duration-150 flex items-center justify-center touch-none ${
          isDragging
            ? 'bg-blue-500/80 shadow-md shadow-blue-500/30'
            : 'hover:bg-blue-500/40 bg-transparent'
        }`}
        title={title}
      >
        {/* Visual Line */}
        <div
          className={`w-[1px] h-full transition-colors ${
            isDragging ? 'bg-blue-400' : 'bg-border/60 group-hover:bg-blue-500/60'
          }`}
        />
        {/* Center Grip Dots */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 flex flex-col gap-1 items-center px-0.5 py-2 rounded-full transition-opacity pointer-events-none ${
            isDragging
              ? 'bg-blue-600 text-white opacity-100'
              : 'bg-surface border border-main text-muted opacity-0 group-hover:opacity-100'
          }`}
        >
          <span className="w-1 h-1 rounded-full bg-current" />
          <span className="w-1 h-1 rounded-full bg-current" />
          <span className="w-1 h-1 rounded-full bg-current" />
        </div>
      </div>
    </>
  );
};
