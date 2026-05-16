from pathlib import Path

from fa_md_pdf.converter import build_jobs, discover_markdown_files, normalize_extensions


def test_normalize_extensions():
    assert normalize_extensions(["md", ".markdown", "MD"]) == (".md", ".markdown")


def test_discover_markdown_files(tmp_path: Path):
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.markdown").write_text("# C", encoding="utf-8")

    files = discover_markdown_files(tmp_path, recursive=True, extensions=[".md", ".markdown"])

    assert [path.name for path in files] == ["a.md", "c.markdown"]


def test_build_jobs_single_file_default_output(tmp_path: Path):
    source = tmp_path / "intro.md"
    source.write_text("# Intro", encoding="utf-8")

    jobs = build_jobs(source, output=None)

    assert len(jobs) == 1
    assert jobs[0].output == source.with_suffix(".pdf")


def test_build_jobs_directory_preserves_structure_with_output_dir(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    nested = docs / "nested"
    nested.mkdir()
    source = nested / "intro.md"
    source.write_text("# Intro", encoding="utf-8")

    out = tmp_path / "out"
    jobs = build_jobs(docs, output=out)

    assert jobs[0].output == out / "nested" / "intro.pdf"
