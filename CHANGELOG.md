# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2026-11-05

### Added
- Official standalone Windows Installer (`MdPersia-0.3.0-x64-Setup.exe`, ~15 MB) powered by Tauri v2 and NSIS with zero prerequisite installation.
- Native Windows file associations for `.md` and `.markdown` files with custom MdPersia branding and icons.
- Bilingual LaTeX Math rendering support (`math_renderer.py`, `word_math.py`) completely offline across PDF and Word (DOCX).
- Smart BiDi algorithm with colon isolation for bilingual Persian-English text, completely resolving text inversion in Word (Issue #1).
- Official PyPI distribution: global installation via `pip install mdpersia` (Issue #5).
- Modular architecture separating the lightweight reading engine (< 16 MB) from optional heavy conversion resources.
- Expanded test suite to 205 automated tests with visual regression baselines and module contracts.
- Collapsible workspace output sidebar and centered reading layout in desktop interface.

### Changed
- Promoted project release to stable version `0.3.0`.
- Streamlined GitHub Actions release pipeline with automated tag builds and asset verification.
- Improved Word document formatting, native multi-level numbering, and document metadata extraction.

## [0.2.0] - 2026-10-06

### Added
- Official rebranding to **MdPersia** with unified CLI executable `mdpersia` and backwards-compatible `fa-md-pdf`.
- Python API support under both `import mdpersia` and `import fa_md_pdf`.
- Full native DOCX (Microsoft Word) generation with correct RTL text flow and paragraph alignments.
- High-resolution vector-quality image conversion for Mermaid diagrams embedded into Word documents.
- Batch directory conversion with recursive scanning and configurable output destinations.
- Modern GUI options: Native Tkinter interface and cross-platform Tauri desktop client.
- Built-in `--wrap-rtl` transformation engine for Markdown files missing explicit RTL wrappers.
- File-watching daemon (`-w` / `--watch`) for auto-recompiling documents upon edits.
- GitHub Actions CI pipeline with multi-version Python (3.11, 3.12, 3.13) and cross-platform matrix (Linux, Windows).
- Complete test suite with 110+ automated tests covering edge cases, BiDi text handling, and Mermaid pipelines.

### Changed
- Upgraded Playwright and markdown rendering pipeline for 100% offline-first execution without external CDN requests.
- Bundled default Persian Vazirmatn fonts with automatic local discovery.
- Enhanced table formatting in Word documents with customized headers and cell borders.

---

## [0.1.0] - 2026-05-12

### Added
- Initial release of Persian Markdown to PDF converter.
- Mermaid diagram rendering via headless Chromium.
- Custom CSS styling and PDF layout options (A4, Letter, Margins).
