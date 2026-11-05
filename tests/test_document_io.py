from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from fa_md_pdf.document_io import DocumentError, read_document, save_document


@pytest.mark.parametrize("encoding,bom,newline", [("utf-8", b"", "\n"), ("utf-8-sig", b"\xef\xbb\xbf", "\r\n"), ("cp1256", b"", "\r\n"), ("utf-8", b"", "\r")])
def test_save_preserves_encoding_bom_newlines_and_final_newline(tmp_path, encoding, bom, newline):
    source = tmp_path / "سند با فاصله.MD"
    source.write_bytes(("# متن عربي" + newline + "- Host: localhost" + newline).encode(encoding))
    loaded = read_document(str(source))
    assert loaded["text"] == "# متن عربي\n- Host: localhost\n"
    saved = save_document(str(source), loaded["text"] + "پايان\n", loaded["revision"])
    assert source.read_bytes() == ("# متن عربي" + newline + "- Host: localhost" + newline + "پايان" + newline).encode(encoding)
    assert source.read_bytes().startswith(bom)
    assert saved["revision"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_noop_save_keeps_mixed_newlines_byte_for_byte(tmp_path):
    source = tmp_path / "mixed.md"
    original = b"# Title\r\nline\nlast\r"
    source.write_bytes(original)
    loaded = read_document(str(source))
    save_document(str(source), loaded["text"], loaded["revision"])
    assert source.read_bytes() == original


def test_conflict_never_overwrites_external_edit_or_deleted_file(tmp_path):
    source = tmp_path / "conflict.md"
    source.write_text("# Original", encoding="utf-8")
    loaded = read_document(str(source))
    source.write_text("# External", encoding="utf-8")
    with pytest.raises(DocumentError, match="فایل روی دیسک") as error:
        save_document(str(source), "# My draft", loaded["revision"])
    assert error.value.code == "CONFLICT"
    assert source.read_text() == "# External"
    source.unlink()
    with pytest.raises(DocumentError) as error:
        save_document(str(source), "# My draft", loaded["revision"])
    assert error.value.code == "CONFLICT"
    assert not source.exists()


def test_legacy_encoding_failure_keeps_original_and_utf8_copy_succeeds(tmp_path):
    source = tmp_path / "legacy.md"
    original = "# متن عربي".encode("cp1256")
    source.write_bytes(original)
    loaded = read_document(str(source))
    with pytest.raises(DocumentError) as error:
        save_document(str(source), loaded["text"] + "\n中文", loaded["revision"])
    assert error.value.code == "ENCODING"
    assert source.read_bytes() == original
    target = tmp_path / "copy.markdown"
    save_document(str(target), loaded["text"] + "\n中文", None, utf8=True)
    assert target.read_text(encoding="utf-8").endswith("中文")


def test_new_copy_never_silently_replaces_existing_document(tmp_path):
    source = tmp_path / "existing.md"
    source.write_text("keep", encoding="utf-8")
    with pytest.raises(DocumentError) as error:
        save_document(str(source), "replace", None)
    assert error.value.code == "CONFLICT"
    assert source.read_text() == "keep"


def test_flush_failure_preserves_original_and_cleans_temporary_file(tmp_path, monkeypatch):
    source = tmp_path / "safe.md"
    source.write_text("original", encoding="utf-8")
    loaded = read_document(str(source))
    def fail(_fd):
        raise OSError("disk full")
    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="disk full"):
        save_document(str(source), "replacement", loaded["revision"])
    assert source.read_text() == "original"
    assert list(tmp_path.iterdir()) == [source]


def test_concurrent_saves_from_same_revision_cannot_both_succeed(tmp_path):
    source = tmp_path / "concurrent.md"
    source.write_text("original", encoding="utf-8")
    revision = read_document(str(source))["revision"]
    def save(text):
        try:
            save_document(str(source), text, revision)
            return "saved"
        except DocumentError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ["first", "second"])) == ["CONFLICT", "saved"]
    assert source.read_text() in {"first", "second"}


def test_readonly_file_is_not_replaced(tmp_path):
    source = tmp_path / "readonly.md"
    source.write_text("keep", encoding="utf-8")
    loaded = read_document(str(source))
    source.chmod(0o444)
    try:
        with pytest.raises(DocumentError) as error:
            save_document(str(source), "replace", loaded["revision"])
        assert error.value.code == "READ_ONLY"
        assert source.read_text() == "keep"
    finally:
        source.chmod(0o666)


def test_detect_external_change_while_flushing(tmp_path, monkeypatch):
    source = tmp_path / "racing.md"
    source.write_text("original", encoding="utf-8")
    loaded = read_document(str(source))
    flush = os.fsync
    def outside_edit(fd):
        flush(fd)
        source.write_text("external", encoding="utf-8")
    monkeypatch.setattr(os, "fsync", outside_edit)
    with pytest.raises(DocumentError) as error:
        save_document(str(source), "my draft", loaded["revision"])
    assert error.value.code == "CONFLICT"
    assert source.read_text() == "external"


def test_editor_refuses_non_markdown_and_invalid_revisions(tmp_path):
    with pytest.raises(DocumentError):
        save_document(str(tmp_path / "script.py"), "oops", None)
    with pytest.raises(DocumentError):
        save_document(str(tmp_path / "valid.md"), "oops", "invalid revision")
    assert not list(tmp_path.iterdir())
