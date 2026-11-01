# Windows beta 0.3.0-beta.3 acceptance

The exact accepted Setup was built from
`1b390311d911bcd6b89df08d79a3171f968dfbaf` in
[Windows installer run 41307780307](https://github.com/Pezhm4n/MdPersia/actions/runs/41307780307).
Later acceptance-harness and documentation changes do not change this binary.
This report supplements the historical beta.2 report; it does not reuse its
measurements as evidence for beta.3.

## Artifact identity

| Item | Bytes |
|---|---:|
| `MdPersia_0.3.0-beta.3_x64-setup.exe` | 15,883,751 |
| Setup limit | 30,000,000 |
| Main installed files | 35,199,052 |
| Optional conversion download | 182,738,764 |
| Optional installed conversion files | 442,221,496 |

Installed sizes are file lengths, excluding shared WebView2, profiles and caches.
They are neither allocated disk space nor total memory measurements.

Setup SHA-256:

```text
7acdfb0870a78d7ef9a38aae61346caa9594daaee20d1c2969b81f5db175c575
```

The pinned conversion ZIP SHA-256 is
`810ef0bb3397fa5716371169c45e1e2e5e92dc6af1a8b30e4eff46f84a3b4029`.
Native acceptance downloaded the exact public pack without GitHub credentials.

## Installed application on Windows 10

Host: Windows 10 x64 build 19045; WebView2 `156.0.4314.58` already installed.
The exact Setup was installed and reinstalled into an isolated path containing
spaces, with all resource-manifest hashes checked. Application child PATH
contained only `C:\Windows\System32`, without developer Python or Node. The
native Tauri/WebView2 window used an isolated profile, with no Vite server or
mock bridge.

The final full run passed:

- Persian filenames, local images, bundled font and offline Mermaid preview
  before downloading conversion resources.
- Physical order: output sidebar left, reading/console center, file queue right;
  one sidebar toggle, close/reopen, and scrolling after an interrupted drag.
- Actual native window icon pixels exactly equal the independent 32px frame of
  the original paper/MD/RTL-arrow artwork. They are not a 16px upscale.
- Successive process and Windows shell opens append to one window's queue;
  reopening deduplicates. Relaunch does not revive the previous queue as ghosts.
- Actual live editing, Ctrl+S, BOM/CRLF preservation, and unsaved-change guard.
- Folder scanning, conversion-dialog keyboard containment, Escape and focus return.
- Explicit conversion download, cancellation, retry, same-length corrupt ZIP
  rejection, and continued reading while the real pack downloads.
- Actual three-file Word conversion, watch rebuild and stop, and PDF output.
- Preferences and conversion resources persist across relaunch. No conversion
  browser remains during reading; owned engine processes stop on app exit.
- Removing optional resources preserves reading and output documents.
- Uninstall removes the application and preserves documents; test registry
  changes restore the original owned handler entries.

Fresh-profile launch to rendered heading measured **2.944 seconds**; subsequent
launch measured **1.579 seconds**. These include CDP attachment and apply only to
this machine and fixture. The separate frozen-reader preview measured 0.183s.
No page errors were recorded in the final full native run.

Two earlier runs stopped at an overly restrictive test requiring `ICON_BIG`.
The native window supplied a correct 32px `ICON_SMALL`. The harness now checks
available slots and compares their actual pixels, rather than interpreting an
unset slot as low resolution. The probe also follows Microsoft's documented
[window-class fallback](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-geticon).
No application change was needed for this test-harness correction.

Local receipts and screenshots:
`output/installer-qa/beta3-corrected-win10-r3/`.

## Reading UI regression and other checks

`scripts/verify-reading-workspace.py --start` passed with a fresh browser profile:
single toggle, close/reopen persistence, drag-to-edge collapse and reopen,
minimum 300px visible sidebar width, pointer-capture loss and window blur,
restored real wheel scrolling, keyboard resize/reset, and widths
1024/1280/1440/1920 without horizontal overflow. Dark/light code and diagram
computed styles passed, with transparent token backgrounds and no SVG invert
filter. The tested dark edge/background contrast was 9.62; light was 7.07.
This checks the fixture and palette, not every Mermaid diagram type or a full
accessibility audit. Receipts: `output/reading-ui/reading-report.json`.

- Python: 174 tests passed; JUnit receipt `output/reading-ui/pytest.xml`.
- TypeScript: 33 tests passed; production TypeScript/Vite build succeeded.
- Editor geometry: 32 actual hit-position clicks, three tooltip controls,
  zero failures or page errors.
- Ruff passed for core/tests and the changed icon/acceptance scripts.
- CI passed two Rust package tests, frozen reader/converter checks, actual
  Mermaid PDF/Word generation, Setup size gate and install/reinstall/uninstall.

Existing Vite editor-chunk and runtime font-path warnings remain. Actual native
font loading passed. The external UX kit's 12/52 self-test concerns that kit's
missing dependencies and Windows shell/encoding assumptions; it is not a
MdPersia accessibility score.

## Installation on the user's workstation

After isolated acceptance, the same Setup was installed under the current
user's `LocalAppData\Programs\MdPersia`. All manifest hashes were checked again.
Windows `AssocQueryStringW` resolved both `.md` and `.markdown` to the installed
`MdPersia.exe`. Opening the repository README through the normal Windows shell
started that exact native executable. Existing Python/Edge windows were not
closed. Receipt: `output/native-install-beta3/user-install-report.json`.

## Limits

Setup is unsigned (`NotSigned`). A clean VM, missing-WebView2 bootstrap,
32-bit Windows, all display scales and a full accessibility audit remain
unconfirmed. The corrupt ZIP was submitted through native IPC; the valid-ZIP
file picker was not separately automated. No universal startup-time, memory
usage or bug-free claim is made.
