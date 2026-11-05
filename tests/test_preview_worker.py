"""The persistent desktop renderer must keep requests isolated and recover from failures."""
from __future__ import annotations

import io
import json
from pathlib import Path

from fa_md_pdf.preview_worker import serve


def render_requests(root: Path, requests: list[dict | str]) -> list[dict]:
    source = io.StringIO("\n".join(item if isinstance(item, str) else json.dumps(item) for item in requests) + "\n")
    output = io.StringIO()
    serve(root, source, output)
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_consecutive_documents_never_replay_the_first_file(tmp_path):
    a = tmp_path / "first.md"
    b = tmp_path / "فایل بعدی.MD"
    a.write_text("# First document", encoding="utf-8")
    b.write_text("# سند دوم\n\n- Host: localhost برای اتصال", encoding="utf-8-sig")
    first, second = render_requests(tmp_path, [{"id": 1, "path": str(a)}, {"id": 2, "path": str(b)}])
    assert first["id"] == 1 and "First document" in first["html"]
    assert second["id"] == 2 and "سند دوم" in second["html"]
    assert "First document" not in second["html"]
    assert "<bdi>Host:" in second["html"]


def test_invalid_requests_and_missing_files_do_not_kill_the_worker(tmp_path):
    document = tmp_path / "valid.md"
    document.write_text("# Still alive", encoding="utf-8")
    replies = render_requests(tmp_path, ["broken JSON", {"id": 2, "path": str(tmp_path / "missing.md")},
                                         {"id": 3, "path": str(document)}])
    assert "error" in replies[0]
    assert replies[1]["id"] == 2 and "error" in replies[1]
    assert "Still alive" in replies[2]["html"]


def test_legacy_persian_encoding_uses_the_same_safe_reader(tmp_path):
    document = tmp_path / "legacy.markdown"
    document.write_bytes("# متن عربي قديم".encode("cp1256"))
    result, = render_requests(tmp_path, [{"id": 1, "path": str(document)}])
    assert "متن عربي قديم" in result["html"]


def test_plain_documents_do_not_request_mermaid_or_a_cdn(tmp_path):
    document = tmp_path / "plain.md"
    document.write_text("# A plain document", encoding="utf-8")
    result, = render_requests(tmp_path, [{"id": 1, "path": str(document)}])
    assert '<script src=' not in result["html"]
    assert "cdn.jsdelivr" not in result["html"]


def test_in_memory_preview_never_modifies_source_and_uses_nonce_policy(tmp_path):
    source = tmp_path / "draft.md"
    source.write_text("# Original", encoding="utf-8")
    result, = render_requests(tmp_path, [{"id": 1, "path": str(source), "text": '# پیش‌نویس\n\n<script>window.BAD=true</script>\n\n```mermaid\ngraph LR\nA-->B\n```'}])
    assert "پیش‌نویس" in result["html"]
    assert source.read_text() == "# Original"
    assert "Content-Security-Policy" in result["html"]
    assert "<script nonce=" in result["html"]
    assert "<script>window.BAD=true</script>" in result["html"]


def test_worker_shares_safe_document_read_save_and_reports_conflicts(tmp_path):
    source = tmp_path / "safe.md"
    source.write_text("# Original", encoding="utf-8")
    read, = render_requests(tmp_path, [{"id": 1, "operation": "read", "path": str(source)}])
    good, conflict = render_requests(tmp_path, [
        {"id": 2, "operation": "save", "path": str(source), "text": "# Saved", "revision": read["document"]["revision"]},
        {"id": 3, "operation": "save", "path": str(source), "text": "# Lost", "revision": read["document"]["revision"]},
    ])
    assert good["document"]["text"] == "# Saved"
    assert conflict["code"] == "CONFLICT"
    assert source.read_text() == "# Saved"
