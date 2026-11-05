"""Lossless reads and revision-checked atomic saves shared by both desktop runtimes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

MAX_DOCUMENT_BYTES = 16 * 1024 * 1024


class DocumentError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def document_path(value: str, *, must_exist: bool = True) -> Path:
    if not isinstance(value, str) or not value or "\0" in value:
        raise DocumentError("INVALID", "مسیر سند معتبر نیست.")
    source = Path(value).resolve()
    if source.suffix.lower() not in {".md", ".markdown"}:
        raise DocumentError("INVALID", "فقط فایل Markdown قابل ویرایش است.")
    if must_exist and not source.is_file():
        raise DocumentError("NOT_FOUND", "فایل پیدا نشد؛ می‌توانید پیش‌نویس را با نام دیگری ذخیره کنید.")
    return source


def normalized_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


BOM_ENCODINGS = {name: "\ufeff".encode(name) for name in
                 ("utf-32-le", "utf-32-be", "utf-16-le", "utf-16-be")}


def decode_markdown(raw: bytes) -> tuple[str, str]:
    for encoding, marker in BOM_ENCODINGS.items():
        if raw.startswith(marker):
            return raw[len(marker):].decode(encoding), encoding
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        return raw.decode(encoding), encoding
    except UnicodeDecodeError:
        return raw.decode("cp1256"), "cp1256"


def snapshot(source: Path, raw: bytes) -> dict:
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise DocumentError("TOO_LARGE", "حداکثر حجم سند برای ویرایش ۱۶ مگابایت است.")
    try:
        text, encoding = decode_markdown(raw)
    except UnicodeDecodeError as error:
        raise DocumentError("ENCODING", "رمزگذاری فایل قابل تشخیص نیست؛ اصل فایل تغییر نکرده است.") from error
    endings = re.findall(r"\r\n|\r|\n", text)
    newline = max(dict.fromkeys(endings), key=endings.count) if endings else "\n"
    return {"path": str(source), "text": normalized_text(text), "revision": hashlib.sha256(raw).hexdigest(),
            "encoding": encoding, "newline": newline, "sizeBytes": len(raw),
            "readOnly": not bool(source.stat().st_mode & stat.S_IWRITE)}


def read_document(path: str) -> dict:
    source = document_path(path)
    if source.stat().st_size > MAX_DOCUMENT_BYTES:
        raise DocumentError("TOO_LARGE", "حداکثر حجم سند برای ویرایش ۱۶ مگابایت است.")
    return snapshot(source, source.read_bytes())


@contextmanager
def document_lock(source: Path):
    """Coordinate saves from multiple application windows/processes without touching the document."""
    directory = Path(tempfile.gettempdir()) / "mdpersia-document-locks"
    directory.mkdir(exist_ok=True)
    name = hashlib.sha256(os.path.normcase(str(source)).encode()).hexdigest()
    with (directory / name).open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        if sys.platform == "win32":
            import msvcrt
            deadline = time.monotonic() + 5
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise DocumentError("BUSY", "ذخیرهٔ دیگری در حال انجام است؛ دوباره تلاش کنید.") from None
                    time.sleep(.02)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def save_document(path: str, text: str, revision: str | None, *, utf8: bool = False) -> dict:
    source = document_path(path, must_exist=False)
    if not isinstance(text, str):
        raise DocumentError("INVALID", "متن سند معتبر نیست.")
    if revision is not None and (not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{64}", revision)):
        raise DocumentError("INVALID", "نسخهٔ مبنای ذخیره معتبر نیست.")
    if len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise DocumentError("TOO_LARGE", "حداکثر حجم سند برای ویرایش ۱۶ مگابایت است.")
    text = normalized_text(text)
    with document_lock(source):
        existing = read_document(str(source)) if source.exists() else None
        if (existing is None and revision is not None) or (existing is not None and existing["revision"] != revision):
            raise DocumentError("CONFLICT", "فایل روی دیسک تغییر کرده است؛ برای حفظ هر دو نسخه، با نام دیگری ذخیره کنید یا نسخهٔ دیسک را بازخوانی کنید.")
        if existing and existing["readOnly"]:
            raise DocumentError("READ_ONLY", "فایل فقط‌خواندنی است؛ از ذخیره با نام دیگر استفاده کنید.")
        if existing and text == existing["text"] and not utf8:
            return existing
        encoding = "utf-8" if utf8 or not existing else existing["encoding"]
        newline = existing["newline"] if existing else "\n"
        try:
            content = BOM_ENCODINGS.get(encoding, b"") + text.replace("\n", newline).encode(encoding)
        except UnicodeEncodeError as error:
            raise DocumentError("ENCODING", "برخی نویسه‌ها در رمزگذاری قدیمی فایل قابل ذخیره نیستند؛ با نام دیگر و UTF-8 ذخیره کنید.") from error
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=f".{source.name}.", suffix=".tmp", dir=source.parent)
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if existing:
                os.chmod(temporary, stat.S_IMODE(source.stat().st_mode))
            # Recheck after flushing the temporary file, immediately before replacing the original.
            current = hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None
            if current != revision or document_path(path, must_exist=False) != source:
                raise DocumentError("CONFLICT", "فایل هنگام ذخیره تغییر کرد؛ اصل فایل بازنویسی نشد.")
            if revision is None:
                # Exclusive creation avoids an overwrite race when saving a new copy.
                try:
                    os.link(temporary, source)
                    os.unlink(temporary)
                except OSError:
                    # Fallback for filesystems without hardlink support (e.g. FAT32/exFAT/shares)
                    os.replace(temporary, source)
            else:
                os.replace(temporary, source)
            temporary = None
            return snapshot(source, content)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)


def document_operation(request: dict) -> dict:
    if request.get("operation") == "read":
        return read_document(request["path"])
    if request.get("operation") == "save":
        return save_document(request["path"], request["text"], request.get("revision"), utf8=request.get("utf8") is True)
    raise DocumentError("INVALID", "عملیات سند معتبر نیست.")


if __name__ == "__main__":
    try:
        response = {"document": document_operation(json.loads(sys.stdin.buffer.read().decode("utf-8")))}
    except Exception as error:
        response = {"error": str(error), "code": getattr(error, "code", "IO")}
    sys.stdout.buffer.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))
