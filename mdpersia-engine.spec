# Build with scripts/build-windows.py: one directory, no extraction on every open.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata, collect_data_files

root = Path(SPECPATH)
pw_data, pw_binaries, pw_imports = collect_all('playwright')
a = Analysis(
    [str(root / 'scripts' / 'desktop-engine-entry.py')],
    pathex=[str(root / 'src')],
    binaries=pw_binaries,
    datas=pw_data + copy_metadata('playwright') + collect_data_files('latex2mathml')
        + copy_metadata('latex2mathml') + copy_metadata('mdit-py-plugins')
        + copy_metadata('mathml2omml') + [
        (str(root / 'src/fa_md_pdf/assets'), 'fa_md_pdf/assets'),
    ],
    hiddenimports=pw_imports + collect_submodules('pygments.lexers')
        + collect_submodules('pygments.styles'),
    excludes=['tkinter', 'pytest', 'IPython', 'numpy', 'pandas'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='mdpersia-engine',
    console=True, debug=False, strip=False, upx=False,
    icon=str(root / 'src/fa_md_pdf/assets/mdpersia.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='engine')
