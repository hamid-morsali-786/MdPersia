"""Stage the existing desktop reader and an immutable optional conversion ZIP."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output/release'
STAGING = OUTPUT / 'staging'
FULL = OUTPUT / 'conversion-content'


def main() -> None:
    subprocess.run([sys.executable, str(ROOT / 'scripts/build-windows.py')], cwd=ROOT, check=True)
    assert OUTPUT.resolve() in FULL.resolve().parents
    if FULL.exists():
        shutil.rmtree(FULL)
    STAGING.replace(FULL)
    metadata = json.loads((FULL / 'release-manifest.json').read_text())
    version = metadata['version']
    metadata['kind'] = 'conversion'
    (FULL / 'release-manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    packs = OUTPUT / 'conversion-packs'
    packs.mkdir(exist_ok=True)
    pending = packs / 'conversion.zip'
    with zipfile.ZipFile(pending, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(FULL.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(FULL).as_posix())
    digest = hashlib.sha256(pending.read_bytes()).hexdigest()
    filename = f'MdPersia-conversion-{version}-{digest[:16]}.zip'
    package = packs / filename
    pending.replace(package)
    STAGING.mkdir()
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--distpath', str(STAGING), '--workpath', str(OUTPUT / 'reader-build'),
        str(ROOT / 'mdpersia-reader.spec')], cwd=ROOT, check=True)
    shutil.copytree(FULL / 'assets', STAGING / 'assets')
    shutil.copy2(FULL / 'THIRD_PARTY_NOTICES.txt', STAGING)
    browser = next((FULL / 'browsers').glob('chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe'))
    repository = os.environ.get('GITHUB_REPOSITORY', 'Pezhm4n/MdPersia')
    catalog = {'version': version, 'sha256': digest, 'bytes': package.stat().st_size,
        'filename': filename, 'engineVersion': version.replace('-beta.', 'b'),
        'browserExecutable': browser.relative_to(FULL).as_posix(),
        'url': f'https://github.com/{repository}/releases/download/resources-v{version}/{filename}'}
    (STAGING / 'conversion-catalog.json').write_text(json.dumps(catalog, indent=2)+'\n')
    files = {p.relative_to(STAGING).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(STAGING.rglob('*')) if p.is_file()}
    (STAGING / 'release-manifest.json').write_text(json.dumps({
        'version': version, 'sourceRevision': metadata['sourceRevision'],
        'kind': 'reader', 'files': files}, indent=2)+'\n')
    assert not list((STAGING / 'reader').rglob('node.exe')), 'Node leaked into reader'
    assert not (STAGING / 'browsers').exists()
    subprocess.run([str(STAGING / 'reader/mdpersia-reader.exe'), '--doctor'], check=True)
    print(json.dumps({'readerBytes': sum(p.stat().st_size for p in STAGING.rglob('*') if p.is_file()),
                      'optionalPack': str(package), 'optionalPackBytes': catalog['bytes']}, indent=2))


if __name__ == '__main__':
    main()
