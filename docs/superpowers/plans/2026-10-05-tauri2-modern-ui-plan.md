# برنامه پیاده‌سازی رابط کاربری مدرن Tauri 2 برای `fa-md-pdf`
# Tauri 2 Modern UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade, human-centric modern desktop application in `desktop-tauri/` replicating the 3-zone workbench layout with React 19, TypeScript, Tailwind CSS, Lucide Icons, and Vazirmatn typography, interfaced with the Python core via Tauri 2 Sidecar.

**Architecture:** A standalone React 19 + TypeScript single-page application built with Vite and Tailwind CSS residing in `desktop-tauri/`, wrapped with a Tauri 2 (Rust) desktop shell that executes the Python backend as a child process and streams logs and progress via Tauri IPC.

**Tech Stack:** Tauri 2 (Rust), React 19, TypeScript, Vite 6, Tailwind CSS v4, Lucide React, Vazirmatn font.

**Spec:** [`docs/superpowers/specs/2026-10-05-tauri2-modern-ui-spec.md`](file:///e:/project/fa-md-pdf-project/docs/superpowers/specs/2026-10-05-tauri2-modern-ui-spec.md)

## Global Constraints
- Must be located in `desktop-tauri/` to keep existing Python CLI and Tkinter GUI intact.
- 100% parameter parity: all 32 CLI/GUI options must be represented and functional.
- Zero generic bootstrap appearance: bespoke developer-tool layout with Slate Dark (`#0B1120` / `#131D31`) and Light (`#F8FAFC` / `#FFFFFF`) themes.
- Clean code: small modular components ($\le 150$ LOC per component), strict TypeScript typing, no `any`.
- Browser preview compatibility: bridge must support browser dev server (`npm run dev`) with mock streaming as well as native Tauri execution.

## Review Focus
1. Parity: Ensure all 32 parameters map 1-to-1 to the Python CLI args without omissions.
2. Responsiveness: Paned layout scales elegantly from 1024px to 4K resolutions.
3. Thread/Process safety: Cancellation stops child processes cleanly without orphaned locks.
4. Persian Typography: Proper RTL rendering with Vazirmatn without broken glyphs or reverse English words.
5. Watch Mode: Auto-recompilation on source file changes without infinite loops.

---

### Task 1: Project Scaffolding & Setup (`desktop-tauri`)

**Files:**
- Create: `desktop-tauri/package.json`
- Create: `desktop-tauri/vite.config.ts`
- Create: `desktop-tauri/tsconfig.json`
- Create: `desktop-tauri/index.html`
- Create: `desktop-tauri/src/index.css`
- Create: `desktop-tauri/src/main.tsx`

**Steps:**
- [ ] Initialize `desktop-tauri/package.json` with React 19, TypeScript, Vite, Tailwind CSS, and Lucide React.
- [ ] Configure `vite.config.ts` with React plugin and path aliases.
- [ ] Set up `tsconfig.json` with strict mode and DOM libraries.
- [ ] Configure `index.css` with CSS variables for Slate/Zinc dark & light palettes and font definitions.
- [ ] Create `index.html` referencing Vazirmatn and JetBrains Mono fonts.
- [ ] Run `npm install` and verify build with `npm run build`.

---

### Task 2: Core Types & CLI Flag Translator

**Files:**
- Create: `desktop-tauri/src/types/index.ts`
- Create: `desktop-tauri/src/services/cliTranslator.ts`
- Create: `desktop-tauri/src/services/cliTranslator.test.ts`

**Steps:**
- [ ] Define TypeScript interfaces for `ConvertJob`, `ConvertOptions`, `ProgressEvent`, `QueueItem`, and `Theme`.
- [ ] Implement `translateOptionsToCliArgs(options: ConvertOptions, jobs: ConvertJob[])` supporting all 32 parameters.
- [ ] Write unit tests for CLI argument translation for PDF, DOCX, and wrap-rtl formats.
- [ ] Run tests and verify 100% parameter accuracy.

---

### Task 3: Zone A - Document Batch Queue Component

**Files:**
- Create: `desktop-tauri/src/components/QueuePanel.tsx`
- Create: `desktop-tauri/src/components/QueueItemRow.tsx`

**Steps:**
- [ ] Build table view displaying file name, size, status badge, and relative path.
- [ ] Implement Drag & Drop file drop zone.
- [ ] Implement actions: Add Files, Add Folder, Remove Selected, and Clear All.
- [ ] Add right-click context menu (Open file, Open folder, Remove).
- [ ] Verify selection, multi-selection, and empty state styling.

---

### Task 4: Zone B - 5-Tab Parameters Inspector Panel

**Files:**
- Create: `desktop-tauri/src/components/InspectorPanel.tsx`
- Create: `desktop-tauri/src/components/Inspector/TabDocument.tsx`
- Create: `desktop-tauri/src/components/Inspector/TabStyling.tsx`
- Create: `desktop-tauri/src/components/Inspector/TabMermaid.tsx`
- Create: `desktop-tauri/src/components/Inspector/TabDocx.tsx`
- Create: `desktop-tauri/src/components/Inspector/TabAdvanced.tsx`

**Steps:**
- [ ] Build top format selector (PDF, DOCX, Wrap-RTL) and output path row.
- [ ] Implement Tab 1 (Document): Page format, margin, landscape, PDF page numbers, strip emojis.
- [ ] Implement Tab 2 (Styling): Font family, custom font file, font dir, custom CSS.
- [ ] Implement Tab 3 (Mermaid & Browser): Themes, timeout, offline JS, CDN URL, browsers path.
- [ ] Implement Tab 4 (DOCX): Image scale, min/max width, font size, highlight code, page numbers.
- [ ] Implement Tab 5 (Advanced): Recursive, keep HTML, fail fast, verbose, RTL suffix.
- [ ] Build bottom action bar: Convert button (with spinner), Cancel button, Watch Mode toggle.
- [ ] Wire dynamic reactivity (enabling/disabling controls based on active format).

---

### Task 5: Zone C - Dual Preview & Terminal Workspace

**Files:**
- Create: `desktop-tauri/src/components/WorkspacePanel.tsx`
- Create: `desktop-tauri/src/components/Workspace/PreviewTab.tsx`
- Create: `desktop-tauri/src/components/Workspace/TerminalTab.tsx`

**Steps:**
- [ ] Build Preview tab with live Markdown rendering, RTL support, and "Open in Editor" button.
- [ ] Build Terminal tab with timestamped colored log entries (`#090D16` terminal theme).
- [ ] Add terminal toolbar with "Open Output Folder", "Copy Logs", and "Clear" actions.
- [ ] Verify tab switching and real-time log scrolling.

---

### Task 6: Top Header & Bottom Status Bar

**Files:**
- Create: `desktop-tauri/src/components/Header.tsx`
- Create: `desktop-tauri/src/components/StatusBar.tsx`
- Create: `desktop-tauri/src/App.tsx`

**Steps:**
- [ ] Build Header with logo, title, theme switcher (Dark / Light toggle) and help info.
- [ ] Build StatusBar with progress percentage bar, status message, and offline health badges.
- [ ] Assemble 3-zone layout in `App.tsx` with responsive layout and state synchronization.
- [ ] Verify theme transitions and dark/light mode consistency across all panels.

---

### Task 7: Tauri 2 Core & Sidecar Bridge Service

**Files:**
- Create: `desktop-tauri/src/services/tauriBridge.ts`
- Create: `desktop-tauri/src-tauri/Cargo.toml`
- Create: `desktop-tauri/src-tauri/tauri.conf.json`
- Create: `desktop-tauri/src-tauri/src/main.rs`
- Create: `desktop-tauri/src-tauri/src/lib.rs`

**Steps:**
- [ ] Implement `tauriBridge.ts` with dual-mode support (desktop Tauri IPC when inside Tauri, mock dev streaming when in browser).
- [ ] Create Tauri 2 configuration files with window setup, permissions, and shell plugin.
- [ ] Implement Rust backend commands in `lib.rs` for spawning `fa-md-pdf` subprocess and event streaming.
- [ ] Verify frontend build cleanly communicates through the bridge.

---

### Task 8: Verification, Test Suite & Standalone Build

**Files:**
- Create: `desktop-tauri/src/services/cliTranslator.test.ts`
- Modify: `README.md` (Add Tauri 2 run and build instructions)

**Steps:**
- [ ] Run full TypeScript typecheck (`tsc --noEmit`).
- [ ] Run unit tests for translator and state management.
- [ ] Run production Vite build (`npm run build`).
- [ ] Verify standalone asset generation and complete feature parity.
