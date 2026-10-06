# Repo Simplification & Over-Engineering Clean-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate dead code, git bloat, duplicate manifests, and hand-rolled logic across `fa-md-pdf` and `desktop-tauri`, reducing codebase complexity and line count while maintaining 100% test coverage and feature parity.

**Architecture:** Modernize Python core with standard library idioms (`pathlib.Path.parents`, dictionary dispatch), remove ~196 committed cache/binary files, eliminate redundant trampolines (`entry_point*.py`, `requirements.txt`), and optimize the Node.js Vite server plugin using native Node.js recursive filesystem APIs.

**Tech Stack:** Python 3.11+, pytest, Node.js 22+, Tauri 2, React 19, Vite 6, Tailwind CSS.

**Spec:** Codebase review findings from `/ponytail-audit` and `rtl_markdown_technical_audit.md`.

## Global Constraints

- Preserve 100% of existing functional tests (58 Python tests, 9 TypeScript tests).
- All changes must be strictly verified with TDD (tests run and verified before claiming task completion).
- No new third-party dependencies may be added.
- File deletions must be verified with global grepping to ensure no unbroken imports.

## Review Focus

1. `pathlib.Path.parents` replacement in `defaults.py` must handle root paths and non-existent paths gracefully.
2. `parse_docx_length` dictionary refactor must support float values and unit variations (`mm`, `cm`, `in`, `pt`, `px`).
3. `fs.readdirSync({ recursive: true })` in `vite.config.ts` must correctly compute relative paths and file extensions.
4. Removing `requirements.txt` must not break `pip install -e .` or CI/dev workflows.
5. Untracking Chrome cache directories must preserve the actual Chromium headless shell binary.

---

### Task 1: Repository Hygiene & Git Bloat Eradication

**Files:**
- Modify: `.gitignore`
- Remove from Git: `browsers/mcp-chrome/Default/*`, `docx-output/*`, `output/*`

- [ ] **Step 1: Update `.gitignore` with ignore rules for browser cache and test outputs**
  Add rules for `browsers/**/Default/`, `browsers/**/Local Storage/`, `*.log`, `output/`, and `docx-output/`.

- [ ] **Step 2: Untrack cached and generated binary files from git index**
  Run `git rm -r --cached browsers/mcp-chrome/Default`
  Run `git rm -r --cached docx-output`
  Run `git rm -r --cached output`

- [ ] **Step 3: Verify repository status**
  Run `git status -s` to verify 196+ tracked junk files are staged for removal.

- [ ] **Step 4: Commit git hygiene changes**
  Run `git commit -m "chore: untrack browser cache and test docx outputs from git"`

---

### Task 2: Remove Redundant Entry Points and Manifests

**Files:**
- Delete: `entry_point.py`
- Delete: `entry_point_gui.py`
- Delete: `requirements.txt`
- Modify: `pyproject.toml` (verify `[project.scripts]` and `[project.dependencies]`)

- [ ] **Step 1: Check all callers of `entry_point.py` and `entry_point_gui.py`**
  Grep repo for references in scripts and PyInstaller specs (`fa-md-pdf.spec`, `fa-md-pdf-gui.spec`, `scripts/build-exe.ps1`).

- [ ] **Step 2: Update PyInstaller specs to use standard entry points**
  Update `fa-md-pdf.spec` to use `src/fa_md_pdf/__main__.py` or module entry point.
  Update `fa-md-pdf-gui.spec` to use `src/fa_md_pdf/gui.py`.

- [ ] **Step 3: Remove redundant files**
  Delete `entry_point.py`, `entry_point_gui.py`, and `requirements.txt`.

- [ ] **Step 4: Verify package execution**
  Run `.venv/Scripts/python -m fa_md_pdf --version`
  Run `.venv/Scripts/python -m pytest`

- [ ] **Step 5: Commit manifest consolidation**
  Run `git commit -m "refactor: remove redundant entrypoint trampolines and requirements.txt"`

---

### Task 3: Simplify and Modernize `defaults.py` (TDD)

**Files:**
- Modify: `src/fa_md_pdf/defaults.py`
- Test: `tests/test_defaults.py`

- [ ] **Step 1: Write test for `defaults.py` path resolution and font lookup**
  Add unit tests in `tests/test_defaults.py` verifying `find_project_root` and `find_preferred_font_file` under edge cases.

- [ ] **Step 2: Run tests to establish baseline**
  Run `pytest tests/test_defaults.py` (ensure green).

- [ ] **Step 3: Refactor `_path_parents` to use standard `Path.parents`**
  Replace custom 14-line generator with `[p.resolve() for p in (start, *start.resolve().parents)]`.

- [ ] **Step 4: Simplify `find_preferred_font_file`**
  Replace loop with `next((p for name in PREFERRED_FONT_FILES if (p := fonts_dir / name).is_file()), None)`.

- [ ] **Step 5: Run tests and verify**
  Run `pytest tests/test_defaults.py` and full suite `pytest`.

- [ ] **Step 6: Commit `defaults.py` simplification**
  Run `git commit -m "refactor(defaults): replace custom generators with stdlib Path methods"`

---

### Task 4: Simplify `converter.py` and `docx_builder.py` (TDD)

**Files:**
- Modify: `src/fa_md_pdf/converter.py`
- Modify: `src/fa_md_pdf/docx_builder.py`
- Test: `tests/test_discovery.py`
- Test: `tests/test_docx_builder.py`

- [ ] **Step 1: Write unit tests for `parse_docx_length` and `normalize_extensions`**
  Ensure edge cases (`5mm`, `1.5in`, `20px`, invalid input fallback `15mm`, extensions `.md`, `MD`, `.MARKDOWN`) are pinned by tests.

- [ ] **Step 2: Run tests to verify baseline**
  Run `pytest tests/test_discovery.py tests/test_docx_builder.py`.

- [ ] **Step 3: Refactor `normalize_extensions` in `converter.py`**
  Replace 11-line mutation loop with clean set comprehension.

- [ ] **Step 4: Refactor `parse_docx_length` in `docx_builder.py`**
  Replace 22-line multiple `if/elif` chain with dictionary dispatch table:
  ```python
  UNIT_CONVERTERS = {
      "mm": Mm,
      "cm": Cm,
      "in": Inches,
      "inch": Inches,
      "pt": Pt,
      "px": lambda v: Inches(v / 96.0),
  }
  ```

- [ ] **Step 5: Run tests to verify all green**
  Run `pytest tests/test_discovery.py tests/test_docx_builder.py`.

- [ ] **Step 6: Commit core simplifications**
  Run `git commit -m "refactor(core): streamline length parsing and extension normalization"`

---

### Task 5: Reuse Safe File Reader in `rtl_wrapper.py`

**Files:**
- Modify: `src/fa_md_pdf/rtl_wrapper.py`
- Test: `tests/test_rtl_wrapper.py`

- [ ] **Step 1: Inspect `wrap_rtl_in_file` in `src/fa_md_pdf/rtl_wrapper.py`**
  Notice direct `source.read_text(encoding="utf-8-sig")` without fallback.

- [ ] **Step 2: Reuse `read_text_safely` from `html_builder.py`**
  Import and call `read_text_safely(source)` to support ANSI/cp1256 Windows edge cases.

- [ ] **Step 3: Run `pytest tests/test_rtl_wrapper.py`**
  Verify all 6 tests pass.

- [ ] **Step 4: Commit `rtl_wrapper` reuse**
  Run `git commit -m "refactor(rtl): reuse read_text_safely in wrap_rtl_in_file"`

---

### Task 6: Modernize Desktop Tauri Vite Plugin with Native Node.js APIs

**Files:**
- Modify: `desktop-tauri/vite.config.ts`
- Modify: `desktop-tauri/src/services/tauriBridge.ts`
- Test: `desktop-tauri/src/services/cliTranslator.test.ts`

- [ ] **Step 1: Replace hand-rolled recursive `scanDir` in `desktop-tauri/vite.config.ts`**
  Use native Node.js 20+ recursive directory reading:
  `fs.readdirSync(folderPath, { recursive: recursive, withFileTypes: true })`
  Cut 20+ lines of hand-rolled recursion boilerplate.

- [ ] **Step 2: Simplify `getTimestamp()` in `tauriBridge.ts`**
  Replace string slicing with standard `new Date().toLocaleTimeString()`.

- [ ] **Step 3: Run frontend tests and build**
  Run `npm test` in `desktop-tauri/`
  Run `npm run build` in `desktop-tauri/`

- [ ] **Step 4: Commit Vite plugin modernization**
  Run `git commit -m "refactor(tauri): use native Node.js recursive readdir in dev server"`

---

### Task 7: Streamline `cliTranslator.ts` Flag Translation

**Files:**
- Modify: `desktop-tauri/src/services/cliTranslator.ts`
- Test: `desktop-tauri/src/services/cliTranslator.test.ts`

- [ ] **Step 1: Review current 7 fragmented mini-functions in `cliTranslator.ts`**
  Assess whether merging them into a clean, cohesive translation pipeline reduces boilerplate while keeping strict typing.

- [ ] **Step 2: Refactor `buildCliArgs` to use declarative mappings**
  Group geometry, typography, and advanced flags cleanly without redundant function call indirection.

- [ ] **Step 3: Verify test suite and build**
  Run `npm test` in `desktop-tauri/` (must pass 9 tests).
  Run `npm run build`.

- [ ] **Step 4: Commit `cliTranslator` refactor**
  Run `git commit -m "refactor(tauri): declarative CLI argument building pipeline"`

---

### Task 8: Full Verification & Sanity Check

**Files:**
- All files across Python and Desktop Tauri

- [ ] **Step 1: Run complete Python test suite**
  Run `.venv/Scripts/python -m pytest` (all 58 tests must pass).

- [ ] **Step 2: Run complete TypeScript test suite**
  Run `npm test` in `desktop-tauri/` (all 9 tests must pass).

- [ ] **Step 3: Test production build**
  Run `npm run build` in `desktop-tauri/`.

- [ ] **Step 4: Test end-to-end conversion**
  Execute sample conversions for PDF, DOCX, and wrap-rtl to confirm zero runtime regressions.
