"""Absolute import keeps the frozen entrypoint independent of Python package execution."""
from fa_md_pdf.desktop_engine import main

if __name__ == '__main__':
    raise SystemExit(main())
