from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'scripts/desktop-reader-entry.py')],
    pathex=[str(root / 'src')],
    datas=[(str(root / 'src/fa_md_pdf/assets'), 'fa_md_pdf/assets')]
        + collect_data_files('latex2mathml') + copy_metadata('latex2mathml')
        + copy_metadata('mdit-py-plugins'),
    hiddenimports=collect_submodules('pygments.lexers') + collect_submodules('pygments.styles'),
    excludes=['playwright', 'docx', 'lxml', 'greenlet', 'fa_md_pdf.converter',
        'fa_md_pdf.docx_builder', 'fa_md_pdf.mermaid_renderer', 'tkinter',
        'pytest', 'IPython', 'numpy', 'pandas'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='mdpersia-reader',
    console=True, debug=False, strip=False, upx=False,
    icon=str(root / 'src/fa_md_pdf/assets/mdpersia.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='reader')
