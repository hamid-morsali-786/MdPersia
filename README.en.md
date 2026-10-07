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
  <img src="docs/screenshots/desktop-ui-light.png" width="900" alt="MdPersia Desktop Application - Light Theme">
</p>

</div>

---

## Table of Contents

- [Overview & Why MdPersia](#why-mdpersia)
- [Key Features](#features)
- [Feature Comparison Matrix](#comparison-matrix)
- [Installation](#installation)
- [Quick Start](#quickstart)
- [Desktop Application (GUI)](#desktop-application-gui)
- [CLI Options Reference](#cli-options-reference)
- [Python API Usage](#python-api)
- [Architecture](#architecture)
- [Star History](#star-history)
- [Contributing & License](#contributing)

---

## Why MdPersia?

Converting technical Markdown files containing **Persian / Arabic (RTL)** text into publishable documents has historically been challenging:

- ❌ **Flipped Punctuation & Mixed Text**: English terms, version numbers, brackets `()` and code blocks within Persian text frequently flip direction in traditional PDF generators.
- ❌ **Broken Word (DOCX) Tables & Layouts**: Generic converters produce left-to-right Word files where text clings to the wrong side and tables lose alignment.
- ❌ **Failed Mermaid Rendering**: System architecture diagrams, flowcharts, and sequence diagrams rarely render without external internet connections or complex LaTeX toolchains.

**MdPersia** solves this definitively. It provides a rock-solid, offline-first pipeline that renders Markdown files with accurate BiDi text direction, beautiful Persian typography (Vazirmatn), crystal-clear Mermaid diagrams, and exports them directly to both **vector PDF** and **native Microsoft Word (DOCX)**.

---

## Features

- 📑 **Dual Native Outputs**: Generate publication-grade **PDFs** via headless Chromium, or fully editable, RTL-configured **Word (.docx)** files.
- 📐 **First-Class Mermaid Support**: Flowcharts, Sequence Diagrams, Gantt charts, and Class diagrams are automatically rendered and embedded.
- 🔒 **100% Offline-First**: Zero runtime calls to external CDNs. Bundles local Chromium support, embedded Vazirmatn fonts, and local Mermaid JavaScript.
- 🔄 **Real-Time Watch Mode (`-w` / `--watch`)**: Automatically re-compiles documents on file save.
- 📦 **Batch Directory Conversion**: Converts entire documentation folders while preserving hierarchical directory structures.
- 🪄 **Intelligent Markdown Repair (`--wrap-rtl`)**: Automatically wraps Persian paragraphs with `<div dir="rtl">` without touching code blocks or existing markup.
- 🖥️ **Both CLI and Modern GUI**: Seamless command-line interface for CI/CD and scripts, plus a clean graphical interface with full light/dark theme support.

---

## Comparison Matrix

| Feature | MdPersia | Pandoc + XeLaTeX | VS Code Markdown-PDF | Typora Export |
| :--- | :---: | :---: | :---: | :---: |
| **Persian / RTL Accuracy** | **Flawless (Native)** | Complex Config | Inconsistent | Good |
| **Native Word (.docx) RTL** | **Yes (Full RTL)** | Basic / LTR Defaults | No | Basic |
| **Offline Mermaid Diagrams** | **Built-in** | Requires Filters | Requires Internet | Partial |
| **Zero External Setup** | **Yes (Standalone)** | Requires >4GB TeXLive | Requires Extension | Closed Source |
| **Batch Folder Processing** | **Yes** | Manual Scripting | Manual | No |
| **Live Watch Daemon** | **Yes (`-w`)** | No | No | No |
| **Graphical User Interface** | **Yes (GUI included)** | No | Editor GUI | Editor GUI |

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

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Headless Browser Setup (One-time)

If you have an internet connection during setup:
```bash
python -m playwright install chromium
```

> **Offline Portable Mode:** Place your Chromium binaries in `./browsers/`, fonts in `./fonts/`, and `mermaid.min.js` in `./vendor/`. MdPersia automatically detects them without requiring any internet access!

---

## Quickstart

### 1. Convert a single file to PDF
```bash
mdpersia ./docs/sample.md
```
*Creates `./docs/sample.pdf`.*

### 2. Convert to Microsoft Word (DOCX)
```bash
mdpersia ./docs/sample.md -f docx
```
*Creates `./docs/sample.docx` with right-to-left layout and styled tables.*

### 3. Convert an entire folder with custom output directory
```bash
mdpersia ./docs -o ./dist -f pdf
```

### 4. Watch for changes in real time
```bash
mdpersia ./docs/specification.md -w -f pdf
```

### 5. Launch the Graphical User Interface
```bash
mdpersia --gui
```
*Or double-click `run_gui.bat` on Windows.*

---

## Desktop Application (GUI)

MdPersia features a desktop interface with:
- **Interactive File Queue**: Drag & drop or browse files/folders with individual status indicators.
- **Inspector Panel**: Configure page margins, paper format (A4, Letter, A3), orientation, Mermaid themes, and font size.
- **Console & Live Log**: Streaming output of conversion jobs with fail-fast toggles.
- **One-Click Format Switch**: Toggle between PDF, DOCX, and Markdown RTL wrapping.

<p align="center">
  <img src="docs/screenshots/desktop-ui-light.png" width="850" alt="MdPersia Desktop Interface">
</p>

---

## Architecture

```mermaid
flowchart LR
    A[Markdown File<br/>fa-text.md] --> B{MdPersia Engine}
    B -->|Parse & RTL Guard| C[Markdown-It-Py AST]
    C -->|Diagram Extraction| D[Local Mermaid Engine]
    D --> E[Headless Chromium]
    E -->|Print to PDF| F[Vector PDF File]
    C -->|Docx AST Builder| G[Python-docx + RTL XML]
    D -->|High-Res PNG| G
    G --> H[Microsoft Word .docx]
```

---

## Python API

You can easily integrate MdPersia into your own Python applications:

```python
from pathlib import Path
from mdpersia import build_jobs, convert_jobs, ConvertOptions

options = ConvertOptions(
    format="docx",       # "pdf" or "docx"
    font_family='"Vazirmatn", sans-serif',
    page_format="A4",
    margin="15mm"
)

jobs = build_jobs(
    input_path=Path("./docs/architecture.md"),
    options=options
)

success, failed = convert_jobs(jobs)
print(f"Completed: {success} succeeded, {failed} failed.")
```

---

## CLI Options Reference

| Flag | Description | Default |
| :--- | :--- | :--- |
| `input` | File or folder containing Markdown files | Current directory |
| `-o, --output` | Output file path or destination folder | Next to source file |
| `-f, --format` | Output format: `pdf` or `docx` | `pdf` |
| `-w, --watch` | Watch file/folder for live auto-conversion | `False` |
| `--gui` | Launch graphical desktop window | `False` |
| `--docx-image-scale` | Diagram resolution multiplier for Word (1-4) | `3` |
| `--page-format` | PDF page size (`A4`, `Letter`, `Legal`) | `A4` |
| `--margin` | Page margin (e.g., `15mm`, `1in`, `20px`) | `15mm` |
| `--landscape` | Produce landscape orientation documents | Portrait |
| `--strip-emojis` | Strip emojis from converted documents | `False` |
| `--wrap-rtl` | Automatically inject `<div dir="rtl">` tags | `False` |

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=hamid-morsali-786/MdPersia&type=Date)](https://star-history.com/#hamid-morsali-786/MdPersia&Date)

---

## Contributing

We welcome contributions from the community!  
Please see our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) for details on submitting pull requests.

---

## Author & License

Created and maintained with ❤️ by **[Hamid Morsali](https://github.com/hamid-morsali-786)**.

Licensed under the **[MIT License](LICENSE)**.
