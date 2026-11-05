"""Fail the release when Setup exceeds the user's strict 30 MB limit."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = list((root / 'desktop-tauri/src-tauri/target/release/bundle/nsis').glob('*-setup.exe'))
if len(files) != 1:
    raise SystemExit(f'Expected one Setup, got {len(files)}')
setup = files[0]
size = setup.stat().st_size
receipt = {'filename': setup.name, 'bytes': size, 'limitBytes': 30_000_000,
           'sha256': hashlib.sha256(setup.read_bytes()).hexdigest(), 'passed': size <= 30_000_000}
(root / 'output/release/installer-size.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
if not receipt['passed']:
    raise SystemExit('Setup exceeds the required 30 MB limit')
