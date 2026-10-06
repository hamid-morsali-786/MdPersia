export type OutputFormat = 'pdf' | 'docx' | 'wrap-rtl';
export type ItemStatus = 'pending' | 'running' | 'success' | 'error';
export type MermaidTheme = 'default' | 'forest' | 'dark' | 'neutral' | 'base' | 'null';
export type PageFormat = 'A4' | 'A3' | 'Letter' | 'Legal';
export type MarginOption = '10mm' | '15mm' | '20mm' | '25mm' | '30mm';

export interface QueueItem {
  id: string;
  name: string;
  path: string;
  sizeBytes: number;
  sizeStr: string;
  status: ItemStatus;
  relativePath?: string;
  error?: string;
}

export interface ConvertOptions {
  format: OutputFormat;
  outputDir: string;
  // Page Geometry (PDF & DOCX shared)
  pageFormat: PageFormat;
  margin: MarginOption;
  landscape: boolean;
  // PDF specific
  pdfPageNumbers: boolean;
  stripEmojis: boolean;
  // DOCX specific
  docxImageScale: number;
  docxImageMinWidth: number;
  docxImageMaxWidth: number;
  docxFontSize: number;
  docxHighlightCode: boolean;
  docxPageNumbers: boolean;
  // Mermaid & Browser
  mermaidTheme: MermaidTheme;
  mermaidTimeout: number; // in seconds
  mermaidJs: string;
  mermaidUrl: string;
  ignoreMermaidErrors: boolean;
  browsersPath: string;
  // Styling
  fontFamily: string;
  fontFile: string;
  fontDir: string;
  customCss: string;
  // Advanced
  recursive: boolean;
  keepHtml: boolean;
  failFast: boolean;
  verbose: boolean;
  wrapRtlSuffix: string;
  watch: boolean;
  extensions: string;
}

export interface ProgressEvent {
  type: 'start' | 'progress' | 'success' | 'error' | 'done' | 'cancelled';
  file?: string;
  total?: number;
  completed?: number;
  error?: string;
  destPath?: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'success' | 'warn' | 'error' | 'summary';
  message: string;
}
