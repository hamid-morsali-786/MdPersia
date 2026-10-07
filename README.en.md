<div align="center">

# MdPersia
### The Modern, Offline-First Persian & RTL Markdown to Word (DOCX) and PDF Converter

[![GitHub Stars](https://img.shields.io/github/stars/hamid-morsali-786/MdPersia?style=for-the-badge&color=e8590c)](https://github.com/hamid-morsali-786/MdPersia/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/hamid-morsali-786/MdPersia?style=for-the-badge&color=f59e0b)](https://github.com/hamid-morsali-786/MdPersia/network/members)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-brightgreen?style=for-the-badge&logo=python)](https://python.org)
[![CI Build](https://img.shields.io/badge/CI-Passing-success?style=for-the-badge&logo=githubactions)](https://github.com/hamid-morsali-786/MdPersia/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=for-the-badge)](CONTRIBUTING.md)

<p align="center">
  <b>Developed &amp; Maintained by:</b> <a href="https://github.com/hamid-morsali-786">hamid-morsali-786</a>
</p>

[فارسی](README.md) | **English**

<br/>

<p align="center">
  <img src="docs/screenshots/desktop-ui-light.png" width="920" alt="MdPersia Desktop Application - Light Theme">
</p>

</div>

---

## Table of Contents

- [Overview & Why MdPersia?](#why-mdpersia)
- [Key Features](#features)
- [Feature Comparison Matrix](#comparison-matrix)
- [Comprehensive Markdown Formatting Guide](#comprehensive-markdown-formatting-guide)
  - [Callouts & Admonitions](#callouts--admonitions)
  - [Code Highlighting (Pygments)](#code-highlighting-pygments)
  - [Advanced RTL Tables](#advanced-rtl-tables)
  - [Page Breaks for Printing](#page-breaks-for-printing)
  - [Emoji & Symbol Typography](#emoji--symbol-typography)
- [Full Mermaid Diagrams Showcase](#full-mermaid-diagrams-showcase)
- [Microsoft Word (DOCX) Deep Dive](#microsoft-word-docx-deep-dive)
- [Vector PDF Deep Dive](#vector-pdf-deep-dive)
- [Smart Markdown RTL Wrapping (RTL Markdown Deep Dive)](#-smart-markdown-rtl-wrapping-rtl-markdown-deep-dive)
- [Installation](#installation)
- [Quick Start & CLI Workflows](#quick-start--cli-workflows)
- [Desktop Application (GUI)](#desktop-application-gui)
- [Comprehensive CLI Options Reference](#comprehensive-cli-options-reference)
- [Python API Reference](#python-api-reference)
- [CI/CD & Enterprise Automation](#cicd--enterprise-automation)
- [Architecture](#architecture)
- [Star History](#star-history)
- [Contributing & License](#contributing)

---

## Why MdPersia?

Writing technical documentation in Markdown is the industry standard. However, converting Markdown documents containing **Persian / Arabic (RTL)** text into publication-ready **PDF** or **Microsoft Word (DOCX)** formats has long been notoriously frustrating:

- ❌ **Flipped Punctuation & Mixed Direction**: In tools like Pandoc or traditional VS Code extensions, mixed English terminology, numbers, code tokens, and parentheses `()` frequently flip or become misaligned.
- ❌ **Broken Word (DOCX) RTL Layouts**: Standard converters generate left-to-right Word files where text clings to the wrong margin and tables are inverted.
- ❌ **Failed Mermaid Diagram Rendering**: Architecture diagrams and flowcharts either fail completely or require online network connections.

**MdPersia** solves all of these challenges. Equipped with a dedicated dual-engine pipeline (Chromium vector printing for PDF and a native Office XML generator for Word), MdPersia produces publication-grade documents with flawless BiDi text direction, beautiful **Vazirmatn** Persian typography, and crystal-clear embedded diagrams.

---

## Features

- 📑 **Dual Native Outputs**: Simultaneously produce fully editable, RTL-structured **Word (.docx)** files and vector-grade **PDFs**.
- 📊 **First-Class Mermaid Support**: Seamless offline rendering for Flowcharts, Sequence Diagrams, Class Diagrams, State Diagrams, Gantt Charts, and Pie Charts.
- ⚡ **100% Offline-First Architecture**: Zero external CDN calls. Local Chromium binaries, Vazirmatn fonts, and local Mermaid scripts work entirely air-gapped.
- 🔄 **Real-Time Watch Mode (`-w` / `--watch`)**: A lightweight daemon automatically recompiles documents the moment you press `Ctrl+S` in your editor.
- 📁 **Batch Directory Processing**: Converts entire folders and subfolders while preserving directory hierarchies.
- 🪄 **Intelligent Markdown Repair (`--wrap-rtl`)**: Automatically wraps Persian paragraphs with `<div dir="rtl">` without touching code blocks or existing markup.
- 🖥️ **Modern Desktop GUI (Tauri)**: A responsive 3-pane workbench with light/dark theme switching, real-time logging, and parameter inspection.

---

## Comparison Matrix

| Feature | MdPersia | Pandoc + XeLaTeX | VS Code Markdown-PDF | Typora Export |
| :--- | :---: | :---: | :---: | :---: |
| **Persian / RTL Accuracy** | **Flawless (Native)** | Complex Config | Inconsistent | System-dependent |
| **Native Word (.docx) RTL** | **Yes (Full RTL)** | Basic / LTR Defaults | No | Basic |
| **Offline Mermaid Diagrams** | **Built-in & Auto** | Requires Filters | Requires Internet | Editor-dependent |
| **Zero External Setup** | **Yes (Standalone)** | Requires >4GB TeXLive | Requires Extension | Closed Source |
| **Batch Folder Processing** | **Yes** | Manual Scripting | Manual | No |
| **Live Watch Daemon** | **Yes (`-w`)** | No | No | No |
| **Graphical User Interface** | **Yes (GUI included)** | No | Editor GUI | Editor GUI |

---

## Comprehensive Markdown Formatting Guide

### Callouts & Admonitions
Highlight important notes, tips, and warnings using GitHub Callout syntax. They render as shaded, thick-bordered boxes in both PDF and Word:

```markdown
> [!NOTE]
> General background context, extra notes, or complementary information.

> [!TIP]
> Pro-tip: Use the A4 format and default options for optimal performance.

> [!IMPORTANT]
> Essential requirement: These settings apply across all subfolders.

> [!WARNING]
> Warning: Overwriting files with the same name replaces existing content.

> [!CAUTION]
> Security notice: Never store sensitive credentials or keys in source files.
```

### Code Highlighting (Pygments)
Code blocks are highlighted via **Pygments** with strict LTR isolation and `Consolas` monospace font:

````markdown
```python
def process_documents(file_paths: list[str]) -> int:
    """Process Persian markdown files into DOCX and PDF."""
    return len(file_paths)
```
````

### Advanced RTL Tables
- In **Word (DOCX)**: Table direction is set to Right-to-Left (`w:bidiVisual`), header rows repeat across pages (`w:tblHeader`), with clean borders and alternating row shading.
- In **PDF**: Tables adapt to page width with proper padding and text wrapping.

```markdown
| Module Name | Output Format | Status | Details |
| :--- | :---: | :---: | :--- |
| `html_builder` | PDF | Active | Vector rendering via Chromium |
| `docx_builder` | DOCX | Active | Office Open XML generation |
| `mermaid` | PNG/SVG | Active | Offline high-resolution rendering |
```

### Page Breaks for Printing
Force a new page in both PDF and Word by placing either tag:

```html
<hr class="page-break">
```

### Emoji & Symbol Typography
- In Word, emojis render cleanly using `Segoe UI Emoji`.
- Use `--strip-emojis` to remove emojis from formal/academic documents while fully preserving Persian typography and **zero-width non-joiners (ZWNJ)**.

---

## Full Mermaid Diagrams Showcase

MdPersia automatically detects ` ```mermaid ` fences and converts them into vector graphics for PDF and high-resolution PNGs for Word.

### 1. Flowchart
```mermaid
flowchart TD
    Start([Start]) --> Input[/Input: Markdown File/]
    Input --> Process{Inspect RTL Structure}
    Process -->|Needs Wrapping| Fix[Inject RTL Wrappers]
    Process -->|Standard| Render[Render DOCX & PDF]
    Fix --> Render
    Render --> Done([Completed])
```

### 2. Sequence Diagram
```mermaid
sequenceDiagram
    actor User as "Developer"
    participant CLI as "MdPersia CLI"
    participant Engine as "Conversion Engine"
    participant Output as "Word / PDF"
    User->>CLI: Run mdpersia doc.md -f docx
    CLI->>Engine: Parse text & diagrams
    Engine->>Engine: Render Mermaid to PNG
    Engine->>Output: Inject native RTL paragraphs & tables
    Output-->>User: Deliver formatted doc.docx
```

### 3. Class Diagram
```mermaid
classDiagram
    class ConvertJob {
        +Path source
        +Path output
        +Path html_output
    }
    class ConvertOptions {
        +str output_format
        +str font_family
        +str page_format
        +str margin
        +bool landscape
    }
    class DocxBuilder {
        +build_docx(tokens, options)
    }
    ConvertJob --> ConvertOptions
    ConvertOptions --> DocxBuilder
```

### 4. Gantt Chart
```mermaid
gantt
    title Documentation Project Schedule
    dateFormat  YYYY-MM-DD
    section Phase 1
    Typography & Structure Analysis :done,    des1, 2026-10-01, 2026-10-03
    Office OpenXML Implementation   :active,  des2, 2026-10-04, 3d
    section Phase 2
    BiDi & Table Verification       :         des3, after des2, 4d
    Production Release              :         des4, after des3, 2d
```

---

## Microsoft Word (DOCX) Deep Dive

MdPersia generates native OpenXML documents with:
1. **Full RTL Page View**: Paragraphs, lists, and tables align to the right margin.
2. **Dedicated Persian Fonts**: `Vazirmatn` as primary, `Tahoma` as fallback, and `Consolas` for code.
3. **Automatic Footer Numbering**: Formatted page numbers ("صفحه X از Y") embedded in document footers.
4. **Resolution Scaling**: Control diagram sharpness with `--docx-image-scale 1..4`.
5. **Dimensions Clamping**: Set minimum/maximum diagram widths with `--docx-image-min-width 4.0` and `--docx-image-max-width 6.5`.

---

## Vector PDF Deep Dive

PDF generation uses Headless Chromium for crisp vector printing:
1. **Paper Formats**: Supports `A4`, `Letter`, `Legal`, `A3`, `A5` via `--page-format`.
2. **Page Margins**: Precise margins with `--margin 15mm` (supports `mm`, `in`, `px`).
3. **Landscape Layout**: Produce wide documents via `--landscape`.
4. **Custom Fonts**: Embed custom `.ttf` fonts with `--font-file` or `--font-dir`.
5. **Custom CSS**: Inject your own styling rules with `--css custom.css`.
6. **HTML Debugging**: Retain intermediate HTML with `--keep-html`.

---

## 🔀 Smart Markdown RTL Wrapping (RTL Markdown Deep Dive)

A distinctive feature of MdPersia is its **smart Markdown-to-Markdown transformer**, accessible via the **`RTL Markdown`** button in the desktop GUI header format bar, or via the **`--wrap-rtl`** CLI flag.

### Why Is This Needed?
Popular platforms such as **GitHub**, **GitLab**, **Obsidian**, **Notion**, and documentation static site generators (**VitePress**, **Docusaurus**) render Markdown left-to-right (LTR) by default. When authoring Persian or Arabic technical documentation, mixed-language sentences containing English identifiers, package names, formulas, or punctuation marks like `()` become inverted and fragmented.

This mode **does not convert to PDF or Word**; instead, it intelligently transforms the raw Markdown source so it renders perfectly right-to-left directly in browsers, GitHub previews, and Markdown editors.

### Technical Architecture & Safety (`rtl_wrapper.py`)
1. **Unicode Script Detection:** Scans text blocks using Persian/Arabic Unicode regex ranges along with zero-width non-joiners (`ZWNJ`), wrapping qualifying paragraphs in `<div dir="rtl">...</div>`.
2. **Code & Math Protection:**
   * Fenced code blocks (```` ``` ```` or `~~~`) remain strictly untouched and isolated in pure LTR.
   * Display math blocks (`$$...$$`) and HTML comments (`<!-- ... -->`) are preserved without modification.
3. **YAML Frontmatter Preservation:** Document-level metadata blocks (`--- ... ---`) at the start of Obsidian notes or blog posts are recognized and preserved.
4. **Idempotent Execution:** Tracks existing `<div dir="rtl">` tag nesting depth. Running the tool repeatedly on already-wrapped files will never produce duplicate or nested wrappers.

### Usage:

#### 1. Desktop GUI
In the Inspector Panel format bar (top right), choose **`RTL Markdown`**, then click **"تبدیل" (Convert)**.

#### 2. Command-Line Interface (CLI)
* **Batch wrap with `.rtl.md` suffix (default):**
  ```bash
  mdpersia ./docs --wrap-rtl
  ```
* **In-place overwrite (modifies files directly):**
  ```bash
  mdpersia ./docs --wrap-rtl --wrap-rtl-suffix ""
  ```
* **Custom suffix (e.g. `guide.fa.md`):**
  ```bash
  mdpersia ./guide.md --wrap-rtl --wrap-rtl-suffix "-fa"
  ```
* **Live watch mode:**
  ```bash
  mdpersia ./guide.md -w --wrap-rtl
  ```

#### 3. Python API
```python
from pathlib import Path
from mdpersia import wrap_rtl_in_markdown, wrap_rtl_in_file

# In-memory transformation
formatted_markdown = wrap_rtl_in_markdown(raw_markdown_text)

# Direct file transformation
output_file = wrap_rtl_in_file(Path("docs/guide.md"))
```

---

## Installation

### Via pip
```bash
pip install mdpersia
```

### From Source (Development)
```bash
git clone https://github.com/hamid-morsali-786/MdPersia.git
cd MdPersia

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

### Headless Chromium Setup
```bash
python -m playwright install chromium
```

---

## Quick Start & CLI Workflows

### Convert a single file to PDF
```bash
mdpersia ./docs/report.md
```

### Convert to Microsoft Word (DOCX)
```bash
mdpersia ./docs/report.md -f docx
```

### Batch convert an entire directory to custom destination
```bash
mdpersia ./docs -o ./output-folder -f docx
```

### Live Watch Mode
```bash
mdpersia ./docs/report.md -w -f pdf
```

### Automatically Wrap Existing Markdown Files
```bash
mdpersia ./notes --wrap-rtl
```

---

## Desktop Application (GUI)

Launch the visual application with:
```bash
mdpersia --gui
```
*Or double-click `run_gui.bat` on Windows.*

Features:
- **Batch Document Queue**: Drag & drop files and view processing progress.
- **5-Tab Inspector**: Configure Document, Style, Mermaid, Word, and Advanced options.
- **Console & Markdown Preview**: Real-time log streaming and instant preview.
- **Theme Support**: Seamless Light & Dark mode switching.

<p align="center">
  <img src="docs/screenshots/desktop-ui-light.png" width="850" alt="MdPersia Desktop Interface">
</p>

---

## Comprehensive CLI Options Reference

| Option | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `input` | Path | Required (unless `--gui`) | Input Markdown file or directory |
| `-o, --output` | Path | Alongside | Output file or destination directory |
| `-f, --format` | Choice | `pdf` | Output format: `pdf` or `docx` |
| `-w, --watch` | Flag | `False` | Watch input file/folder for live updates |
| `--gui` | Flag | `False` | Launch visual desktop interface |
| `--docx-image-scale` | 1-4 | `3` | Mermaid diagram resolution scale for Word |
| `--docx-image-min-width` | Float | `4.0` | Minimum diagram width in Word (inches) |
| `--docx-image-max-width` | Float | `6.5` | Maximum diagram width in Word (inches) |
| `--docx-font-size` | Int | `12` | Body text font size in points |
| `--page-format` | String | `A4` | PDF page size (`A4`, `Letter`, `Legal`, `A3`) |
| `--margin` | String | `15mm` | PDF page margins (`10mm`, `1in`, `20px`) |
| `--landscape` | Flag | Portrait | Generate landscape orientation documents |
| `--strip-emojis` | Flag | `False` | Strip emojis while preserving Persian ZWNJ |
| `--recursive` | Flag | `True` | Recursively scan subfolders for markdown |
| `--no-recursive` | Flag | - | Only convert files directly in input folder |
| `--extensions` | List | `.md .markdown` | Recognized markdown file extensions |
| `--font-family` | String | Vazirmatn | CSS font-family stack |
| `--font-file` | Path | - | Custom local font file |
| `--font-dir` | Path | `./fonts` | Directory containing Vazirmatn fonts |
| `--css` | Path | - | Custom stylesheet file |
| `--mermaid-js` | Path | `./vendor/mermaid.min.js` | Local Mermaid JavaScript file path for offline rendering |
| `--mermaid-url` | URL | - | Fallback remote CDN URL for Mermaid JavaScript |
| `--mermaid-theme` | Choice | `default` | Mermaid theme (`default`, `base`, `dark`, `forest`, `neutral`) |
| `--mermaid-timeout` | Int | `30000` | Diagram render timeout (milliseconds) |
| `--ignore-mermaid-errors` | Flag | `False` | Continue conversion if Mermaid fails |
| `--browsers-path` | Path | `./browsers` | Custom Playwright browsers path |
| `--keep-html` | Flag | `False` | Retain intermediate HTML file |
| `--fail-fast` | Flag | `False` | Abort batch conversion on first error |
| `--verbose` | Flag | `False` | Detailed logging output |
| `--wrap-rtl` | Flag | `False` | Inject `<div dir="rtl">` wrappers into markdown |
| `--wrap-rtl-suffix` | String | `.rtl` | Output suffix for wrapped markdown |

---

## Python API Reference

```python
from pathlib import Path
from mdpersia import build_jobs, convert_jobs, ConvertOptions, ConversionError

# 1. Configure conversion options
options = ConvertOptions(
    output_format="docx",
    font_family='"Vazirmatn", sans-serif',
    page_format="A4",
    margin="15mm",
    docx_font_size_pt=12,
    docx_image_scale=3,
    include_page_numbers=True,
    strip_emojis=False
)

# 2. Build the job queue
jobs = build_jobs(
    input_path=Path("./docs/architecture.md"),
    output=Path("./dist/architecture.docx"),
    output_format=options.output_format
)

# 3. Execute conversion
try:
    results = convert_jobs(jobs, options=options, fail_fast=True)
    success_count = sum(1 for r in results if r.ok)
    print(f"Conversion completed: {success_count} succeeded, {len(results) - success_count} failed.")
except ConversionError as err:
    print(f"Conversion error: {err}")
```

---

## CI/CD & Enterprise Automation

```yaml
name: Compile Documents

on:
  push:
    branches: [ main ]

jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install MdPersia
        run: |
          pip install mdpersia
          python -m playwright install --with-deps chromium
      - name: Compile PDF and Word Documentation
        run: |
          mdpersia docs/ -o dist/pdf/ -f pdf
          mdpersia docs/ -o dist/docx/ -f docx
      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: compiled-docs
          path: dist/
```

---

## Architecture

```mermaid
flowchart TD
    MD[Input Markdown File] --> Parser[Markdown-It-Py Parser]
    
    subgraph Core Processing Pipeline
        Parser --> AST[Syntax Tree AST]
        AST --> BiDi[BiDi RTL Engine & Isolation]
        AST --> MermaidExt[Mermaid Diagram Extractor]
    end

    MermaidExt --> LocalMermaid[Offline Mermaid.js]
    LocalMermaid --> Chromium[Headless Chromium]
    Chromium --> PNG[High-Resolution PNGs]

    BiDi --> HTMLGen[Vector HTML Generator]
    PNG --> HTMLGen
    HTMLGen --> ChromiumPDF[Chromium PDF Engine]
    ChromiumPDF --> PDFOut[(Vector PDF Document)]

    BiDi --> DocxGen[Office OpenXML Builder]
    PNG --> DocxGen
    DocxGen --> WordOut[(Native Word .docx Document)]
```

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=hamid-morsali-786/MdPersia&type=Date)](https://star-history.com/#hamid-morsali-786/MdPersia&Date)

---

## Contributing

We welcome contributions from the community!  
Please see our [Contributing Guide](CONTRIBUTING.md), [Code of Conduct](CODE_OF_CONDUCT.md), and [Security Policy](SECURITY.md).

---

## Author & License

Created and maintained with ❤️ by **[Hamid Morsali](https://github.com/hamid-morsali-786)**.

Licensed under the **[MIT License](LICENSE)**.
