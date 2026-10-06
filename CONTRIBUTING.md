# Contributing to MdPersia

Thank you for your interest in contributing to **MdPersia**! 🎉  
We welcome contributions of all kinds: bug reports, bug fixes, feature proposals, documentation improvements, test enhancements, and new design presets.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat all contributors and users with kindness, respect, and empathy.

---

## Development Setup

### 1. Prerequisites
- **Python 3.11+**
- Git

### 2. Fork and Clone
```bash
git clone https://github.com/hamid-morsali-786/MdPersia.git
cd MdPersia
```

### 3. Create a Virtual Environment
```bash
# On Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# On Windows PowerShell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
Install MdPersia in editable mode along with development dependencies:
```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 5. Install Playwright Browsers (if running headless tests without bundled browsers)
```bash
python -m playwright install chromium
```

---

## Running Tests & Linters

We use **Pytest** for testing and **Ruff** for linting. Always make sure tests and lint checks pass before submitting a pull request.

### Run Tests
```bash
pytest
```

### Run Ruff Linter
```bash
ruff check src tests
```

---

## Contribution Workflow

1. **Create an Issue**: Check existing issues first. If none exists, open an issue to discuss your proposed change or report a bug.
2. **Branch from `main`**:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```
3. **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add custom callout styling options`
   - `fix: correct table border alignment in DOCX`
   - `docs: update CLI examples in README`
   - `test: add edge cases for mixed-direction brackets`
4. **Push and Open a Pull Request**: Push your branch to GitHub and open a PR against `main`. Provide a descriptive PR summary matching the PR template.

---

## Coding Guidelines

- **RTL Integrity**: All text parsing and HTML/DOCX transformation logic must respect BiDi (Bidirectional) text rules and unicode isolation.
- **Offline-First Principle**: Do not introduce mandatory network calls or external CDN dependencies for default workflows. Assets must function standalone.
- **Type Annotations**: All new functions and public APIs should include type hints (`from __future__ import annotations`).
- **Tests**: Every new feature or bug fix must come with accompanying automated tests in `tests/`.

---

Thank you for helping make Persian and RTL document authoring better for everyone! 🚀
