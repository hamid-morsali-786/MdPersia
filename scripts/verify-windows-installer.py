"""Install, verify and uninstall in an isolated folder; restore owned handler keys.

Does not change Windows UserChoice or touch user documents. Requires no elevation.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import winreg

TREES = [r'Software\Classes\MdPersia.Markdown', r'Software\MdPersia\Capabilities']
VALUES = [(r'Software\Classes\.md\OpenWithProgids', 'MdPersia.Markdown'),
          (r'Software\Classes\.markdown\OpenWithProgids', 'MdPersia.Markdown'),
          (r'Software\RegisteredApplications', 'MdPersia')]


def read_value(path, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, kind = winreg.QueryValueEx(key, name)
            return {'value': base64.b64encode(value).decode() if isinstance(value, bytes) else value,
                    'kind': kind, 'binary': isinstance(value, bytes)}
    except FileNotFoundError:
        return None


def snapshot_tree(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            children, values, _ = winreg.QueryInfoKey(key)
            return {'values': {winreg.EnumValue(key, i)[0]: read_value(path, winreg.EnumValue(key, i)[0]) for i in range(values)},
                    'children': {winreg.EnumKey(key, i): snapshot_tree(path+'\\'+winreg.EnumKey(key, i)) for i in range(children)}}
    except FileNotFoundError:
        return None


def remove_owned_tree(path):
    if not any(path == root or path.startswith(root+'\\') for root in TREES):
        raise ValueError('Refusing to modify an unrelated registry tree')
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while winreg.QueryInfoKey(key)[0]:
                remove_owned_tree(path+'\\'+winreg.EnumKey(key, 0))
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def restore_value(path, name, item):
    if item is None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass
    else:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
            value = base64.b64decode(item['value']) if item['binary'] else item['value']
            winreg.SetValueEx(key, name, 0, item['kind'], value)


def restore_tree(path, snapshot):
    if snapshot is None:
        return
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path):
        pass
    for name, value in snapshot['values'].items():
        restore_value(path, name, value)
    for name, child in snapshot['children'].items():
        restore_tree(path+'\\'+name, child)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('setup', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-native-ui', action='store_true', help='CI packaging check; does not claim UI acceptance')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if (root / 'output').resolve() not in output.parents:
        raise ValueError('Acceptance directory must be below the workspace output directory')
    install = output / 'installed MdPersia'
    if install.exists():
        raise ValueError('Use a fresh acceptance directory')
    output.mkdir(parents=True, exist_ok=True)
    setup = args.setup.resolve()
    backup = {p: snapshot_tree(p) for p in TREES}
    values = [read_value(p, n) for p, n in VALUES]
    (output / 'handler-backup.json').write_text(json.dumps({'trees': backup, 'values': values}, indent=2))
    report = {'setup': str(setup), 'sha256': hashlib.sha256(setup.read_bytes()).hexdigest()}
    try:
        for attempt in range(2):
            # NSIS /D consumes the rest of the raw command line and must not be quoted.
            command_line = subprocess.list2cmdline([str(setup), '/S']) + ' /D=' + str(install)
            subprocess.run(command_line, check=True, timeout=300)
            assert (install / 'MdPersia.exe').is_file()
            manifest = json.loads((install / 'release-manifest.json').read_text())
            for path, expected in manifest['files'].items():
                assert hashlib.sha256((install / path).read_bytes()).hexdigest() == expected, path
        report['installAndReinstallPreserveExactBundledResources'] = True
        report['installedFileBytes'] = sum(path.stat().st_size for path in install.rglob('*') if path.is_file())
        command = read_value(TREES[0]+r'\shell\open\command', '')['value']
        assert command == f'"{install / "MdPersia.exe"}" "%1"', command
        icon = read_value(TREES[0]+r'\DefaultIcon', '')['value']
        assert 'MdPersia.exe' in icon and 'python' not in icon.lower()
        report['nativeAssociationAndApplicationIcon'] = True
        subprocess.run([sys.executable, str(root / 'scripts/verify-reader-engine.py'), str(install),
                        '--output', str(output / 'frozen')], check=True)
        if not args.skip_native_ui:
            subprocess.run([sys.executable, str(root / 'scripts/verify-native-app.py'), str(install / 'MdPersia.exe'),
                            '--output', str(output / 'native'), '--registered-handler'], check=True)
    finally:
        try:
            uninstaller = install / 'uninstall.exe'
            if uninstaller.is_file():
                subprocess.run([str(uninstaller), '/S'], check=True, timeout=120)
                for _ in range(50):
                    if not (install / 'MdPersia.exe').exists():
                        break
                    time.sleep(.1)
                report['uninstallRemovesApplication'] = not (install / 'MdPersia.exe').exists()
                if (output / 'native').exists():
                    report['documentsSurviveUninstall'] = (output / 'native/فایل نخست.md').is_file()
        finally:
            for path in TREES:
                remove_owned_tree(path)
                restore_tree(path, backup[path])
            for (path, name), value in zip(VALUES, values):
                restore_value(path, name, value)
            report['previousMarkdownHandlerRestoredAfterTest'] = True
            (output / 'installer-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
