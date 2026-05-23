# Implementation Tasks

## Task 1: Add on_progress callback to converter.py

- [ ] Add optional `on_progress` callback parameter to `convert_jobs()` function signature
- [ ] Call `on_progress(job, result.ok, result.error)` after each job completes
- [ ] Ensure backward compatibility: CLI continues to work without passing callback
- [ ] Verify existing tests still pass

**Requirements:** R11-AC3

## Task 2: Add --gui flag to CLI

- [ ] Add `--gui` argument to `build_parser()` in cli.py with `action="store_true"`
- [ ] In `main()`, check `args.gui` early (before input validation) and call `launch_gui()`
- [ ] Make `input` argument optional when `--gui` is provided (use `nargs='?'`)
- [ ] Return 0 after GUI window closes

**Requirements:** R1-AC1, R1-AC3

## Task 3: Create gui.py module with MainWindow

- [ ] Create `src/fa_md_pdf/gui.py`
- [ ] Implement `MainWindow` class with tkinter root window
- [ ] Set window title: "fa-md-pdf - تبدیل مارک‌داون به PDF"
- [ ] Configure RTL layout direction for the window
- [ ] Set Persian-compatible font (Vazirmatn → Tahoma → Segoe UI fallback)
- [ ] Set minimum window size (800x600)
- [ ] Implement `launch_gui()` and `main()` entry point functions

**Requirements:** R1-AC1, R1-AC2, R10-AC1, R10-AC2, R10-AC3, R11-AC1

## Task 4: Implement Input Selection panel

- [ ] Add input path Entry field (right-aligned, RTL)
- [ ] Add "انتخاب فایل" button that opens file dialog for .md/.markdown files
- [ ] Add "انتخاب فولدر" button that opens directory dialog
- [ ] Add "جستجوی بازگشتی" checkbox, checked by default
- [ ] Display resolved absolute path in the Entry field after selection
- [ ] Allow manual typing/pasting in the input field
- [ ] Show red error label when path doesn't exist

**Requirements:** R2-AC1, R2-AC2, R2-AC3, R2-AC4, R2-AC5, R2-AC6

## Task 5: Implement Output Configuration panel

- [ ] Add output path Entry field (right-aligned, RTL)
- [ ] Add "انتخاب..." button that opens directory dialog
- [ ] Allow manual typing/pasting in the output field
- [ ] Leave empty by default (PDFs generated next to source)

**Requirements:** R3-AC1, R3-AC2, R3-AC3, R3-AC4

## Task 6: Implement Options Panel with tabs

- [ ] Create ttk.Notebook with 4 tabs: صفحه, فونت, Mermaid, پیشرفته
- [ ] **Tab "صفحه":** Page format dropdown (A4, Letter, Legal), margin text field (default 15mm), landscape checkbox
- [ ] **Tab "فونت":** Font-family display field, font file picker, font directory picker, mutual exclusivity logic
- [ ] **Tab "Mermaid":** Mermaid JS file picker, theme dropdown, timeout field, ignore-errors checkbox, optional URL field
- [ ] **Tab "پیشرفته":** Extensions field, keep-html checkbox, fail-fast checkbox, browsers-path picker
- [ ] Auto-populate detected paths (fonts dir, mermaid js, browsers path) from project root

**Requirements:** R4, R5, R6, R7, R8

## Task 7: Implement ConversionThread and progress communication

- [ ] Create `ProgressEvent` dataclass with event_type, job, total, completed, error fields
- [ ] Create `ConversionThread(threading.Thread)` class
- [ ] Thread calls `build_jobs()` then iterates with `on_progress` callback
- [ ] Post `ProgressEvent` to `queue.Queue` for each job result
- [ ] Support `threading.Event` for cancellation between jobs
- [ ] Post final "done" or "cancelled" event when thread exits

**Requirements:** R9-AC3, R9-AC4, R9-AC9

## Task 8: Implement Convert/Cancel buttons and Progress Display

- [ ] Add "تبدیل" button that validates input and starts ConversionThread
- [ ] Add "انصراف" button (disabled by default, enabled during conversion)
- [ ] Disable "تبدیل" button during conversion
- [ ] Add scrollable Text widget for progress log
- [ ] Poll queue via `root.after(100, poll_queue)` for thread-safe updates
- [ ] Show "✓ source → output" for success, "✗ source - error" for failure
- [ ] Show summary line when all jobs complete: "نتیجه: X موفق، Y ناموفق"
- [ ] Show validation error if input path is empty or invalid

**Requirements:** R9-AC1, R9-AC2, R9-AC5, R9-AC6, R9-AC7, R9-AC8

## Task 9: Implement error handling and dialogs

- [ ] Show `messagebox.showerror` when browsers directory is missing
- [ ] Show `messagebox.showerror` when mermaid.min.js is missing
- [ ] Show inline error labels for invalid file/directory paths
- [ ] Catch unexpected exceptions in ConversionThread and display in progress log

**Requirements:** R12-AC1, R12-AC2, R12-AC3, R12-AC4

## Task 10: Add fa-md-pdf-gui entry point to pyproject.toml

- [ ] Add `fa-md-pdf-gui = "fa_md_pdf.gui:main"` to `[project.scripts]`
- [ ] Verify `pip install -e .` registers both commands

**Requirements:** R1-AC2

## Task 11: Auto-detect offline assets on GUI launch

- [ ] Call `find_project_root()` when GUI launches
- [ ] Auto-populate browsers path if `browsers/` exists
- [ ] Auto-populate mermaid JS path if `vendor/mermaid.min.js` exists
- [ ] Auto-populate font directory if `fonts/` exists
- [ ] Call `set_playwright_browsers_path()` before conversion starts

**Requirements:** R1-AC4, R5-AC5, R7-AC2, R8-AC5, R11-AC2, R11-AC4
