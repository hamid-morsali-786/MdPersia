"""
Tests for mdpersia public API exports and compatibility aliases.
"""

from __future__ import annotations
import mdpersia


def test_mdpersia_exports():
    assert hasattr(mdpersia, "__version__")
    assert hasattr(mdpersia, "convert_jobs")
    assert hasattr(mdpersia, "build_jobs")
    assert hasattr(mdpersia, "ConvertOptions")
    assert hasattr(mdpersia, "ConversionError")
    assert hasattr(mdpersia, "main")
    assert mdpersia.__version__ == "0.2.0"
