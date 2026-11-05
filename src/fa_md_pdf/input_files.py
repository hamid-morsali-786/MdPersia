"""Markdown discovery shared by conversion and the small desktop reader."""
from pathlib import Path
from typing import Iterable


def normalize_extensions(values: Iterable[str]) -> tuple[str, ...]:
    exts = tuple(dict.fromkeys(f".{v.strip().lstrip('.').lower()}" for v in values if v.strip()))
    return exts or ('.md', '.markdown')


def is_markdown_file(path: Path, extensions: Iterable[str]) -> bool:
    return path.is_file() and path.suffix.lower() in set(normalize_extensions(extensions))


def discover_markdown_files(input_dir: Path, recursive: bool, extensions: Iterable[str]) -> list[Path]:
    normalized = normalize_extensions(extensions)
    pattern = '**/*' if recursive else '*'
    return sorted(path for path in input_dir.glob(pattern) if is_markdown_file(path, normalized))


def output_for_file(
    source: Path, input_root: Path | None, output: Path | None,
    output_format: str = 'pdf', target_name: str | None = None,
) -> Path:
    target_name = target_name or source.with_suffix(f'.{output_format}').name
    target_suffixes = {'.pdf', '.docx', '.md', '.markdown'}
    if output is None:
        return source.parent / target_name
    if input_root is None:
        return output if output.suffix.lower() in target_suffixes else output / target_name
    relative = source.relative_to(input_root)
    return output / relative.parent / target_name
