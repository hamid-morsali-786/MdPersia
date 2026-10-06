import React, { useState, useEffect } from 'react';

interface PaneSplitterProps {
  onResize: (deltaX: number) => void;
  onReset?: () => void;
  title?: string;
}

export const PaneSplitter: React.FC<PaneSplitterProps> = ({
  onResize,
  onReset,
  title = 'تغییر اندازه بخش (بکشید)',
}) => {
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (!isDragging) return;

    let prevX = 0;

    const handleMouseMove = (e: MouseEvent) => {
      if (prevX !== 0) {
        // In RTL, moving leftwards (decreasing X) expands right-side panels
        const delta = prevX - e.clientX;
        onResize(delta);
      }
      prevX = e.clientX;
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, onResize]);

  return (
    <div
      onMouseDown={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDoubleClick={onReset}
      className={`group relative w-1.5 hover:w-2 -mx-[3px] z-30 h-full cursor-col-resize select-none shrink-0 transition-all duration-150 flex items-center justify-center ${
        isDragging ? 'bg-blue-500/80 shadow-md shadow-blue-500/30 w-2' : 'hover:bg-blue-500/40 bg-transparent'
      }`}
      title={title}
    >
      {/* Visual Line */}
      <div
        className={`w-[1px] h-full transition-colors ${
          isDragging ? 'bg-blue-400' : 'bg-transparent group-hover:bg-blue-500/60'
        }`}
      />
      {/* Center Grip Dots */}
      <div
        className={`absolute top-1/2 -translate-y-1/2 flex flex-col gap-1 items-center px-0.5 py-2 rounded-full transition-opacity ${
          isDragging ? 'bg-blue-600 text-white opacity-100' : 'bg-subtle border border-main text-muted opacity-0 group-hover:opacity-100'
        }`}
      >
        <span className="w-1 h-1 rounded-full bg-current" />
        <span className="w-1 h-1 rounded-full bg-current" />
        <span className="w-1 h-1 rounded-full bg-current" />
      </div>
    </div>
  );
};
