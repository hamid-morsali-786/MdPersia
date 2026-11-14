import extensions from '../../../src/fa_md_pdf/assets/document-formats.json';

export const DOCUMENT_EXTENSIONS: string[] = extensions;
export const DOCUMENT_ACCEPT = extensions.map(extension => '.' + extension).join(',');
export const DEFAULT_EXTENSIONS = extensions.map(extension => '.' + extension).join(', ');

export function isMarkdownPath(path: string): boolean {
  const name = path.split(/[\\/]/).pop() || '';
  const dot = name.lastIndexOf('.');
  return dot > 0 && extensions.includes(name.slice(dot + 1).toLowerCase());
}

export function copyDocumentPath(path: string): string {
  const dot = path.lastIndexOf('.');
  return isMarkdownPath(path) ? path.slice(0, dot) + '-copy' + path.slice(dot) : path + '-copy.md';
}
