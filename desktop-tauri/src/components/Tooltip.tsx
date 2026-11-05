import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

interface TooltipProps {
  label: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * Fixed-position tooltip: panels clip their content with overflow-hidden,
 * so an absolutely positioned tip inside the trigger would be cut off.
 */
export const Tooltip: React.FC<TooltipProps> = ({ label, children, className }) => {
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const tip = useRef<HTMLSpanElement>(null);
  const id = useId();
  const timer = useRef<number | undefined>(undefined);

  const show = useCallback((el: HTMLElement) => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      if (el.isConnected) setAnchor(el);
    }, 120);
  }, []);

  const hide = useCallback(() => {
    window.clearTimeout(timer.current);
    setAnchor(null);
    setCoords(null);
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  useLayoutEffect(() => {
    if (!anchor || !tip.current) return;
    const measure = () => {
      const trigger = anchor.getBoundingClientRect();
      const bounds = tip.current!.getBoundingClientRect();
      const padding = 8;
      const left = Math.max(padding, Math.min(trigger.left + trigger.width / 2 - bounds.width / 2, window.innerWidth - bounds.width - padding));
      const above = trigger.top - bounds.height - padding;
      const top = Math.max(padding, Math.min(above >= padding ? above : trigger.bottom + padding, window.innerHeight - bounds.height - padding));
      setCoords(previous => previous?.top === top && previous.left === left ? previous : { top, left });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(tip.current);
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') hide(); };
    window.addEventListener('scroll', hide, true);
    window.addEventListener('resize', hide);
    window.addEventListener('keydown', escape);
    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', hide, true);
      window.removeEventListener('resize', hide);
      window.removeEventListener('keydown', escape);
    };
  }, [anchor, label, hide]);

  const describedChild = React.isValidElement<{ 'aria-describedby'?: string }>(children) && anchor
    ? React.cloneElement(children, { 'aria-describedby': [children.props['aria-describedby'], id].filter(Boolean).join(' ') })
    : children;

  return (
    <span
      data-tip-host
      className={`inline-flex ${className ?? ''}`}
      onMouseEnter={(e) => show(e.currentTarget)}
      onMouseLeave={hide}
      onFocus={(e) => show(e.currentTarget)}
      onBlur={hide}
      onKeyDown={(e) => { if (e.key === 'Escape') hide(); }}
      onPointerDown={hide}
    >
      {describedChild}
      {anchor && createPortal(
        <span
          ref={tip}
          id={id}
          role="tooltip"
          dir="auto"
          className="tip"
          style={{ top: coords?.top ?? 0, left: coords?.left ?? 0, visibility: coords ? 'visible' : 'hidden' }}
        >
          {label}
        </span>
      , anchor.closest('dialog[open]') || document.body)}
    </span>
  );
};
