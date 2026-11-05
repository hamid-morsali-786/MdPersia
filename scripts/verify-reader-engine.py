"""Verify the small installed preview/editor engine without a conversion pack."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    app, output = args.directory.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    engine = app / 'reader/mdpersia-reader.exe'
    env = {**os.environ, 'PATH': os.environ['SYSTEMROOT']+'\\System32', 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    for key in ('PYTHONHOME', 'PYTHONPATH', 'PLAYWRIGHT_BROWSERS_PATH'):
        env.pop(key, None)
    source = output / 'خواندن و ویرایش.md'
    source.write_bytes('# سند فارسی\r\n\r\n- Host: localhost برای اتصال\r\n'.encode('utf-8-sig'))
    assets = '\\\\?\\'+str(app / 'assets')
    command = [str(engine), '--assets-dir', assets]
    doctor = subprocess.run([*command, '--doctor'], env=env, cwd=output, encoding='utf-8', capture_output=True, check=True)
    report = {'os': platform.platform(), 'doctor': json.loads(doctor.stdout), 'restrictedPath': env['PATH']}
    assert report['doctor']['kind'] == 'reader' and report['doctor']['assets'] == str(app / 'assets')
    assert not (app / 'browsers').exists() and not (app / 'engine').exists()
    assert not list((app / 'reader').rglob('node.exe'))
    started = time.perf_counter()
    worker = subprocess.Popen([*command, '--worker'], env=env, cwd=output, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    try:
        def request(**body):
            worker.stdin.write(json.dumps({'id':1, **body}, ensure_ascii=False)+'\n')
            worker.stdin.flush()
            result = json.loads(worker.stdout.readline())
            assert not result.get('error'), result
            return result
        html = request(operation='preview', path=str(source))['html']
        assert 'سند فارسی' in html
        report['firstPreviewSeconds'] = round(time.perf_counter()-started, 3)
        document = request(operation='read', path=str(source))['document']
        changed = document['text']+'\nذخیره بدون موتور تبدیل\n'
        request(operation='save', path=str(source), text=changed, revision=document['revision'])
        assert source.read_bytes() == changed.replace('\n', '\r\n').encode('utf-8-sig')
        report['previewReadSaveWithoutBrowserPythonOrNodeOnPath'] = True
    finally:
        worker.stdin.close()
        worker.wait(timeout=15)
    wrapped = subprocess.run([*command, '--convert', str(source), '--wrap-rtl'], env=env, cwd=output,
                             encoding='utf-8', capture_output=True, check=True)
    assert source.with_name(source.stem+'.rtl.md').is_file(), wrapped.stdout+wrapped.stderr
    report['rtlMarkdownConversionNeedsNoOptionalPack'] = True
    (output / 'reader-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
