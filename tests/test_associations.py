"""Windows file-association helpers are pure up to winreg; only the plan is tested here."""


import pytest

from fa_md_pdf import associations
from fa_md_pdf.cli import build_parser


def test_open_command_quotes_exe_and_file():
    cmd = associations.open_command(r"C:\Program Files\MdPersia\md.exe", extra_args="--gui")
    assert cmd == '"C:\\Program Files\\MdPersia\\md.exe" --gui "%1"'


def test_open_command_falls_back_to_module_launcher_for_python():
    cmd = associations.open_command(r"C:\Python311\python.exe")
    assert "-m mdpersia" in cmd
    assert '"%1"' in cmd


def test_open_command_always_opens_the_viewer():
    """A double-click must never run a conversion, whichever entry point owns the key.

    `mdpersia file.md` without --gui is the CLI converter, and a pip-installed console
    script is not named python*, so both paths need the viewer flag.
    """
    interpreter = associations.open_command(r"C:\Python311\pythonw.exe")
    console_script = associations.open_command(r"C:\Python311\Scripts\mdpersia.exe")
    native = associations.open_command(r"I:\app\fa-md-pdf-desktop.exe")

    for cmd in (interpreter, console_script, native):
        assert associations.VIEWER_FLAG in cmd
    assert "-m mdpersia" in interpreter
    assert "-m" not in console_script


def test_build_entries_stays_under_current_user():
    entries = associations.build_entries(r"C:\app\MdPersia.exe")
    assert entries
    for entry in entries:
        assert entry.key.startswith("Software\\Classes\\") or entry.key.startswith(
            "Software\\RegisteredApplications"
        )


def test_build_entries_registers_prog_id_without_hijacking_default_extension():
    keys = {e.key for e in associations.build_entries(r"C:\app\MdPersia.exe")}
    assert associations.PROGID_KEY in keys
    # The user's own default handler for .md must not be rewritten.
    assert "Software\\Classes\\.md" not in keys
    assert "Software\\Classes\\.markdown" not in keys


def test_build_entries_exposes_open_with_and_context_verb():
    entries = associations.build_entries(r"C:\app\MdPersia.exe")
    by_key = {(e.key, e.name): e.value for e in entries}

    assert by_key[(rf"{associations.PROGID_KEY}\SupportedTypes", ".md")] == ""
    assert by_key[(rf"{associations.PROGID_KEY}\Capabilities\FileAssociations", ".markdown")] == (
        associations.PROG_ID
    )
    verb = r"Software\Classes\SystemFileAssociations\.md\shell\MdPersia.view"
    assert by_key[(verb, "")] == associations.VERB_LABEL
    assert by_key[(rf"{verb}\command", "")].endswith('"%1"')


def test_markdown_icon_is_bundled_and_independent_of_python():
    from pathlib import Path

    entries = associations.build_entries(r"C:\Python311\pythonw.exe")
    icon = next(e.value for e in entries if e.key.endswith("\\DefaultIcon"))
    assert icon.endswith('mdpersia.ico",0')
    assert "python" not in icon.lower()
    assert Path(icon.rsplit(",", 1)[0].strip('"')).is_file()


def test_custom_icon_paths_with_spaces_are_quoted():
    entries = associations.build_entries(r"C:\app\MdPersia.exe", r"C:\My icons\md.ico")
    icon = next(e.value for e in entries if e.key.endswith("\\DefaultIcon"))
    assert icon == '"C:\\My icons\\md.ico",0'


def test_uninstall_keys_cover_exactly_what_register_creates():
    trees = associations.build_uninstall_keys()
    assert associations.PROGID_KEY in trees
    for ext in associations.EXTENSIONS:
        assert rf"Software\Classes\SystemFileAssociations\{ext}\shell\MdPersia.view" in trees
    # Deleting a tree implies removing its children, so no tree may nest inside another.
    for a in trees:
        for b in trees:
            if a is not b:
                assert not b.startswith(a + "\\")


def test_resolve_viewer_exe_prefers_override_then_release(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    override = tmp_path / "Custom.exe"
    assert associations.resolve_viewer_exe(tmp_path, override) == override

    assert associations.resolve_viewer_exe(tmp_path).name.lower().startswith("python")

    release = tmp_path / "desktop-tauri" / "src-tauri" / "target" / "release"
    release.mkdir(parents=True)
    exe = release / "MdPersia.exe"
    exe.write_bytes(b"")
    assert associations.resolve_viewer_exe(tmp_path) == exe


def test_register_refuses_non_windows(monkeypatch):
    monkeypatch.setattr(associations.sys, "platform", "darwin")
    with pytest.raises(OSError):
        associations.register("C:\\app\\MdPersia.exe")


def test_association_flags_are_parsed():
    args = build_parser().parse_args(["--register-associations"])
    assert args.register_associations is True
    args = build_parser().parse_args(["--unregister-associations"])
    assert args.unregister_associations is True
    args = build_parser().parse_args(["--association-status"])
    assert args.association_status is True


def test_association_status_reports_a_working_registration(capsys, monkeypatch):
    from fa_md_pdf import associations
    from fa_md_pdf.cli import main

    monkeypatch.setattr(
        associations, "association_state",
        lambda: (True, r'"C:\Py\python.exe" -m mdpersia --gui "%1"', r"C:\Py\python.exe"),
    )
    assert main(["--association-status"]) == 0
    assert "Status: working" in capsys.readouterr().out


def test_association_status_flags_a_stale_entry_and_never_writes(capsys, monkeypatch):
    from fa_md_pdf import associations
    from fa_md_pdf.cli import main

    monkeypatch.setattr(
        associations, "association_state",
        lambda: (False, r'"C:\Py\pythonw.exe" -m fa_md_pdf.viewer "%1"',
                 "module 'fa_md_pdf.viewer' is not importable"),
    )
    writes: list = []
    monkeypatch.setattr(associations, "register", lambda *a, **k: writes.append(a))

    assert main(["--association-status"]) == 1
    out = capsys.readouterr().out
    assert "Status: broken" in out
    assert "--register-associations" in out
    assert writes == []


def test_watch_flag_survives_parser_edits():
    assert build_parser().parse_args(["-w", "a.md"]).watch is True


# --- stale-registration detection -------------------------------------------
# A key can outlive its target: this machine carries an entry pointing at a
# `fa_md_pdf.viewer` module that does not exist, so key presence alone lies.

def test_split_command_handles_quoted_windows_paths():
    exe, args = associations.split_command(
        r'"C:\Python\pythonw.exe" -m fa_md_pdf.viewer "%1"'
    )
    assert exe == r"C:\Python\pythonw.exe"
    assert args == ["-m", "fa_md_pdf.viewer", "%1"]


def test_validate_flags_a_missing_executable():
    ok, reason = associations.validate_open_command(
        r'"C:\gone\MdPersia.exe" --gui "%1"',
        exe_exists=lambda p: False,
    )
    assert ok is False
    assert "missing" in reason


def test_validate_flags_a_module_that_no_longer_exists():
    ok, reason = associations.validate_open_command(
        r'"C:\Py\pythonw.exe" -m fa_md_pdf.viewer "%1"',
        exe_exists=lambda p: True,
        module_resolver=lambda exe, mod: False,
    )
    assert ok is False
    assert "fa_md_pdf.viewer" in reason


def test_validate_accepts_a_working_command():
    seen = {}

    def resolver(exe, mod):
        seen["args"] = (exe, mod)
        return True

    ok, reason = associations.validate_open_command(
        r'"C:\Py\python.exe" -m mdpersia --gui "%1"',
        exe_exists=lambda p: True,
        module_resolver=resolver,
    )
    assert ok is True
    assert seen["args"] == (r"C:\Py\python.exe", "mdpersia")


def test_validate_flags_a_module_command_that_ignores_viewer_flag():
    """The pre-fix command stayed importable but converted instead of viewing."""
    ok, reason = associations.validate_open_command(
        r'"C:\Py\python.exe" -m mdpersia "%1"',
        exe_exists=lambda p: True,
        module_resolver=lambda exe, mod: True,
    )
    assert ok is False
    assert "--gui" in reason


def test_unreadable_module_probe_is_not_reported_as_broken():
    # resolver returning None means "could not ask"; never call that broken.
    ok, _ = associations.validate_open_command(
        r'"C:\Py\python.exe" -m mdpersia --gui "%1"',
        exe_exists=lambda p: True,
        module_resolver=lambda exe, mod: None,
    )
    assert ok is True


def test_validate_reports_not_registered_for_absent_command():
    ok, reason = associations.validate_open_command(None)
    assert ok is False
    assert reason == "not registered"


def test_registered_command_passes_its_own_validation():
    """Whatever register writes must be something status calls working."""
    for exe in (
        r"C:\Python311\pythonw.exe",
        r"C:\Python311\Scripts\mdpersia.exe",
        r"I:\Computer\dev\MdPersia\desktop-tauri\src-tauri\target\release\fa-md-pdf-desktop.exe",
    ):
        by_key = {(e.key, e.name): e.value for e in associations.build_entries(exe)}
        command = by_key[(rf"{associations.PROGID_KEY}\shell\open\command", "")]
        ok, reason = associations.validate_open_command(
            command, exe_exists=lambda p: True, module_resolver=lambda e, m: True
        )
        assert ok is True, f"{exe}: {reason}"


def test_windowless_launcher_is_preferred_for_double_clicks(tmp_path, monkeypatch):
    monkeypatch.setattr(associations.sys, "platform", "win32")
    python = tmp_path / "python.exe"
    python.write_bytes(b"")
    assert associations._windowless_launcher(python) == python

    (tmp_path / "pythonw.exe").write_bytes(b"")
    assert associations._windowless_launcher(python).name == "pythonw.exe"

    script = tmp_path / "mdpersia.exe"
    script.write_bytes(b"")
    assert associations._windowless_launcher(script) == script
