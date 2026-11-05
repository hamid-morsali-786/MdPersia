from __future__ import annotations

import io
import sys

import pytest

from fa_md_pdf import desktop_engine


def test_installed_assets_are_resolved_beside_engine_not_cwd(tmp_path, monkeypatch):
    app = tmp_path / 'installed app'
    fonts = app / 'assets/fonts'
    fonts.mkdir(parents=True)
    (fonts / 'Vazirmatn-Regular.ttf').write_bytes(b'font')
    vendor = app / 'assets/vendor'
    vendor.mkdir()
    (vendor / 'mermaid.min.js').write_text('/* offline */')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(app / 'engine/mdpersia-engine.exe'))
    monkeypatch.chdir(tmp_path)
    assert desktop_engine.asset_root() == app / 'assets'
    if sys.platform == 'win32':
        resolved = desktop_engine.asset_root('\\\\?\\' + str(app / 'assets'))
        assert resolved == app / 'assets'
        assert resolved.as_uri().startswith('file:///')


def test_missing_bundled_browser_fails_instead_of_using_system_install(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAYWRIGHT_BROWSERS_PATH', 'unused')
    monkeypatch.setenv('MDPERSIA_BUNDLED_ENGINE', '0')
    assets = tmp_path / 'assets'
    assets.mkdir()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match='مرورگر داخلی'):
        desktop_engine.configure_runtime(assets)
    (tmp_path / 'browsers').mkdir()
    desktop_engine.configure_runtime(assets)
    import os
    assert os.environ['PLAYWRIGHT_BROWSERS_PATH'] == str(tmp_path / 'browsers')
    assert os.environ['MDPERSIA_BUNDLED_ENGINE'] == '1'


def test_worker_reuses_renderer_and_returns_independent_documents(tmp_path):
    from fa_md_pdf.preview_worker import serve
    import json
    source = tmp_path / 'document.md'
    source.write_text('# عنوان\n\nHost: localhost', encoding='utf-8')
    requests = io.StringIO('\n'.join(json.dumps({'id': i, 'path': str(source), 'text': text})
                                  for i, text in [(1, '# نخست'), (2, '# دوم')]))
    responses = io.StringIO()
    serve(tmp_path, requests, responses)
    results = [json.loads(line) for line in responses.getvalue().splitlines()]
    assert results[0]['id'] == 1 and 'نخست' in results[0]['html']
    assert results[1]['id'] == 2 and 'دوم' in results[1]['html']
    assert 'نخست' not in results[1]['html']
