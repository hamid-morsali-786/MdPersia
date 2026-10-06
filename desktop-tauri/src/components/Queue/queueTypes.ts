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
    defaultWidth: 180,
    minWidth: 110,
    maxWidth: 500,
    required: true,
    align: 'right',
  },
  {
    id: 'size',
    label: 'حجم',
    defaultWidth: 80,
    minWidth: 55,
    maxWidth: 200,
    align: 'left',
  },
  {
    id: 'status',
    label: 'وضعیت',
    defaultWidth: 95,
    minWidth: 75,
    maxWidth: 220,
    align: 'center',
  },
  {
    id: 'relativePath',
    label: 'مسیر نسبی',
    defaultWidth: 140,
    minWidth: 80,
    maxWidth: 400,
    align: 'right',
  },
] as const;

export const DEFAULT_COLUMN_WIDTHS: Record<ColumnKey, number> = {
  name: 180,
  size: 80,
  status: 95,
  relativePath: 140,
};

export const DEFAULT_VISIBLE_COLUMNS: ColumnKey[] = ['name', 'size', 'status', 'relativePath'];

export const STORAGE_KEY_COLUMN_WIDTHS = 'fa_queue_column_widths_v1';
export const STORAGE_KEY_VISIBLE_COLUMNS = 'fa_queue_visible_columns_v1';
