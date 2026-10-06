# Ponytail Round 2 Simplification & Over-Engineering Clean-Up Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the 9 over-engineering and repository bloat findings identified in `/ponytail-audit` round 2: purge unused binaries and generated examples from git, remove obsolete scripts, fix Persian typography preservation in emoji stripping, simplify font CSS generation, unify output path resolution, inline single-use debug helpers, and streamline CLI argument translation in Desktop Tauri.

**Architecture:** Apply Ponytail principles (stdlib over custom, minimal working diffs, delete over add). Protect Persian cursive connectors by removing `\u200D` from `EMOJI_PATTERN`, eliminate dead conditional branches in `html_builder.py`, replace 7 fragmented argument helpers in `cliTranslator.ts` with a concise declarative mapping, and unify directory path calculations between CLI and converter.

**Tech Stack:** Python 3.11+, pytest, Node.js 22+, Tauri 2, React 19, TypeScript, Vite 6.

**Spec:** Codebase audit findings from `/ponytail-audit` round 2.

## Global Constraints

- 100% test pass rate at every commit: zero regressions across 27 Python tests and 9 TypeScript tests.
- All code changes strictly verified with TDD before commit.
- Preserve Persian typography integrity: ZWNJ (`\u200C`) and ZWJ (`\u200D`) must never be stripped as emojis.
- Zero new external dependencies.
- Follow Ponytail rule: deletion over addition, shortest working diff.

## Review Focus

1. `EMOJI_PATTERN` without `\u200D`: verify Persian words with zero-width joiners are preserved when `--strip-emojis` is active.
2. `strip_emojis` space normalization: verify tables (`|`), parentheses (`()`), and tabs are formatted cleanly without multiple redundant regex passes.
3. `output_for_file` and `_resolve_wrap_rtl_output`: ensure nested directory structures are preserved identically when converting a folder.
4. `desktop-tauri/src/services/cliTranslator.ts`: ensure identical CLI arguments are generated for all 3 formats (PDF, DOCX, wrap-rtl) after declarative refactoring.
5. Repository size: verify that `browsers/ffmpeg-1011` and `browsers/winldd-1007` are removed from git tracking without affecting Chromium execution.

---

### Task 1: Purge Unused Binaries and Generated Outputs from Git Index

**Files:**
- Modify: `.gitignore`
- Remove from Git: `browsers/ffmpeg-1011/`, `browsers/winldd-1007/`, `examples/*.rtl.md`, `examples/*.docx`

- [ ] **Step 1: Update `.gitignore` with ignore patterns for example outputs**
  Ensure `.gitignore` ignores `examples/*.rtl.md` and `examples/*.docx`.

- [ ] **Step 2: Remove unused binaries and generated files from git**
  Run:
  `git rm -r --cached browsers/ffmpeg-1011 browsers/winldd-1007`
  `git rm --cached examples/*.rtl.md`
  `git rm examples/sample-fa.docx` (if staged/tracked)

- [ ] **Step 3: Remove physical directory of unused binaries if appropriate**
  Remove `browsers/ffmpeg-1011` and `browsers/winldd-1007` from disk.

- [ ] **Step 4: Verify git status**
  Confirm ~4 MB of tracked binary files are removed and only essential Chromium shell remains.

- [ ] **Step 5: Commit Task 1**
  Run: `git commit -m "chore: untrack unused browser binaries and generated example outputs"`

---

### Task 2: Remove Obsolete Script `scripts/copy-existing-playwright-browsers.ps1`

**Files:**
- Delete: `scripts/copy-existing-playwright-browsers.ps1`

- [ ] **Step 1: Check callers of `copy-existing-playwright-browsers.ps1`**
  Verify nothing in `README.md`, `scripts/`, or `package.json` references this script.

- [ ] **Step 2: Delete `scripts/copy-existing-playwright-browsers.ps1`**
  Remove the redundant script.

- [ ] **Step 3: Commit Task 2**
  Run: `git commit -m "refactor: remove redundant copy-existing-playwright-browsers script"`

---

### Task 3: Typography Protection & HTML Builder Cleanup (TDD)

**Files:**
- Modify: `src/fa_md_pdf/html_builder.py`
- Test: `tests/test_html_builder.py`

**Interfaces:**
- `EMOJI_PATTERN`: compiled regex matching emojis without `\u200D`.
- `strip_emojis(text: str) -> str`: strips emojis and normalizes spaces.
- `_build_vazirmatn_font_dir_css(font_family: str, font_dir: Path) -> str`: generates CSS `@font-face` rules.

- [ ] **Step 1: Add unit tests in `tests/test_html_builder.py` for Persian typography preservation**
  Assert that `strip_emojis("متن فارسی با اتصال\u200Dنما و ایموجی 😊")` strips `😊` but leaves `\u200D` intact.
  Assert that font css generation produces valid rules without dead branches.

- [ ] **Step 2: Run test to observe baseline or failure**
  Run: `pytest tests/test_html_builder.py`

- [ ] **Step 3: Implement fixes in `src/fa_md_pdf/html_builder.py`**
  1. Remove `|[\u200D]` from `EMOJI_PATTERN`.
  2. Simplify `strip_emojis`: combine space normalization cleanly.
  3. Delete duplicate `if not rules:` block in `_build_vazirmatn_font_dir_css`.

- [ ] **Step 4: Run tests to verify all pass**
  Run: `pytest tests/test_html_builder.py`

- [ ] **Step 5: Commit Task 3**
  Run: `git commit -m "fix(typography): preserve Persian ZWJ in strip_emojis and simplify font css"`

---

### Task 4: Unify Output Path Resolution & Inline Debug Helper (TDD)

**Files:**
- Modify: `src/fa_md_pdf/converter.py`
- Modify: `src/fa_md_pdf/cli.py`
- Test: `tests/test_converter.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- `output_for_file(source: Path, input_root: Path | None, output: Path | None, output_format: str = "pdf") -> Path`

- [ ] **Step 1: Check existing output resolution tests**
  Run: `pytest tests/test_converter.py tests/test_cli.py`

- [ ] **Step 2: Inline single-use `_write_html_for_debug` in `converter.py`**
  Remove `_write_html_for_debug` definition and inline the 2 lines directly into `_render_job`.

- [ ] **Step 3: Unify path calculation helper or reuse `output_for_file` logic in `cli.py`**
  Streamline `_resolve_wrap_rtl_output` to follow the standardized relative path computation.

- [ ] **Step 4: Run test suite to verify no regressions**
  Run: `pytest`

- [ ] **Step 5: Commit Task 4**
  Run: `git commit -m "refactor(core): inline debug html helper and streamline path resolution"`

---

### Task 5: Streamline `desktop-tauri/src/services/cliTranslator.ts` (TDD)

**Files:**
- Modify: `desktop-tauri/src/services/cliTranslator.ts`
- Test: `desktop-tauri/src/services/cliTranslator.test.ts`

**Interfaces:**
- `buildCliArgs(item: QueueItem, options: ConvertOptions): string[]`

- [ ] **Step 1: Run TypeScript unit tests to establish baseline**
  Run: `npm test` in `desktop-tauri/` (9 passing).

- [ ] **Step 2: Refactor `cliTranslator.ts`**
  Replace the 7 fragmented functions with a declarative, cohesive argument mapping inside `buildCliArgs`. Keep `DEFAULT_CONVERT_OPTIONS` identical.

- [ ] **Step 3: Run TypeScript tests and Vite production build**
  Run: `npm test`
  Run: `npm run build`

- [ ] **Step 4: Commit Task 5**
  Run: `git commit -m "refactor(tauri): simplify CLI argument builder into declarative pipeline"`

---

### Task 6: Final Verification & End-to-End Validation

**Files:**
- Full repository

- [ ] **Step 1: Run complete Python test suite**
  Run: `.venv/Scripts/python -m pytest -v` (all tests must pass).

- [ ] **Step 2: Run complete Desktop Tauri test suite**
  Run: `npm test` in `desktop-tauri/`.

- [ ] **Step 3: Verify end-to-end conversions**
  Test conversion of `examples/sample-fa.md` with:
  1. Wrap RTL: `.venv\Scripts\python -m fa_md_pdf examples\sample-fa.md --wrap-rtl`
  2. DOCX: `.venv\Scripts\python -m fa_md_pdf examples\sample-fa.md --format docx`
  3. PDF: `.venv\Scripts\python -m fa_md_pdf examples\sample-fa.md --format pdf`

- [ ] **Step 4: Final commit and cleanliness check**
  Run: `git status -s` to ensure repository is clean and unpolluted.
