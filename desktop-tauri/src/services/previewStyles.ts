import type { ReadingSettings } from './appSettings';

/** Preview-only colors: exports keep their own print/conversion styles. */
export function previewStyles(theme: string, zoom: number, reading: ReadingSettings): string {
  const dark = theme === 'dark';
  const colors = dark ? {
    page: '#121214', text: '#e4e4e7', heading: '#fafafa', border: '#3f4552',
    surface: '#1b2230', code: '#171e2b', muted: '#a8b5ca', accent: '#93c5fd',
    keyword: '#c4b5fd', string: '#a7e3b1', number: '#f6ce82', function: '#8ed5ee',
    node: '#233249', cluster: '#182131', edge: '#b8c9e4', inline: '#f2c4dd',
  } : {
    page: '#ffffff', text: '#263244', heading: '#0f172a', border: '#cbd5e1',
    surface: '#f1f5f9', code: '#f5f7fa', muted: '#52647b', accent: '#1d4ed8',
    keyword: '#65339b', string: '#166534', number: '#92400e', function: '#075985',
    node: '#e8eff9', cluster: '#f5f7fb', edge: '#475569', inline: '#9d174d',
  };
  const variables = Object.entries(colors).map(([name, value]) => `--preview-${name}:${value};`).join('');
  return `
    :root { ${variables} color-scheme:${dark ? 'dark' : 'light'}; }
    html { zoom:${zoom}%; scroll-behavior:auto; overflow-y:auto; }
    html,body { margin:0; padding:0; }
    body,.markdown-body { background:var(--preview-page) !important; color:var(--preview-text) !important; }
    .markdown-body { padding:32px clamp(18px,4vw,44px) !important;
      max-width:${reading.readingWidth === 'wide' ? 'none' : '920px'} !important;
      line-height:${reading.lineHeight} !important; margin:0 auto !important;
      box-sizing:border-box !important; min-height:100vh; overflow-wrap:break-word; }
    .markdown-body p,.markdown-body li { line-height:inherit !important; }
    h1,h2,h3,h4,h5,h6 { color:var(--preview-heading) !important; border-color:var(--preview-border) !important; }
    a { color:var(--preview-accent) !important; }
    hr,table th,table td { border-color:var(--preview-border) !important; }
    table th { background:var(--preview-surface) !important; color:var(--preview-text) !important; }
    table td { background:var(--preview-page) !important; color:var(--preview-text) !important; }
    blockquote { background:var(--preview-surface) !important; color:var(--preview-text) !important; }
    .markdown-body :not(pre)>code { background:var(--preview-surface) !important; color:var(--preview-inline) !important; }
    .markdown-body pre:not(.mermaid) { background:var(--preview-code) !important;
      color:var(--preview-text) !important; border:1px solid var(--preview-border) !important;
      padding:18px 20px !important; border-radius:10px; line-height:1.8 !important;
      white-space:${reading.wrapCode ? 'pre-wrap' : 'pre'} !important;
      overflow-wrap:${reading.wrapCode ? 'anywhere' : 'normal'} !important;
      overflow-x:auto !important; max-width:100%; box-sizing:border-box; tab-size:4;
      direction:ltr !important; text-align:left !important; unicode-bidi:isolate !important; }
    .markdown-body pre:not(.mermaid),.markdown-body pre:not(.mermaid) * {
      font-family:'Cascadia Mono',Consolas,'Vazirmatn',monospace !important;
      font-size:13px !important; }
    .markdown-body pre:not(.mermaid) code,.markdown-body pre:not(.mermaid) span {
      background:transparent !important; padding:0 !important; border:0 !important;
      white-space:inherit !important; overflow-wrap:inherit !important; }
    .markdown-body pre:not(.mermaid) code { display:block; color:inherit !important; }
    .markdown-body pre code :is(.k,.kd,.kn,.kr,.kt,.kc,.ow) { color:var(--preview-keyword) !important; }
    .markdown-body pre code :is(.s,.s1,.s2,.sb,.sc,.sd,.sa,.se,.sh,.si,.sr,.ss,.sx) { color:var(--preview-string) !important; }
    .markdown-body pre code :is(.c,.c1,.cm,.cs,.ch,.cp,.cpf) { color:var(--preview-muted) !important; }
    .markdown-body pre code :is(.m,.mi,.mf,.mh,.mo,.mb,.il) { color:var(--preview-number) !important; }
    .markdown-body pre code :is(.nf,.fm,.nc,.nn,.nb,.bp,.na,.nv,.vi,.vg) { color:var(--preview-function) !important; }
    .markdown-body pre code :is(.o,.p) { color:var(--preview-text) !important; }
    .mermaid { filter:none !important; background:var(--preview-cluster) !important;
      color:var(--preview-text) !important; border:1px solid var(--preview-border) !important;
      padding:24px 16px !important; border-radius:10px; white-space:normal !important;
      overflow:visible !important; max-width:100%; box-sizing:border-box; }
    .mermaid svg { background:transparent !important; max-width:100%; height:auto; display:block; margin-inline:auto; }
    .mermaid svg :is(.node rect,.node circle,.node ellipse,.node polygon,.node path,.actor,.labelBox,.activation0,.activation1,.activation2) {
      fill:var(--preview-node) !important; stroke:var(--preview-edge) !important; }
    .mermaid svg .cluster rect { fill:var(--preview-cluster) !important; stroke:var(--preview-border) !important; }
    .mermaid svg :is(text,.label,.nodeLabel,.cluster-label,.edgeLabel,.messageText,.loopText,.noteText) {
      fill:var(--preview-text) !important; color:var(--preview-text) !important; }
    .mermaid svg :is(.label,.nodeLabel,.cluster-label,.edgeLabel) * { color:var(--preview-text) !important; }
    .mermaid svg :is(.flowchart-link,.edgePath path,.messageLine0,.messageLine1,.actor-line,.loopLine,line) {
      stroke:var(--preview-edge) !important; stroke-width:1.8px !important; }
    .mermaid svg marker path { fill:var(--preview-edge) !important; stroke:var(--preview-edge) !important; }
    .mermaid svg :is(.edgeLabel,.edgeLabel p,.edgeLabel span,.labelBkg,.note) {
      background:var(--preview-cluster) !important; fill:var(--preview-cluster) !important; }
    img { max-width:100%; height:auto; }
  `;
}
