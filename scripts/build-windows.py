"""Stage the complete offline engine for Tauri. Run in an isolated release venv.

python -m pip install -r requirements-release.lock
python scripts/build-windows.py
cd desktop-tauri; npm ci; npm run tauri build -- --bundles nsis
"""
from __future__ import annotations

import hashlib
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output' / 'release'
STAGING = OUTPUT / 'staging'


def reset_generated(path: Path) -> None:
    target = path.resolve()
    if OUTPUT.resolve() not in target.parents:
        raise ValueError(f'Refusing to remove outside generated release directory: {target}')
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)


def run(*args: str, env=None) -> None:
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def main() -> None:
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        raise SystemExit('Build on Windows x64 with Python 3.11 x64.')
    browser_cache = OUTPUT / 'browser-cache'
    previous_browsers = STAGING / 'browsers'
    if previous_browsers.is_dir() and not browser_cache.exists():
        assert OUTPUT.resolve() in previous_browsers.resolve().parents
        assert OUTPUT.resolve() in browser_cache.resolve().parents
        shutil.move(str(previous_browsers), str(browser_cache))
    reset_generated(STAGING)
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--distpath', str(STAGING), '--workpath', str(OUTPUT / 'pyinstaller'),
        str(ROOT / 'mdpersia-engine.spec'))
    assets = STAGING / 'assets'
    for folder in ('fonts', 'vendor'):
        shutil.copytree(ROOT / folder, assets / folder)
    shutil.copy2(ROOT / 'LICENSE', assets / 'LICENSE')
    licenses = assets / 'licenses'
    licenses.mkdir()
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.is_file():
        shutil.copy2(python_license, licenses / 'Python.txt')
    for package in ('playwright', 'greenlet', 'pyee', 'markdown-it-py', 'mdurl',
                    'latex2mathml', 'mathml2omml', 'mdit-py-plugins',
                    'python-docx', 'lxml', 'Pygments', 'typing_extensions', 'pyinstaller'):
        dist = distribution(package)
        for file in dist.files or []:
            if file.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE')):
                relative = Path(file.name) if '..' in file.parts else Path(str(file))
                target = licenses / package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dist.locate_file(file), target)
    run(sys.executable, '-m', 'playwright', 'install', '--only-shell', 'chromium',
        env={**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(browser_cache)})
    shutil.copytree(browser_cache, STAGING / 'browsers', ignore=shutil.ignore_patterns('.links'))
    # The driver Node binary is private to Playwright; no global Node is used.
    notices = ['MdPersia: MIT (assets/LICENSE).',
        'Vazirmatn: SIL Open Font License (assets/fonts/OFL.txt).',
        'Mermaid: MIT (assets/vendor/LICENSE.mermaid).',
        'Python: PSF License; python-docx: MIT; markdown-it-py: MIT; Pygments: BSD.',
        'Playwright: Apache-2.0; Chromium: BSD and bundled third-party licenses.',
        'See engine/_internal and browsers for bundled dependency license files.']
    (STAGING / 'THIRD_PARTY_NOTICES.txt').write_text('\n'.join(notices) + '\n', encoding='utf-8')
    version = json.loads((ROOT / 'desktop-tauri/package.json').read_text())['version']
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    files = {p.relative_to(STAGING).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(STAGING.rglob('*')) if p.is_file()}
    manifest = {'version': version, 'sourceRevision': revision, 'files': files}
    (STAGING / 'release-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    run(str(STAGING / 'engine/mdpersia-engine.exe'), '--doctor')
    print(f'Staged complete runtime: {STAGING}')


if __name__ == '__main__':
    main()
