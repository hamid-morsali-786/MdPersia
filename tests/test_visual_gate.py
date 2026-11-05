import runpy

import pytest


def test_visual_gate_rejects_changed_pixels_and_dimensions(tmp_path):
    image = pytest.importorskip('PIL.Image')
    compare = runpy.run_path('scripts/verify-visual-corpus.py')['compare']
    expected, actual, diff = [tmp_path / name for name in ['expected.png', 'actual.png', 'diff.png']]
    image.new('RGB', (100, 100), 'white').save(expected)
    image.new('RGB', (100, 100), 'white').save(actual)
    compare(actual, expected, diff)
    image.new('RGB', (100, 100), 'black').save(actual)
    with pytest.raises(AssertionError, match='Visual regression'):
        compare(actual, expected, diff)
    assert diff.exists()
    image.new('RGB', (101, 100), 'white').save(actual)
    with pytest.raises(AssertionError, match='Page size changed'):
        compare(actual, expected, diff)
