import React from 'react';
import { ColumnDef } from './queueTypes';

interface ResizableHeaderCellProps {
  column: ColumnDef;
  width: number;
  isResizing: boolean;
  onStartResize: (e: React.MouseEvent) => void;
  onResetWidth: () => void;
}

export const ResizableHeaderCell: React.FC<ResizableHeaderCellProps> = ({
  column,
  width,
  isResizing,
  onStartResize,
  onResetWidth,
}) => {
  const alignClass =
    column.align === 'left'
      ? 'text-left'
      : column.align === 'center'
      ? 'text-center'
      : 'text-right';

  return (
    <th
      style={{ width: `${width}px` }}
      className={`relative px-3 py-2 font-medium select-none group transition-colors ${alignClass}`}
    >
      <span className="truncate block" title={column.label}>
        {column.label}
      </span>

      {/* Resize Handle (Left edge in RTL) */}
      <div
        role="separator"
        aria-orientation="vertical"
        title="برای تغییر اندازه بکشید (دوبار کلیک برای اندازه پیش‌فرض)"
        onMouseDown={onStartResize}
        onDoubleClick={onResetWidth}
        className={`absolute left-0 top-0 bottom-0 w-2 cursor-col-resize z-10 flex items-center justify-center transition-colors ${
          isResizing
            ? 'bg-blue-500'
            : 'hover:bg-blue-500/60 active:bg-blue-600'
        }`}
      >
        <div
          className={`w-[1px] h-3.5 transition-colors ${
            isResizing ? 'bg-white' : 'bg-transparent group-hover:bg-blue-400/80'
          }`}
        />
      </div>
    </th>
  );
};
