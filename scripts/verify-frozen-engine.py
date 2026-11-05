"""Exercise the shipped executable with no Python/Node on PATH, away from the repo."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    app, output = args.directory.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    engine = app / 'engine/mdpersia-engine.exe'
    env = {**os.environ, 'PATH': os.path.join(os.environ['SYSTEMROOT'], 'System32'),
           'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONNOUSERSITE': '1'}
    for key in ('PYTHONHOME', 'PYTHONPATH', 'PLAYWRIGHT_BROWSERS_PATH'):
        env.pop(key, None)
    source = output / 'سند آزمایش نصب.md'
    text = '# آزمایش MdPersia\r\n\r\n- Host: localhost برای اتصال\r\n\r\nEnglish Solver: example.\r\n\r\n```mermaid\r\ngraph LR\r\nA[شروع]-->B[پایان]\r\n```\r\n'
    source.write_bytes(text.encode('utf-8-sig'))
    def run(*options: str):
        return subprocess.run([str(engine), *options], cwd=output, env=env,
                              encoding='utf-8', capture_output=True, check=True, timeout=120)
    report = {'os': platform.platform(), 'restrictedPath': env['PATH'],
              'doctor': json.loads(run('--doctor').stdout)}
    # Reproduce the exact resource path representation returned by Tauri on Windows.
    assets = '\\\\?\\' + str(app / 'assets')
    native_doctor = json.loads(run('--assets-dir', assets, '--doctor').stdout)
    assert native_doctor['assets'] == str(app / 'assets')
    report['tauriVerbatimResourcePathNormalized'] = True
    started = time.perf_counter()
    worker = subprocess.Popen([str(engine), '--assets-dir', assets, '--worker'], cwd=output, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    try:
        def request(**body):
            worker.stdin.write(json.dumps({'id': 1, **body}, ensure_ascii=False)+'\n')
            worker.stdin.flush()
            reply = json.loads(worker.stdout.readline())
            assert not reply.get('error'), reply
            return reply
        preview = request(operation='preview', path=str(source))
        report['firstPreviewSeconds'] = round(time.perf_counter()-started, 3)
        assert 'آزمایش MdPersia' in preview['html'] and 'mermaid' in preview['html']
        started = time.perf_counter()
        request(operation='preview', path=str(source))
        report['warmPreviewSeconds'] = round(time.perf_counter()-started, 3)
        snapshot = request(operation='read', path=str(source))['document']
        changed = snapshot['text'] + '\nبند ذخیره‌شده\n'
        request(operation='save', path=str(source), text=changed, revision=snapshot['revision'])
        assert source.read_bytes().startswith(b'\xef\xbb\xbf')
        assert 'بند ذخیره‌شده' in source.read_text(encoding='utf-8-sig')
        report['realReadSaveAndBomPreserved'] = True
    finally:
        worker.stdin.close()
        worker.wait(timeout=15)
    for kind in ('pdf', 'docx'):
        result = run('--assets-dir', assets, '--convert', str(source), '--format', kind, '--verbose')
        (output / f'{kind}-conversion.log').write_text(result.stdout+result.stderr, encoding='utf-8')
        target = source.with_suffix('.'+kind)
        assert target.is_file() and target.stat().st_size > 1000
        if kind == 'pdf':
            assert target.read_bytes().startswith(b'%PDF-')
        else:
            with zipfile.ZipFile(target) as archive:
                assert 'آزمایش MdPersia' in archive.read('word/document.xml').decode('utf-8')
                assert any(p.startswith('word/media/') for p in archive.namelist()), 'Mermaid image missing'
        report[kind+'Bytes'] = target.stat().st_size
    report['bundledPdfAndDocxWithMermaid'] = True
    (output / 'frozen-engine-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
