import { ConvertOptions, QueueItem } from '../types';

/**
 * Translates React UI ConvertOptions and targeted QueueItem into CLI arguments for fa-md-pdf.
 */
export function buildCliArgs(item: QueueItem, options: ConvertOptions): string[] {
  const args: string[] = [item.path];

  if (options.outputDir?.trim()) {
    args.push('--output', options.outputDir.trim());
  }

  if (options.format === 'wrap-rtl') {
    args.push('--wrap-rtl');
    if (options.wrapRtlSuffix) {
      args.push('--wrap-rtl-suffix', options.wrapRtlSuffix);
    }
  } else {
    args.push('--format', options.format);
    if (options.pageFormat) args.push('--page-format', options.pageFormat);
    if (options.margin) args.push('--margin', options.margin);
    if (options.landscape) args.push('--landscape');
    if (options.stripEmojis) args.push('--strip-emojis');

    if (options.format === 'docx') {
      args.push(
        '--docx-image-scale', String(options.docxImageScale),
        '--docx-image-min-width', String(options.docxImageMinWidth),
        '--docx-image-max-width', String(options.docxImageMaxWidth),
        '--docx-font-size', String(options.docxFontSize),
      );
    }

    if (options.mermaidTheme) args.push('--mermaid-theme', options.mermaidTheme);
    if (options.mermaidTimeout) args.push('--mermaid-timeout', String(options.mermaidTimeout * 1000));
    if (options.mermaidJs?.trim()) args.push('--mermaid-js', options.mermaidJs.trim());
    if (options.mermaidUrl?.trim()) args.push('--mermaid-url', options.mermaidUrl.trim());
    if (options.ignoreMermaidErrors) args.push('--ignore-mermaid-errors');

    if (options.fontFamily?.trim()) args.push('--font-family', options.fontFamily.trim());
    if (options.fontFile?.trim()) args.push('--font-file', options.fontFile.trim());
    if (options.fontDir?.trim()) args.push('--font-dir', options.fontDir.trim());
    if (options.customCss?.trim()) args.push('--css', options.customCss.trim());
  }

  if (options.browsersPath?.trim()) args.push('--browsers-path', options.browsersPath.trim());
  if (options.keepHtml) args.push('--keep-html');
  if (options.failFast) args.push('--fail-fast');
  if (options.verbose) args.push('--verbose');
  if (options.watch) args.push('--watch');
  args.push(options.recursive ? '--recursive' : '--no-recursive');

  if (options.extensions?.trim()) {
    const exts = options.extensions
      .split(/[, ]+/)
      .map(e => e.trim())
      .filter(Boolean)
      .map(e => (e.startsWith('.') ? e : `.${e}`));
    if (exts.length > 0) {
      args.push('--extensions', ...exts);
    }
  }

  return args;
}

/**
 * Default initial options matching fa-md-pdf defaults.
 */
export const DEFAULT_CONVERT_OPTIONS: ConvertOptions = {
  format: 'pdf',
  outputDir: '',
  pageFormat: 'A4',
  margin: '15mm',
  landscape: false,
  pdfPageNumbers: true,
  stripEmojis: false,
  docxImageScale: 3,
  docxImageMinWidth: 4.0,
  docxImageMaxWidth: 6.5,
  docxFontSize: 12,
  docxHighlightCode: true,
  docxPageNumbers: true,
  mermaidTheme: 'default',
  mermaidTimeout: 30,
  mermaidJs: '',
  mermaidUrl: '',
  ignoreMermaidErrors: false,
  browsersPath: '',
  fontFamily: '"Vazirmatn", "Noto Naskh Arabic", "Segoe UI", Tahoma, Arial, sans-serif',
  fontFile: '',
  fontDir: '',
  customCss: '',
  recursive: true,
  keepHtml: false,
  failFast: false,
  verbose: false,
  wrapRtlSuffix: '.rtl.md',
  watch: false,
  extensions: '.md, .markdown',
};
