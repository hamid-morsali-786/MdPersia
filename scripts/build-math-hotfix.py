"""Wrap the accepted native Setup with a locally rebuilt reader; no publication.

The native shell and pinned optional converter remain the accepted beta.3 build.
Only the preview/HTML reader payload is updated. Requires the original Setup,
a PyInstaller reader directory, and an NSIS compiler supplied by the maintainer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--reader', type=Path, required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    assert output.is_relative_to(root / 'output')
    output.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(args.base.read_bytes()).hexdigest() == (
        '7acdfb0870a78d7ef9a38aae61346caa9594daaee20d1c2969b81f5db175c575')
    manifest = json.loads((args.installed / 'release-manifest.json').read_text())
    manifest['nativeSourceRevision'] = '1b390311d911bcd6b89df08d79a3171f968dfbaf'
    manifest['sourceRevision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    manifest['localPatch'] = 'mathml-1'
    manifest['files'] = {k: v for k, v in manifest['files'].items() if not k.startswith('reader/')}
    for path in args.reader.rglob('*'):
        if path.is_file():
            manifest['files']['reader/' + path.relative_to(args.reader).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / 'release-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    setup = output / 'MdPersia_0.3.0-beta.3_math-fix_x64-setup.exe'
    # Paths are maintainer-controlled, never document content or remote input.
    def nsi(path):
        value = str(path.resolve())
        assert not any(c in value for c in ('"', '$', '\n', '\r'))
        return value
    script = f'''
Unicode true
Name "MdPersia"
OutFile "{nsi(setup)}"
InstallDir "$LOCALAPPDATA\\Programs\\MdPersia"
RequestExecutionLevel user
SetCompressor /SOLID lzma
Icon "{nsi(root / 'src/fa_md_pdf/assets/mdpersia.ico')}"
ShowInstDetails show
Function .onInit
  FindWindow $0 "" "MdPersia | تبدیل تخصصی مارک‌داون فارسی به PDF و Word"
  StrCmp $0 0 ready
  MessageBox MB_OK "Please save your documents and close MdPersia before installing."
  Abort
  ready:
FunctionEnd
Section
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File /oname=base.exe "{nsi(args.base)}"
  ExecWait '"$PLUGINSDIR\\base.exe" /S /D=$INSTDIR' $0
  StrCmp $0 0 base_ok
  SetErrorLevel 1
  Abort "Base installation failed."
  base_ok:
  SetOutPath "$INSTDIR\\reader"
  File /r "{nsi(args.reader)}\\*"
  SetOutPath "$INSTDIR"
  File "{nsi(output / 'release-manifest.json')}"
SectionEnd
'''
    (output / 'installer.nsi').write_text(script, encoding='utf-8-sig')
    subprocess.run([str(args.compiler.resolve()), str(output / 'installer.nsi')], check=True)
    assert setup.stat().st_size < 30_000_000
    receipt = {'setup': str(setup), 'bytes': setup.stat().st_size,
               'sha256': hashlib.sha256(setup.read_bytes()).hexdigest(),
               'nativeReusedFromAcceptedBeta3': True, 'localPatch': 'mathml-1'}
    (output / 'installer-size.json').write_text(json.dumps(receipt, indent=2))
    shutil.copy2(args.installed / 'conversion-catalog.json', output)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
