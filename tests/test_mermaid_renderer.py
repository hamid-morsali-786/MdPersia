"""
Tests for Mermaid rendering to PNG using Playwright and offline Mermaid JS.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from fa_md_pdf.mermaid_renderer import render_mermaid_to_png


def test_render_mermaid_empty_list():
    assert render_mermaid_to_png([], mermaid_source="vendor/mermaid.min.js") == {}


def test_render_mermaid_deduplication(vendor_mermaid: Path):
    if not vendor_mermaid.is_file():
        pytest.skip("Offline mermaid.min.js not found in vendor")

    code = "graph TD\n    A[شروع] --> B[پایان]"
    # Pass duplicate code in list
    result = render_mermaid_to_png(
        [code, code],
        mermaid_source=str(vendor_mermaid),
        timeout_ms=15_000,
    )

    assert len(result) == 1
    assert code in result
    png_path = result[code]
    assert png_path.is_file()
    assert png_path.stat().st_size > 0
    # Verify PNG magic number
    header = png_path.read_bytes()[:8]
    assert header == b"\x89PNG\r\n\x1a\n"


def test_render_mermaid_multiple_diagrams(vendor_mermaid: Path):
    if not vendor_mermaid.is_file():
        pytest.skip("Offline mermaid.min.js not found in vendor")

    diag1 = "graph LR\n    Client --> Server"
    diag2 = "flowchart TD\n    Node1 --> Node2"

    result = render_mermaid_to_png(
        [diag1, diag2],
        mermaid_source=str(vendor_mermaid),
        mermaid_theme="dark",
        device_scale_factor=2,
        timeout_ms=15_000,
    )

    assert len(result) == 2
    assert diag1 in result
    assert diag2 in result
    assert result[diag1] != result[diag2]
    assert result[diag1].is_file()
    assert result[diag2].is_file()


def test_render_mermaid_syntax_error_raises_exception(vendor_mermaid: Path):
    if not vendor_mermaid.is_file():
        pytest.skip("Offline mermaid.min.js not found in vendor")

    invalid_code = "graph INVALID_SYNTAX_###_@@@"
    with pytest.raises(RuntimeError, match="Mermaid render error"):
        render_mermaid_to_png(
            [invalid_code],
            mermaid_source=str(vendor_mermaid),
            ignore_errors=False,
            timeout_ms=10_000,
        )


def test_render_mermaid_syntax_error_ignored_when_flag_set(vendor_mermaid: Path):
    if not vendor_mermaid.is_file():
        pytest.skip("Offline mermaid.min.js not found in vendor")

    invalid_code = "graph INVALID_SYNTAX_###_@@@"
    # Should not raise when ignore_errors is True
    result = render_mermaid_to_png(
        [invalid_code],
        mermaid_source=str(vendor_mermaid),
        ignore_errors=True,
        timeout_ms=10_000,
    )
    assert invalid_code not in result


def test_render_mermaid_timeout_error(vendor_mermaid: Path):
    if not vendor_mermaid.is_file():
        pytest.skip("Offline mermaid.min.js not found in vendor")

    valid_code = "graph TD\n    X --> Y"
    # An impossibly short timeout of 1ms should trigger PlaywrightTimeoutError
    with pytest.raises(RuntimeError, match="Timeout rendering Mermaid block"):
        render_mermaid_to_png(
            [valid_code],
            mermaid_source=str(vendor_mermaid),
            timeout_ms=1,
            ignore_errors=False,
        )


def test_render_mermaid_timeout_ignored_when_flag_set(vendor_mermaid: Path):
    if not vendor_mermaid.is_file():
        pytest.skip("Offline mermaid.min.js not found in vendor")

    valid_code = "graph TD\n    X --> Y"
    result = render_mermaid_to_png(
        [valid_code],
        mermaid_source=str(vendor_mermaid),
        timeout_ms=1,
        ignore_errors=True,
    )
    assert valid_code not in result
