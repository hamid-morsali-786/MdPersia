export const QUEUE_DISPLAY_FIELDS = [
  { id: 'status', label: 'آیکون وضعیت' },
  { id: 'size', label: 'حجم فایل زیر نام' },
  { id: 'relativePath', label: 'نام پوشه زیر نام فایل' },
] as const;

export type QueueDisplayField = typeof QUEUE_DISPLAY_FIELDS[number]['id'];
export const DEFAULT_QUEUE_DISPLAY: readonly QueueDisplayField[] = ['status', 'size'];
// Read the old column settings as preferences for the secondary details.
export const QUEUE_DISPLAY_KEY = 'fa_queue_visible_columns_v2';

export function queueDisplayFields(saved: unknown): Set<QueueDisplayField> {
  if (!Array.isArray(saved)) return new Set(DEFAULT_QUEUE_DISPLAY);
  const fields = QUEUE_DISPLAY_FIELDS.filter(field => saved.includes(field.id)).map(field => field.id);
  return new Set(fields.length || saved.includes('name') ? fields : DEFAULT_QUEUE_DISPLAY);
}

export function formatQueueBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
}
