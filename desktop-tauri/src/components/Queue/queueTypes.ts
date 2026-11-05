export type ColumnKey = 'name' | 'size' | 'status' | 'relativePath';

export interface ColumnDef {
  id: ColumnKey;
  label: string;
  defaultWidth: number;
  minWidth: number;
  maxWidth?: number;
  required?: boolean;
  align?: 'right' | 'left' | 'center';
}

export const QUEUE_COLUMNS: readonly ColumnDef[] = [
  {
    id: 'name',
    label: 'نام فایل',
    defaultWidth: 148,
    minWidth: 110,
    maxWidth: 500,
    required: true,
    align: 'right',
  },
  {
    id: 'size',
    label: 'حجم',
    defaultWidth: 74,
    minWidth: 55,
    maxWidth: 200,
    align: 'center',
  },
  {
    id: 'status',
    label: 'وضعیت',
    defaultWidth: 92,
    minWidth: 90,
    maxWidth: 220,
    align: 'center',
  },
  {
    id: 'relativePath',
    label: 'مسیر',
    defaultWidth: 100,
    minWidth: 72,
    maxWidth: 400,
    align: 'right',
  },
] as const;

export const DEFAULT_COLUMN_WIDTHS: Record<ColumnKey, number> = {
  name: 148,
  size: 74,
  status: 92,
  relativePath: 100,
};

/**
 * `relativePath` stays opt-in: four metadata columns cannot share a 380px sidebar
 * without every cell truncating. It is one click away in the columns popover.
 */
export const DEFAULT_VISIBLE_COLUMNS: ColumnKey[] = ['name', 'size', 'status'];

/** Stretches to the panel width so the table never scrolls sideways. */
export const FILL_COLUMN: ColumnKey = 'name';

export const STORAGE_KEY_COLUMN_WIDTHS = 'fa_queue_column_widths_v3';
export const STORAGE_KEY_VISIBLE_COLUMNS = 'fa_queue_visible_columns_v2';
