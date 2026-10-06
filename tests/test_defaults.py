from pathlib import Path

from fa_md_pdf.defaults import (
    default_browsers_path,
    default_fonts_path,
    default_mermaid_path,
    find_project_root,
    resolve_user_path,
)


def test_find_project_root_from_docs_folder(tmp_path: Path):
    project = tmp_path / "project"
    docs = project / "docs"
    vendor = project / "vendor"

    docs.mkdir(parents=True)
    vendor.mkdir()
    (vendor / "mermaid.min.js").write_text("window.mermaid = {};", encoding="utf-8")

    assert find_project_root(docs / "intro.md", cwd=docs) == project


def test_default_asset_paths(tmp_path: Path):
    assert default_mermaid_path(tmp_path) == tmp_path / "vendor" / "mermaid.min.js"
    assert default_browsers_path(tmp_path) == tmp_path / "browsers"
    assert default_fonts_path(tmp_path) == tmp_path / "fonts"


def test_resolve_user_path_prefers_cwd_existing_file(tmp_path: Path, monkeypatch):
    project = tmp_path / "project"
    cwd = tmp_path / "cwd"
    project.mkdir()
    cwd.mkdir()
    file_in_cwd = cwd / "x.css"
    file_in_cwd.write_text("body {}", encoding="utf-8")

    monkeypatch.chdir(cwd)

    assert resolve_user_path(Path("x.css"), project) == file_in_cwd.resolve()


def test_find_preferred_font_file(tmp_path: Path):
    from fa_md_pdf.defaults import find_preferred_font_file

    fonts = tmp_path / "fonts"
    fonts.mkdir()
    assert find_preferred_font_file(fonts) is None

    (fonts / "Vazirmatn-Medium.ttf").write_text("", encoding="utf-8")
    assert find_preferred_font_file(fonts) == (fonts / "Vazirmatn-Medium.ttf").resolve()

    (fonts / "Vazirmatn-Regular.ttf").write_text("", encoding="utf-8")
    assert find_preferred_font_file(fonts) == (fonts / "Vazirmatn-Regular.ttf").resolve()

